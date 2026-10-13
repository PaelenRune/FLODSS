"""Population initialization strategies for Genetic Layout Optimization."""

import itertools
import random
from typing import Dict, List, Optional, Set, Tuple

from app.algorithms.ga.fitness import GAFitnessEvaluator
from app.algorithms.ga.models import BayChromosome, GAConfig, Individual, individual_sort_key
from app.algorithms.generator.models import GeneratorConfig
from app.algorithms.generator.search_guillotine_packing import GuillotineRowPackingEngine
from app.models.department import Department
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout


def find_valid_bay_combinations(
    problem: FacilityLayoutProblem,
    orientation: str = "horizontal",
    min_bay_size: int = 1,
    max_bay_size: int = 6,
) -> List[Tuple[str, ...]]:
    """Identify department combinations whose collective bay height/width satisfies individual bounds."""
    fac_w = problem.facility.width
    fac_h = problem.facility.height
    tot_area_prob = problem.total_required_area
    area_util = tot_area_prob / (fac_w * fac_h) if (fac_w * fac_h) > 0 else 1.0
    sum_max_w = sum(d.max_width for d in problem.departments if d.max_width is not None)

    if area_util >= 0.40 and (sum_max_w == 0 or fac_w <= sum_max_w):
        active_w = fac_w
        active_h = fac_h
    else:
        aspect = fac_w / fac_h if fac_h > 0 else 1.0
        active_w = round((tot_area_prob * aspect) ** 0.5, 2)
        active_h = round(tot_area_prob / active_w, 2)

    depts = list(problem.departments)
    valid_bays: List[Tuple[str, ...]] = []

    for r in range(min_bay_size, min(max_bay_size + 1, len(depts) + 1)):
        for combo in itertools.combinations(depts, r):
            tot_area = sum(d.required_area for d in combo)
            if orientation == "vertical":
                bay_w = tot_area / active_h
                ok = True
                for d in combo:
                    h = d.required_area / bay_w
                    if d.min_width is not None and bay_w < d.min_width - 1e-4:
                        ok = False; break
                    if d.max_width is not None and bay_w > d.max_width + 1e-4:
                        ok = False; break
                    if d.min_height is not None and h < d.min_height - 1e-4:
                        ok = False; break
                    if d.max_height is not None and h > d.max_height + 1e-4:
                        ok = False; break
                    if d.min_aspect_ratio is not None or d.max_aspect_ratio is not None:
                        ar = max(bay_w / h, h / bay_w)
                        if d.min_aspect_ratio and ar < d.min_aspect_ratio - 1e-4:
                            ok = False; break
                        if d.max_aspect_ratio and ar > d.max_aspect_ratio + 1e-4:
                            ok = False; break
                if ok:
                    valid_bays.append(tuple(d.id for d in combo))
            else:
                bay_h = tot_area / active_w
                ok = True
                for d in combo:
                    w = d.required_area / bay_h
                    if d.min_width is not None and w < d.min_width - 1e-4:
                        ok = False; break
                    if d.max_width is not None and w > d.max_width + 1e-4:
                        ok = False; break
                    if d.min_height is not None and bay_h < d.min_height - 1e-4:
                        ok = False; break
                    if d.max_height is not None and bay_h > d.max_height + 1e-4:
                        ok = False; break
                    if d.min_aspect_ratio is not None or d.max_aspect_ratio is not None:
                        ar = max(w / bay_h, bay_h / w)
                        if d.min_aspect_ratio and ar < d.min_aspect_ratio - 1e-4:
                            ok = False; break
                        if d.max_aspect_ratio and ar > d.max_aspect_ratio + 1e-4:
                            ok = False; break
                if ok:
                    valid_bays.append(tuple(d.id for d in combo))

    return valid_bays


def extract_chromosome_from_layout(
    layout: ContinuousLayout,
    orientation: str = "horizontal",
) -> Optional[BayChromosome]:
    """Convert an existing continuous layout into an equivalent BayChromosome."""
    if not layout.placements:
        return None

    placements = list(layout.placements.values())
    if orientation == "vertical":
        # Group by x coordinate
        sorted_p = sorted(placements, key=lambda p: (round(p.x, 1), round(p.y, 1)))
        bays_dict: Dict[float, List[str]] = {}
        for p in sorted_p:
            key = round(p.x, 1)
            bays_dict.setdefault(key, []).append(p.department_id)
        bays = list(bays_dict.values())
    else:
        # Group by y coordinate
        sorted_p = sorted(placements, key=lambda p: (round(p.y, 1), round(p.x, 1)))
        bays_dict = {}
        for p in sorted_p:
            key = round(p.y, 1)
            bays_dict.setdefault(key, []).append(p.department_id)
        bays = list(bays_dict.values())

    order: List[str] = []
    bay_sizes: List[int] = []
    for b in bays:
        order.extend(b)
        bay_sizes.append(len(b))

    return BayChromosome(order=order, bay_sizes=bay_sizes, orientation=orientation)


def initialize_population(
    problem: FacilityLayoutProblem,
    config: GAConfig,
    evaluator: GAFitnessEvaluator,
    rng: random.Random,
) -> List[Individual]:
    """Construct and evaluate the initial GA population using domain heuristics and diversity."""
    dept_ids = [d.id for d in problem.departments]
    n = len(dept_ids)
    population: List[Individual] = []
    seen_signatures: Set[str] = set()

    def add_chromosome(chrom: BayChromosome) -> bool:
        sig = f"{'-'.join(chrom.order)}|{'-'.join(str(s) for s in chrom.bay_sizes)}|{chrom.orientation}"
        if sig in seen_signatures:
            return False
        seen_signatures.add(sig)
        ind = Individual(chromosome=chrom)
        evaluator.evaluate(problem, ind, config)
        population.append(ind)
        return True

    # 1. Guillotine row packing seed (if requested and problem is suitable)
    if config.seed_with_guillotine and n >= 4:
        try:
            gen_cfg = GeneratorConfig(
                max_nodes=500,
                max_backtracks=250,
                max_runtime_seconds=1.5,
                tolerance=config.tolerance,
                random_seed=config.random_seed,
            )
            gen_res = GuillotineRowPackingEngine.search(problem, gen_cfg)
            if gen_res.is_feasible and gen_res.layout:
                extracted = extract_chromosome_from_layout(gen_res.layout, orientation=config.orientation)
                if extracted and len(extracted.order) == n:
                    add_chromosome(extracted)
                    # Also add a few permutation variations within the same bays
                    bays = extracted.get_bays()
                    for _ in range(5):
                        permuted_bays = [rng.sample(b, len(b)) for b in bays]
                        add_chromosome(BayChromosome.from_bays(permuted_bays, orientation=config.orientation))
        except Exception:
            pass

    # 2. Heuristic domain partitions (search valid bay combinations)
    valid_combos = find_valid_bay_combinations(problem, orientation=config.orientation)
    if valid_combos:
        # Search for valid bay partitions of all departments
        all_ids_set = set(dept_ids)
        for i, b1 in enumerate(valid_combos[:60]):
            rem = all_ids_set - set(b1)
            for b2 in valid_combos[i + 1 : i + 60]:
                if set(b2).issubset(rem):
                    b3 = tuple(did for did in dept_ids if did in rem and did not in b2)
                    if b3 in valid_combos or not b3:
                        bays_to_use = [list(b1), list(b2)]
                        if b3:
                            bays_to_use.append(list(b3))
                        # Create chromosome
                        c = BayChromosome.from_bays(bays_to_use, orientation=config.orientation)
                        add_chromosome(c)
                        # Add a few internal order permutations
                        for _ in range(2):
                            perm_b = [rng.sample(b, len(b)) for b in bays_to_use]
                            add_chromosome(BayChromosome.from_bays(perm_b, orientation=config.orientation))
                    if len(population) >= config.population_size // 2:
                        break
            if len(population) >= config.population_size // 2:
                break

    # 3. Flow-volume heuristic orderings
    flow_weights: Dict[str, float] = {did: 0.0 for did in dept_ids}
    for flow in problem.flows:
        flow_weights[flow.source_department] = flow_weights.get(flow.source_department, 0.0) + flow.quantity
        flow_weights[flow.target_department] = flow_weights.get(flow.target_department, 0.0) + flow.quantity

    sorted_by_flow = sorted(dept_ids, key=lambda did: flow_weights[did], reverse=True)
    # Area descending
    sorted_by_area = sorted(dept_ids, key=lambda did: [d.required_area for d in problem.departments if d.id == did][0], reverse=True)

    # Standard bay size partitions
    k_bays = max(config.min_bays, min(config.max_bays, n // 3 if n >= 6 else 2))
    base_size = n // k_bays
    rem_size = n % k_bays
    std_bay_sizes = [base_size + (1 if i < rem_size else 0) for i in range(k_bays)]

    add_chromosome(BayChromosome(order=sorted_by_flow, bay_sizes=std_bay_sizes, orientation=config.orientation))
    add_chromosome(BayChromosome(order=sorted_by_area, bay_sizes=std_bay_sizes, orientation=config.orientation))

    # 4. Fill remaining population with randomized individuals
    attempts = 0
    max_attempts = config.population_size * 20
    while len(population) < config.population_size and attempts < max_attempts:
        attempts += 1
        rand_order = rng.sample(dept_ids, n)
        # Random bay partition
        num_b = rng.randint(config.min_bays, config.max_bays)
        # Partition n into num_b integers >= 1
        cuts = sorted(rng.sample(range(1, n), num_b - 1))
        b_sizes = [cuts[0]] + [cuts[j] - cuts[j - 1] for j in range(1, len(cuts))] + [n - cuts[-1]]

        chrom = BayChromosome(order=rand_order, bay_sizes=b_sizes, orientation=config.orientation)
        add_chromosome(chrom)

    # Sort initial population using Feasibility-First (Deb's rule)
    population.sort(key=individual_sort_key)
    return population[: config.population_size]
