"""Extensible Problem Loader architecture supporting JSON, CSV, and future formats."""

from abc import ABC, abstractmethod
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship
from app.models.constraint import Constraint
from app.models.problem import FacilityLayoutProblem, ObjectiveConfig
from app.services.matrix_parser import parse_from_to_matrix, parse_relationship_matrix


class BaseProblemLoader(ABC):
    """Abstract Base Class for format-specific problem loaders."""

    @abstractmethod
    def can_load(self, source_path: Path) -> bool:
        """Return True if this loader can handle the source file format."""
        pass

    @abstractmethod
    def load(self, source: Union[str, Path, TextIO, Dict[str, Any]]) -> FacilityLayoutProblem:
        """Load and return a validated FacilityLayoutProblem instance."""
        pass


class JSONProblemLoader(BaseProblemLoader):
    """Loads problems from JSON files or dict payloads."""

    def can_load(self, source_path: Path) -> bool:
        return source_path.suffix.lower() == ".json"

    def load(self, source: Union[str, Path, TextIO, Dict[str, Any]]) -> FacilityLayoutProblem:
        if isinstance(source, dict):
            return FacilityLayoutProblem.model_validate(source)
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Problem file not found at: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FacilityLayoutProblem.model_validate(data)

        # File-like object
        data = json.load(source)
        return FacilityLayoutProblem.model_validate(data)


class CSVProblemLoader(BaseProblemLoader):
    """Loads problems from CSV packages or multi-table CSV files."""

    def can_load(self, source_path: Path) -> bool:
        return source_path.suffix.lower() == ".csv" or (source_path.is_dir() and any(source_path.glob("*.csv")))

    def load(self, source: Union[str, Path, TextIO, Dict[str, Any]]) -> FacilityLayoutProblem:
        """Load from a CSV directory containing departments.csv, facility.csv, flows.csv, relationships.csv."""
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.is_dir():
                return self._load_from_directory(path)
            elif path.is_file():
                return self._load_single_csv(path)
        raise ValueError("CSVProblemLoader requires a directory or file path.")

    def _load_from_directory(self, dir_path: Path) -> FacilityLayoutProblem:
        # 1. Facility
        facility_file = dir_path / "facility.csv"
        if not facility_file.exists():
            raise FileNotFoundError(f"Missing required 'facility.csv' in {dir_path}")
        with open(facility_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            facility = Facility(
                id=row.get("id", "FAC_01"),
                name=row.get("name", "Facility"),
                width=float(row["width"]),
                height=float(row["height"]),
                area=float(row["area"]) if "area" in row and row["area"] else None,
            )

        # 2. Departments
        depts_file = dir_path / "departments.csv"
        if not depts_file.exists():
            raise FileNotFoundError(f"Missing required 'departments.csv' in {dir_path}")
        departments: List[Department] = []
        with open(depts_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                departments.append(
                    Department(
                        id=row["id"].strip(),
                        name=row.get("name", row["id"]).strip(),
                        required_area=float(row["required_area"]),
                        min_width=float(row["min_width"]) if row.get("min_width") else None,
                        max_width=float(row["max_width"]) if row.get("max_width") else None,
                        min_height=float(row["min_height"]) if row.get("min_height") else None,
                        max_height=float(row["max_height"]) if row.get("max_height") else None,
                    )
                )

        # 3. Flows (optional)
        flows: List[Flow] = []
        flows_file = dir_path / "flows.csv"
        if flows_file.exists():
            with open(flows_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # Check if it's matrix or tabular
                if "source_department" in content or "source" in content:
                    reader = csv.DictReader(content.splitlines())
                    for row in reader:
                        flows.append(
                            Flow(
                                source_department=row.get("source_department") or row["source"],
                                target_department=row.get("target_department") or row["target"],
                                quantity=float(row["quantity"]),
                                unit=row.get("unit", "moves/day"),
                                cost_per_unit_distance=float(row.get("cost_per_unit_distance", 1.0)),
                            )
                        )
                else:
                    flows = parse_from_to_matrix(content)

        # 4. Relationships (optional)
        relationships: List[Relationship] = []
        rels_file = dir_path / "relationships.csv"
        if rels_file.exists():
            with open(rels_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                relationships = parse_relationship_matrix(content)

        return FacilityLayoutProblem(
            id=dir_path.name,
            name=f"Problem {dir_path.name}",
            facility=facility,
            departments=departments,
            flows=flows,
            relationships=relationships,
        )

    def _load_single_csv(self, file_path: Path) -> FacilityLayoutProblem:
        """Parse structured single CSV with multiple tagged sections or standard format."""
        raise NotImplementedError(
            f"Single-file CSV problem loading not yet supported. Please provide a CSV directory or JSON file ({file_path})."
        )


class ExcelProblemLoader(BaseProblemLoader):
    """Placeholder for future XLSX Excel spreadsheet ingestion."""

    def can_load(self, source_path: Path) -> bool:
        return source_path.suffix.lower() in (".xlsx", ".xls")

    def load(self, source: Union[str, Path, TextIO, Dict[str, Any]]) -> FacilityLayoutProblem:
        raise NotImplementedError(
            "ExcelProblemLoader (.xlsx) is scheduled for a future release. Please export to JSON or CSV."
        )


class ProblemLoaderFactory:
    """Dispatches loading to the appropriate format-specific loader."""

    _loaders: List[BaseProblemLoader] = [
        JSONProblemLoader(),
        CSVProblemLoader(),
        ExcelProblemLoader(),
    ]

    @classmethod
    def get_loader(cls, path: Union[str, Path]) -> BaseProblemLoader:
        source_path = Path(path)
        for loader in cls._loaders:
            if loader.can_load(source_path):
                return loader
        # Default fallback to JSON loader
        return cls._loaders[0]

    @classmethod
    def load(cls, source: Union[str, Path, Dict[str, Any]]) -> FacilityLayoutProblem:
        if isinstance(source, dict):
            return JSONProblemLoader().load(source)
        loader = cls.get_loader(source)
        return loader.load(source)


def load_problem(source: Union[str, Path, Dict[str, Any]]) -> FacilityLayoutProblem:
    """Convenience function to load a problem from any supported file path or dictionary."""
    return ProblemLoaderFactory.load(source)
