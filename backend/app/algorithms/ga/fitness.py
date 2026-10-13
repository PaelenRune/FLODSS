"""Fitness assessment service for Genetic Algorithm layout optimization."""

from typing import Dict, List, Optional
from app.algorithms.ga.decoder import BayChromosomeDecoder
from app.algorithms.ga.models import GAConfig, Individual
from app.constraints.engine import ConstraintEngine
from app.evaluation.config import EvaluationConfig
from app.evaluation.evaluators import MaterialHandlingCostEvaluator
from app.models.constraint import ConstraintClassification
from app.models.problem import FacilityLayoutProblem


class GAFitnessEvaluator:
    """Evaluates individual layouts for Material Handling Cost (MHC) and soft penalties."""

    def __init__(self, eval_config: Optional[EvaluationConfig] = None):
        self.eval_config = eval_config or EvaluationConfig()
        self.mhc_evaluator = MaterialHandlingCostEvaluator(self.eval_config)
        self.constraint_engine = ConstraintEngine()

    def evaluate(
        self,
        problem: FacilityLayoutProblem,
        individual: Individual,
        config: GAConfig,
    ) -> None:
        """Decode chromosome and calculate fitness with feasibility constraints."""
        layout, is_feasible, violations = BayChromosomeDecoder.decode(
            problem=problem,
            chromosome=individual.chromosome,
            tolerance=config.tolerance,
        )
        individual.layout = layout
        individual.violations = violations

        if not layout.placements:
            individual.is_feasible = False
            individual.raw_mhc = float("inf")
            individual.soft_penalty = 0.0
            individual.fitness = config.infeasible_penalty + 1e6
            return

        # 1. Calculate raw Material Handling Cost (MHC)
        mhc_res = self.mhc_evaluator.evaluate(problem, layout)
        raw_mhc = float(mhc_res.value)
        individual.raw_mhc = raw_mhc

        # 2. Calculate soft constraint violations and penalties
        all_violations = self.constraint_engine.check_all(problem, layout)
        soft_violations = [v for v in all_violations if v.classification == ConstraintClassification.SOFT]
        soft_penalty = sum(v.penalty_cost for v in soft_violations)
        individual.soft_penalty = round(soft_penalty, 2)

        # 3. Overall feasibility
        individual.is_feasible = is_feasible

        # 4. Fitness score:
        # Feasible individuals minimize: MHC + lambda * Soft Penalty.
        # Infeasible individuals receive a massive penalty barrier so feasible solutions always dominate.
        if is_feasible:
            fitness = raw_mhc + (config.soft_penalty_weight * soft_penalty)
        else:
            penalty_barrier = config.infeasible_penalty + (len(violations) * 10000.0)
            fitness = penalty_barrier + raw_mhc

        individual.fitness = round(fitness, 2)
