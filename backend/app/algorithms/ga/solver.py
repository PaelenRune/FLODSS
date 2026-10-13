"""Genetic Algorithm Solver implementation for Facility Layout Optimization."""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Set

from app.algorithms.base import AlgorithmCategory, BaseLayoutAlgorithm, ValidationResult
from app.algorithms.ga.fitness import GAFitnessEvaluator
from app.algorithms.ga.initialization import initialize_population
from app.algorithms.ga.models import (
    BayChromosome,
    GAConfig,
    GAResult,
    GATerminationReason,
    GenerationRecord,
    Individual,
    individual_sort_key,
)
from app.algorithms.ga.operators import (
    crossover_chromosomes,
    mutate_chromosome,
    tournament_selection,
)
from app.algorithms.registry import AlgorithmRegistry
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.models.geometry import Dimensions2D, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import DepartmentPlacement, LayoutSolution
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator

logger = logging.getLogger(__name__)


@AlgorithmRegistry.register("ga")
@AlgorithmRegistry.register("genetic_algorithm")
class GeneticLayoutAlgorithm(BaseLayoutAlgorithm):
    """Genetic Algorithm optimization heuristic for unequal-area facility layouts.
    
    Uses Flexible Bay Structure (FBS) chromosome representation, Order Crossover (OX),
    and multi-objective fitness balancing Material Handling Cost (MHC) and soft constraints.
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters=parameters)

    @property
    def name(self) -> str:
        return "genetic_algorithm"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AlgorithmCategory:
        return AlgorithmCategory.METAHEURISTIC

    @property
    def default_parameters(self) -> Dict[str, Any]:
        return GAConfig().model_dump()

    @property
    def supported_problem_types(self) -> List[str]:
        return ["unequal_areas", "continuous", "aspect_ratios", "soft_constraints", "hard_constraints"]

    def validate(self, problem: FacilityLayoutProblem) -> ValidationResult:
        """Verify problem has departments and valid facility dimensions."""
        errors: List[str] = []
        warnings: List[str] = []

        if not problem.departments:
            errors.append("Problem contains no departments.")
        if len(problem.departments) < 2:
            errors.append("At least 2 departments are required for optimization.")
        if problem.facility.width <= 0 or problem.facility.height <= 0:
            errors.append(f"Invalid facility dimensions: {problem.facility.width}x{problem.facility.height}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def solve(self, problem: FacilityLayoutProblem, **kwargs) -> LayoutSolution:
        """Execute Genetic Algorithm and return standard LayoutSolution."""
        result = self.solve_with_result(problem, **kwargs)
        return result.best_solution

    def solve_with_result(
        self,
        problem: FacilityLayoutProblem,
        config: Optional[GAConfig] = None,
        **kwargs,
    ) -> GAResult:
        """Execute Genetic Algorithm and return comprehensive GAResult with telemetry."""
        # 1. Merge hyperparameters
        merged_params = self.parameters.copy()
        merged_params.update(kwargs)
        if config is not None:
            effective_config = config
        else:
            effective_config = GAConfig(**{k: v for k, v in merged_params.items() if k in GAConfig.model_fields})

        start_time = time.time()
        rng = random.Random(effective_config.random_seed)

        eval_config = EvaluationConfig()
        evaluator = GAFitnessEvaluator(eval_config)

        # 2. Initialize population
        population: List[Individual] = initialize_population(
            problem=problem,
            config=effective_config,
            evaluator=evaluator,
            rng=rng,
        )

        if not population:
            raise RuntimeError("Genetic Algorithm failed to initialize population.")

        # Identify best individual using Feasibility-First (Deb's rule)
        population.sort(key=individual_sort_key)
        best_ind = population[0].model_copy(deep=True)

        initial_mhc = best_ind.raw_mhc
        history: List[GenerationRecord] = []
        stagnant_generations = 0
        termination_reason = GATerminationReason.MAX_GENERATIONS_REACHED

        # Record initial generation 0
        avg_fit = sum(ind.fitness for ind in population) / len(population)
        unique_fits = len(set(round(ind.fitness, 2) for ind in population))
        feasible_count = sum(1 for ind in population if ind.is_feasible)
        best_feasible_mhc = min((ind.raw_mhc for ind in population if ind.is_feasible), default=None)
        unique_chroms = len(set((tuple(ind.chromosome.order), tuple(ind.chromosome.bay_sizes), ind.chromosome.orientation) for ind in population))
        unique_sigs = len(set(generate_layout_signature(ind.layout) for ind in population if ind.layout and ind.is_feasible))

        history.append(
            GenerationRecord(
                generation=0,
                best_fitness=best_ind.fitness,
                best_mhc=best_ind.raw_mhc,
                best_soft_penalty=best_ind.soft_penalty,
                avg_fitness=round(avg_fit, 2),
                best_is_feasible=best_ind.is_feasible,
                diversity=round(unique_fits / len(population), 4),
                best_feasible_mhc=best_feasible_mhc,
                feasible_count=feasible_count,
                unique_chromosomes=unique_chroms,
                unique_signatures=unique_sigs,
                invalid_offspring_count=0,
            )
        )

        # 3. Generational loop
        for gen in range(1, effective_config.generations + 1):
            # Check elapsed runtime
            elapsed = time.time() - start_time
            if elapsed >= effective_config.max_runtime_seconds:
                termination_reason = GATerminationReason.TIMEOUT
                break

            # Check stagnation limit
            if stagnant_generations >= effective_config.stagnation_limit:
                termination_reason = GATerminationReason.STAGNATION_LIMIT_REACHED
                break

            # Elitism: retain top individuals using feasibility-first order
            elites = [ind.model_copy(deep=True) for ind in population[: effective_config.elitism_count]]
            next_population: List[Individual] = list(elites)

            invalid_offspring_count = 0

            # Produce offspring
            while len(next_population) < effective_config.population_size:
                p1 = tournament_selection(population, effective_config.tournament_size, rng)
                p2 = tournament_selection(population, effective_config.tournament_size, rng)

                c1_chrom, c2_chrom = crossover_chromosomes(
                    p1.chromosome,
                    p2.chromosome,
                    effective_config.crossover_rate,
                    rng,
                )

                c1_chrom = mutate_chromosome(c1_chrom, effective_config.mutation_rate, effective_config, rng)
                c2_chrom = mutate_chromosome(c2_chrom, effective_config.mutation_rate, effective_config, rng)

                ind1 = Individual(chromosome=c1_chrom)
                evaluator.evaluate(problem, ind1, effective_config)
                if not ind1.is_feasible:
                    invalid_offspring_count += 1
                next_population.append(ind1)

                if len(next_population) < effective_config.population_size:
                    ind2 = Individual(chromosome=c2_chrom)
                    evaluator.evaluate(problem, ind2, effective_config)
                    if not ind2.is_feasible:
                        invalid_offspring_count += 1
                    next_population.append(ind2)

            next_population.sort(key=individual_sort_key)
            population = next_population[: effective_config.population_size]

            current_gen_best = population[0]
            if individual_sort_key(current_gen_best) < individual_sort_key(best_ind):
                best_ind = current_gen_best.model_copy(deep=True)
                stagnant_generations = 0
            else:
                stagnant_generations += 1

            # Telemetry logging
            gen_avg_fit = sum(ind.fitness for ind in population) / len(population)
            gen_unique_fits = len(set(round(ind.fitness, 2) for ind in population))
            gen_feasible_count = sum(1 for ind in population if ind.is_feasible)
            gen_best_feasible_mhc = min((ind.raw_mhc for ind in population if ind.is_feasible), default=None)
            gen_unique_chroms = len(set((tuple(ind.chromosome.order), tuple(ind.chromosome.bay_sizes), ind.chromosome.orientation) for ind in population))
            gen_unique_sigs = len(set(generate_layout_signature(ind.layout) for ind in population if ind.layout and ind.is_feasible))

            history.append(
                GenerationRecord(
                    generation=gen,
                    best_fitness=best_ind.fitness,
                    best_mhc=best_ind.raw_mhc,
                    best_soft_penalty=best_ind.soft_penalty,
                    avg_fitness=round(gen_avg_fit, 2),
                    best_is_feasible=best_ind.is_feasible,
                    diversity=round(gen_unique_fits / len(population), 4),
                    best_feasible_mhc=gen_best_feasible_mhc,
                    feasible_count=gen_feasible_count,
                    unique_chromosomes=gen_unique_chroms,
                    unique_signatures=gen_unique_sigs,
                    invalid_offspring_count=invalid_offspring_count,
                )
            )

        total_runtime = time.time() - start_time

        # 4. Final solution construction
        best_layout = best_ind.layout or ContinuousLayout(
            problem_id=problem.id,
            facility_width=problem.facility.width,
            facility_height=problem.facility.height,
            placements={},
        )

        placements_dict: Dict[str, DepartmentPlacement] = {}
        positions_dict: Dict[str, Point2D] = {}
        dimensions_dict: Dict[str, Dimensions2D] = {}
        for did, cp in best_layout.placements.items():
            dp = DepartmentPlacement(
                department_id=did,
                origin=Point2D(x=cp.x, y=cp.y),
                dimensions=Dimensions2D(width=cp.width, height=cp.height),
            )
            placements_dict[did] = dp
            positions_dict[did] = dp.centroid
            dimensions_dict[did] = dp.dimensions

        # Full assessment via EvaluationEngine
        eval_engine = EvaluationEngine()
        eval_report = eval_engine.evaluate(problem, best_layout)

        impr_mhc = initial_mhc - best_ind.raw_mhc
        impr_pct = (impr_mhc / initial_mhc * 100.0) if initial_mhc > 0 else 0.0

        layout_solution = LayoutSolution(
            problem_id=problem.id,
            algorithm_name=self.name,
            algorithm_version=self.version,
            execution_time_seconds=round(total_runtime, 4),
            placements=placements_dict,
            department_positions=positions_dict,
            department_dimensions=dimensions_dict,
            is_complete=len(placements_dict) == len(problem.departments),
            placed_department_count=len(placements_dict),
            total_department_count=len(problem.departments),
            feasibility_status=best_ind.is_feasible,
            objective_values={
                "material_handling_cost": round(best_ind.raw_mhc, 2),
                "soft_penalty": round(best_ind.soft_penalty, 2),
                "combined_fitness": round(best_ind.fitness, 2),
                "initial_mhc": round(initial_mhc, 2),
                "improvement_mhc": round(impr_mhc, 2),
                "improvement_percentage": round(impr_pct, 2),
            },
            constraint_violations=eval_report.constraint_violations,
            metadata={
                "chromosome": best_ind.chromosome.model_dump(),
                "generations_completed": len(history) - 1,
                "termination_reason": termination_reason.value,
                "history": [h.model_dump() for h in history],
                "layout_signature": eval_report.layout_signature,
            },
        )

        # Collect unique feasible candidate layouts from population
        unique_candidate_layouts: List[ContinuousLayout] = []
        seen_candidate_sigs: Set[str] = set()

        if best_layout and best_ind.is_feasible:
            best_sig = eval_report.layout_signature or generate_layout_signature(best_layout)
            seen_candidate_sigs.add(best_sig)
            unique_candidate_layouts.append(best_layout)

        for ind in population:
            if ind.is_feasible and ind.layout:
                sig = generate_layout_signature(ind.layout)
                if sig not in seen_candidate_sigs:
                    seen_candidate_sigs.add(sig)
                    unique_candidate_layouts.append(ind.layout)

        return GAResult(
            best_solution=layout_solution,
            best_layout=best_layout,
            best_chromosome=best_ind.chromosome,
            best_fitness=best_ind.fitness,
            best_mhc=best_ind.raw_mhc,
            best_soft_penalty=best_ind.soft_penalty,
            is_feasible=best_ind.is_feasible,
            generation_count=len(history) - 1,
            termination_reason=termination_reason,
            runtime_seconds=round(total_runtime, 4),
            history=history,
            initial_mhc=round(initial_mhc, 2),
            improvement_mhc=round(impr_mhc, 2),
            improvement_percentage=round(impr_pct, 2),
            candidate_pool=unique_candidate_layouts,
        )
