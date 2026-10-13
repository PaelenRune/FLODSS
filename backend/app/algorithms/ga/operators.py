"""Genetic operators: Selection, Order Crossover (OX), and Mutations for Flexible Bay Structure."""

import random
from typing import List, Tuple

from app.algorithms.ga.models import BayChromosome, GAConfig, Individual, individual_sort_key


def tournament_selection(
    population: List[Individual],
    tournament_size: int,
    rng: random.Random,
) -> Individual:
    """Sample k individuals uniformly at random and return the best using feasibility-first ranking."""
    k = min(tournament_size, len(population))
    candidates = rng.sample(population, k)
    return min(candidates, key=individual_sort_key)


def order_crossover(
    order1: List[str],
    order2: List[str],
    rng: random.Random,
) -> Tuple[List[str], List[str]]:
    """Classic 2-Point Order Crossover (OX) for department permutations.
    
    Guarantees no duplicate and no omitted departments in either offspring.
    """
    n = len(order1)
    if n <= 2:
        return list(order1), list(order2)

    pt1 = rng.randint(0, n - 2)
    pt2 = rng.randint(pt1 + 1, n - 1)

    def ox_single(p1: List[str], p2: List[str]) -> List[str]:
        child = ["" for _ in range(n)]
        # Copy middle slice from p1
        child[pt1 : pt2 + 1] = p1[pt1 : pt2 + 1]
        copied_set = set(child[pt1 : pt2 + 1])

        # Fill remaining spots cyclically starting from pt2 + 1 using p2 elements
        p2_idx = (pt2 + 1) % n
        child_idx = (pt2 + 1) % n

        while child_idx != pt1:
            item = p2[p2_idx]
            if item not in copied_set:
                child[child_idx] = item
                copied_set.add(item)
                child_idx = (child_idx + 1) % n
            p2_idx = (p2_idx + 1) % n

        return child

    child1 = ox_single(order1, order2)
    child2 = ox_single(order2, order1)
    return child1, child2


def bay_sizes_crossover(
    bays1: List[int],
    bays2: List[int],
    total_depts: int,
    rng: random.Random,
) -> Tuple[List[int], List[int]]:
    """Recombine bay partitions while maintaining sum(bay_sizes) == total_depts."""
    # With 50% chance, swap bay configurations
    if rng.random() < 0.5:
        return list(bays2), list(bays1)
    return list(bays1), list(bays2)


def crossover_chromosomes(
    parent1: BayChromosome,
    parent2: BayChromosome,
    crossover_rate: float,
    rng: random.Random,
) -> Tuple[BayChromosome, BayChromosome]:
    """Execute crossover between two parent chromosomes with given probability."""
    if rng.random() > crossover_rate:
        return parent1.copy(), parent2.copy()

    total_depts = len(parent1.order)
    c1_order, c2_order = order_crossover(parent1.order, parent2.order, rng)
    c1_bays, c2_bays = bay_sizes_crossover(parent1.bay_sizes, parent2.bay_sizes, total_depts, rng)

    child1 = BayChromosome(
        order=c1_order,
        bay_sizes=c1_bays,
        orientation=parent1.orientation,
    )
    child2 = BayChromosome(
        order=c2_order,
        bay_sizes=c2_bays,
        orientation=parent2.orientation,
    )
    return child1, child2


def swap_mutation(order: List[str], rng: random.Random) -> List[str]:
    """Swap two distinct positions in the permutation."""
    n = len(order)
    if n < 2:
        return list(order)
    mutated = list(order)
    i, j = rng.sample(range(n), 2)
    mutated[i], mutated[j] = mutated[j], mutated[i]
    return mutated


def insertion_mutation(order: List[str], rng: random.Random) -> List[str]:
    """Remove department at index i and insert at index j."""
    n = len(order)
    if n < 2:
        return list(order)
    mutated = list(order)
    i = rng.randrange(n)
    item = mutated.pop(i)
    j = rng.randrange(n)
    mutated.insert(j, item)
    return mutated


def inversion_mutation(order: List[str], rng: random.Random) -> List[str]:
    """Reverse subsegment between two random cut points."""
    n = len(order)
    if n < 3:
        return list(order)
    mutated = list(order)
    i, j = sorted(rng.sample(range(n), 2))
    mutated[i : j + 1] = reversed(mutated[i : j + 1])
    return mutated


def bay_shift_mutation(bay_sizes: List[int], rng: random.Random) -> List[int]:
    """Transfer one department from a bay of size > 1 to an adjacent bay."""
    if len(bay_sizes) < 2:
        return list(bay_sizes)

    valid_donor_indices = [idx for idx, size in enumerate(bay_sizes) if size > 1]
    if not valid_donor_indices:
        return list(bay_sizes)

    donor = rng.choice(valid_donor_indices)
    # Choose adjacent recipient (left or right)
    options: List[int] = []
    if donor > 0:
        options.append(donor - 1)
    if donor < len(bay_sizes) - 1:
        options.append(donor + 1)

    recipient = rng.choice(options)
    mutated = list(bay_sizes)
    mutated[donor] -= 1
    mutated[recipient] += 1
    return mutated


def bay_split_or_merge_mutation(
    bay_sizes: List[int],
    min_bays: int,
    max_bays: int,
    rng: random.Random,
) -> List[int]:
    """Split a large bay into two or merge two adjacent bays."""
    mutated = list(bay_sizes)
    can_split = len(mutated) < max_bays and any(s >= 2 for s in mutated)
    can_merge = len(mutated) > min_bays

    if can_split and (not can_merge or rng.random() < 0.5):
        # Split a bay
        eligible = [idx for idx, size in enumerate(mutated) if size >= 2]
        chosen = rng.choice(eligible)
        size = mutated[chosen]
        part1 = size // 2
        part2 = size - part1
        mutated = mutated[:chosen] + [part1, part2] + mutated[chosen + 1 :]
    elif can_merge:
        # Merge two adjacent bays
        chosen = rng.randrange(len(mutated) - 1)
        merged_size = mutated[chosen] + mutated[chosen + 1]
        mutated = mutated[:chosen] + [merged_size] + mutated[chosen + 2 :]

    return mutated


def mutate_chromosome(
    chromosome: BayChromosome,
    mutation_rate: float,
    config: GAConfig,
    rng: random.Random,
) -> BayChromosome:
    """Apply stochastic mutation to chromosome order and/or bay partition structure."""
    if rng.random() > mutation_rate:
        return chromosome.copy()

    order = list(chromosome.order)
    bay_sizes = list(chromosome.bay_sizes)

    # 1. Permutation mutation
    perm_mut_type = rng.choice(["swap", "insertion", "inversion"])
    if perm_mut_type == "swap":
        order = swap_mutation(order, rng)
    elif perm_mut_type == "insertion":
        order = insertion_mutation(order, rng)
    else:
        order = inversion_mutation(order, rng)

    # 2. Bay structure mutation (with 35% probability if mutation triggered)
    if rng.random() < 0.35:
        if rng.random() < 0.7:
            bay_sizes = bay_shift_mutation(bay_sizes, rng)
        else:
            bay_sizes = bay_split_or_merge_mutation(bay_sizes, config.min_bays, config.max_bays, rng)

    return BayChromosome(
        order=order,
        bay_sizes=bay_sizes,
        orientation=chromosome.orientation,
    )
