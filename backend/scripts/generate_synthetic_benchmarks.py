"""Generates 4 synthetic industrial benchmark datasets for Phase 13 validation:
1. HIGH_DENSITY_15 (15 departments, 90.0% area utilization, heterogeneous departments)
2. HIGH_DENSITY_20 (20 departments, 91.67% area utilization, tight aspect ratio limits, dense flow)
3. CONSTRAINED_FACTORY_12 (12 departments, fixed positions, reserved zones, hard & soft constraints)
4. LOGISTICS_FACTORY_15 (15 departments, asymmetric directed flows, sequential process routing)
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"


def build_high_density_15():
    """Build synthetic HIGH_DENSITY_15 benchmark problem."""
    departments = [
        {"id": "DEP_01_REC", "name": "Receiving Dock", "required_area": 1200.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_02_RAW", "name": "Raw Material Warehouse", "required_area": 1800.0, "min_width": 25.0, "max_width": 70.0, "min_height": 25.0, "max_height": 70.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_03_MAC1", "name": "Heavy Machining Cell 1", "required_area": 1500.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_04_MAC2", "name": "Heavy Machining Cell 2", "required_area": 1500.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_05_MILL", "name": "Light Milling & Drilling", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_06_STAMP", "name": "Sheet Metal Stamping", "required_area": 1200.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_07_WELD", "name": "Robotic Welding Bay", "required_area": 1400.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_08_HEAT", "name": "Heat Treatment Furnaces", "required_area": 800.0, "min_width": 15.0, "max_width": 40.0, "min_height": 15.0, "max_height": 40.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_09_SURF", "name": "Surface Finishing & Paint", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_10_QC", "name": "Quality Control & CMM", "required_area": 600.0, "min_width": 12.0, "max_width": 40.0, "min_height": 12.0, "max_height": 40.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_11_SUBA", "name": "Sub-Assembly Line A", "required_area": 1000.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_12_SUBB", "name": "Sub-Assembly Line B", "required_area": 1000.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_13_ASSY", "name": "Final System Assembly", "required_area": 1200.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_14_PACK", "name": "Packaging & Crating", "required_area": 700.0, "min_width": 15.0, "max_width": 40.0, "min_height": 15.0, "max_height": 40.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_15_SHIP", "name": "Shipping & Logistics Dock", "required_area": 500.0, "min_width": 12.0, "max_width": 35.0, "min_height": 12.0, "max_height": 35.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
    ]

    flows = [
        {"source_department": "DEP_01_REC", "target_department": "DEP_02_RAW", "quantity": 180.0, "cost_per_unit_distance": 1.0, "unit": "pallets/day"},
        {"source_department": "DEP_02_RAW", "target_department": "DEP_03_MAC1", "quantity": 60.0, "cost_per_unit_distance": 1.2, "unit": "totes/day"},
        {"source_department": "DEP_02_RAW", "target_department": "DEP_04_MAC2", "quantity": 55.0, "cost_per_unit_distance": 1.2, "unit": "totes/day"},
        {"source_department": "DEP_02_RAW", "target_department": "DEP_06_STAMP", "quantity": 70.0, "cost_per_unit_distance": 1.5, "unit": "coils/day"},
        {"source_department": "DEP_03_MAC1", "target_department": "DEP_05_MILL", "quantity": 45.0, "cost_per_unit_distance": 1.0, "unit": "parts/day"},
        {"source_department": "DEP_04_MAC2", "target_department": "DEP_08_HEAT", "quantity": 40.0, "cost_per_unit_distance": 1.5, "unit": "baskets/day"},
        {"source_department": "DEP_06_STAMP", "target_department": "DEP_07_WELD", "quantity": 65.0, "cost_per_unit_distance": 1.2, "unit": "frames/day"},
        {"source_department": "DEP_07_WELD", "target_department": "DEP_09_SURF", "quantity": 60.0, "cost_per_unit_distance": 1.3, "unit": "chassis/day"},
        {"source_department": "DEP_08_HEAT", "target_department": "DEP_10_QC", "quantity": 40.0, "cost_per_unit_distance": 1.0, "unit": "batches/day"},
        {"source_department": "DEP_05_MILL", "target_department": "DEP_10_QC", "quantity": 45.0, "cost_per_unit_distance": 1.0, "unit": "parts/day"},
        {"source_department": "DEP_09_SURF", "target_department": "DEP_11_SUBA", "quantity": 30.0, "cost_per_unit_distance": 1.1, "unit": "panels/day"},
        {"source_department": "DEP_09_SURF", "target_department": "DEP_12_SUBB", "quantity": 30.0, "cost_per_unit_distance": 1.1, "unit": "panels/day"},
        {"source_department": "DEP_10_QC", "target_department": "DEP_11_SUBA", "quantity": 40.0, "cost_per_unit_distance": 1.0, "unit": "kits/day"},
        {"source_department": "DEP_10_QC", "target_department": "DEP_12_SUBB", "quantity": 40.0, "cost_per_unit_distance": 1.0, "unit": "kits/day"},
        {"source_department": "DEP_11_SUBA", "target_department": "DEP_13_ASSY", "quantity": 70.0, "cost_per_unit_distance": 1.4, "unit": "modules/day"},
        {"source_department": "DEP_12_SUBB", "target_department": "DEP_13_ASSY", "quantity": 70.0, "cost_per_unit_distance": 1.4, "unit": "modules/day"},
        {"source_department": "DEP_13_ASSY", "target_department": "DEP_14_PACK", "quantity": 90.0, "cost_per_unit_distance": 1.2, "unit": "machines/day"},
        {"source_department": "DEP_14_PACK", "target_department": "DEP_15_SHIP", "quantity": 90.0, "cost_per_unit_distance": 1.0, "unit": "crates/day"},
    ]

    relationships = [
        {"department_a": "DEP_01_REC", "department_b": "DEP_02_RAW", "relationship_type": "A", "score": 16.0, "reason": "Immediate raw material receiving buffer"},
        {"department_a": "DEP_02_RAW", "department_b": "DEP_03_MAC1", "relationship_type": "E", "score": 8.0, "reason": "Direct batch transfer to machining"},
        {"department_a": "DEP_06_STAMP", "department_b": "DEP_07_WELD", "relationship_type": "A", "score": 16.0, "reason": "Stampings feed welding fixtures"},
        {"department_a": "DEP_07_WELD", "department_b": "DEP_09_SURF", "relationship_type": "E", "score": 8.0, "reason": "Weldments to shot blast and painting"},
        {"department_a": "DEP_11_SUBA", "department_b": "DEP_13_ASSY", "relationship_type": "A", "score": 16.0, "reason": "Primary feeder to final line"},
        {"department_a": "DEP_12_SUBB", "department_b": "DEP_13_ASSY", "relationship_type": "A", "score": 16.0, "reason": "Secondary feeder to final line"},
        {"department_a": "DEP_13_ASSY", "department_b": "DEP_14_PACK", "relationship_type": "A", "score": 16.0, "reason": "Continuous assembly offload"},
        {"department_a": "DEP_14_PACK", "department_b": "DEP_15_SHIP", "relationship_type": "A", "score": 16.0, "reason": "Packaged freight loading dock"},
        {"department_a": "DEP_08_HEAT", "department_b": "DEP_10_QC", "relationship_type": "I", "score": 4.0, "reason": "Metallurgical inspection"},
        {"department_a": "DEP_08_HEAT", "department_b": "DEP_15_SHIP", "relationship_type": "X", "score": -8.0, "reason": "Thermal hazard isolation from dock"},
    ]

    constraints = [
        {"id": "C_NON_OVERLAP", "type": "non_overlapping", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "Strict physical boundary non-overlap"},
        {"id": "C_BOUNDARY", "type": "boundary", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "All departments strictly within facility boundaries"},
        {"id": "C_HEAT_ISOLATION", "type": "min_distance", "involved_departments": ["DEP_08_HEAT", "DEP_15_SHIP"], "parameters": {"distance": 30.0}, "classification": "soft", "penalty": 4000.0, "description": "Thermal buffer requirement between heat treat and shipping dock"},
    ]

    return {
        "id": "HIGH_DENSITY_15",
        "name": "Synthetic High-Density Heavy Machinery Plant (15 Departments)",
        "facility": {
            "id": "FAC_HD_15",
            "name": "Heavy Machinery Plant",
            "width": 180.0,
            "height": 100.0,
            "area": 18000.0,
            "metadata": {"synthetic": True, "created_for": "Phase 13 Industrial Validation"}
        },
        "departments": departments,
        "flows": flows,
        "relationships": relationships,
        "constraints": constraints,
        "metadata": {
            "is_synthetic": True,
            "validation_suite": "Phase 13 Industrial Benchmark Suite",
            "density_category": "high_density",
            "department_count": 15,
            "target_utilization": 0.90,
        }
    }


def build_high_density_20():
    """Build synthetic HIGH_DENSITY_20 benchmark problem."""
    depts_data = [
        ("DEP_01_INB", "Inbound Logistics Hub", 1600.0),
        ("DEP_02_RAWA", "Raw Steel Storage Bay A", 1400.0),
        ("DEP_03_RAWB", "Raw Alloy Storage Bay B", 1400.0),
        ("DEP_04_SAW", "Sawing & Blank Preparation", 1000.0),
        ("DEP_05_MILL", "CNC Milling Cell", 1200.0),
        ("DEP_06_TURN", "CNC Turning Lathe Cell", 1200.0),
        ("DEP_07_GRIND", "Precision Cylindrical Grinding", 800.0),
        ("DEP_08_PRESS", "Heavy Hydraulic Stamping", 1500.0),
        ("DEP_09_RWELD", "Robotic Seam Welding", 1300.0),
        ("DEP_10_MWELD", "Manual TIG/MIG Welding", 1000.0),
        ("DEP_11_WASH", "Industrial Degreasing & Wash", 700.0),
        ("DEP_12_HEAT", "Annealing & Heat Treatment", 900.0),
        ("DEP_13_COAT", "Electroplating & Protective Coating", 1100.0),
        ("DEP_14_CLEAN", "Cleanroom Precision Assembly", 1000.0),
        ("DEP_15_MOD1", "Sub-Assembly Module 1", 1100.0),
        ("DEP_16_MOD2", "Sub-Assembly Module 2", 1100.0),
        ("DEP_17_INTEG", "Final System Integration", 1500.0),
        ("DEP_18_METRO", "Coordinate Metrology & Testing", 800.0),
        ("DEP_19_AUTO_PACK", "Automated Packaging Cell", 800.0),
        ("DEP_20_OUTB", "Outbound Logistics Hub", 1600.0),
    ]

    departments = []
    for d_id, name, area in depts_data:
        departments.append({
            "id": d_id,
            "name": name,
            "required_area": area,
            "min_width": 15.0,
            "max_width": 75.0,
            "min_height": 15.0,
            "max_height": 75.0,
            "min_aspect_ratio": 1.0,
            "max_aspect_ratio": 2.0,
        })

    flows = [
        {"source_department": "DEP_01_INB", "target_department": "DEP_02_RAWA", "quantity": 100.0, "cost_per_unit_distance": 1.0, "unit": "t/day"},
        {"source_department": "DEP_01_INB", "target_department": "DEP_03_RAWB", "quantity": 100.0, "cost_per_unit_distance": 1.0, "unit": "t/day"},
        {"source_department": "DEP_02_RAWA", "target_department": "DEP_04_SAW", "quantity": 80.0, "cost_per_unit_distance": 1.2, "unit": "t/day"},
        {"source_department": "DEP_03_RAWB", "target_department": "DEP_08_PRESS", "quantity": 80.0, "cost_per_unit_distance": 1.2, "unit": "t/day"},
        {"source_department": "DEP_04_SAW", "target_department": "DEP_05_MILL", "quantity": 40.0, "cost_per_unit_distance": 1.1, "unit": "parts/day"},
        {"source_department": "DEP_04_SAW", "target_department": "DEP_06_TURN", "quantity": 40.0, "cost_per_unit_distance": 1.1, "unit": "parts/day"},
        {"source_department": "DEP_05_MILL", "target_department": "DEP_07_GRIND", "quantity": 35.0, "cost_per_unit_distance": 1.0, "unit": "parts/day"},
        {"source_department": "DEP_06_TURN", "target_department": "DEP_07_GRIND", "quantity": 35.0, "cost_per_unit_distance": 1.0, "unit": "parts/day"},
        {"source_department": "DEP_08_PRESS", "target_department": "DEP_09_RWELD", "quantity": 50.0, "cost_per_unit_distance": 1.3, "unit": "frames/day"},
        {"source_department": "DEP_08_PRESS", "target_department": "DEP_10_MWELD", "quantity": 30.0, "cost_per_unit_distance": 1.2, "unit": "frames/day"},
        {"source_department": "DEP_09_RWELD", "target_department": "DEP_11_WASH", "quantity": 45.0, "cost_per_unit_distance": 1.0, "unit": "assemblies/day"},
        {"source_department": "DEP_10_MWELD", "target_department": "DEP_11_WASH", "quantity": 25.0, "cost_per_unit_distance": 1.0, "unit": "assemblies/day"},
        {"source_department": "DEP_07_GRIND", "target_department": "DEP_12_HEAT", "quantity": 60.0, "cost_per_unit_distance": 1.4, "unit": "baskets/day"},
        {"source_department": "DEP_12_HEAT", "target_department": "DEP_13_COAT", "quantity": 60.0, "cost_per_unit_distance": 1.2, "unit": "baskets/day"},
        {"source_department": "DEP_11_WASH", "target_department": "DEP_13_COAT", "quantity": 60.0, "cost_per_unit_distance": 1.2, "unit": "frames/day"},
        {"source_department": "DEP_13_COAT", "target_department": "DEP_18_METRO", "quantity": 100.0, "cost_per_unit_distance": 1.0, "unit": "kits/day"},
        {"source_department": "DEP_18_METRO", "target_department": "DEP_14_CLEAN", "quantity": 30.0, "cost_per_unit_distance": 1.5, "unit": "optics/day"},
        {"source_department": "DEP_18_METRO", "target_department": "DEP_15_MOD1", "quantity": 40.0, "cost_per_unit_distance": 1.1, "unit": "kits/day"},
        {"source_department": "DEP_18_METRO", "target_department": "DEP_16_MOD2", "quantity": 40.0, "cost_per_unit_distance": 1.1, "unit": "kits/day"},
        {"source_department": "DEP_14_CLEAN", "target_department": "DEP_17_INTEG", "quantity": 30.0, "cost_per_unit_distance": 1.5, "unit": "sensors/day"},
        {"source_department": "DEP_15_MOD1", "target_department": "DEP_17_INTEG", "quantity": 40.0, "cost_per_unit_distance": 1.3, "unit": "subsystems/day"},
        {"source_department": "DEP_16_MOD2", "target_department": "DEP_17_INTEG", "quantity": 40.0, "cost_per_unit_distance": 1.3, "unit": "subsystems/day"},
        {"source_department": "DEP_17_INTEG", "target_department": "DEP_19_AUTO_PACK", "quantity": 80.0, "cost_per_unit_distance": 1.2, "unit": "products/day"},
        {"source_department": "DEP_19_AUTO_PACK", "target_department": "DEP_20_OUTB", "quantity": 80.0, "cost_per_unit_distance": 1.0, "unit": "pallets/day"},
    ]

    relationships = [
        {"department_a": "DEP_01_INB", "department_b": "DEP_02_RAWA", "relationship_type": "A", "score": 16.0, "reason": "Immediate raw delivery"},
        {"department_a": "DEP_01_INB", "department_b": "DEP_03_RAWB", "relationship_type": "A", "score": 16.0, "reason": "Immediate raw delivery"},
        {"department_a": "DEP_17_INTEG", "department_b": "DEP_19_AUTO_PACK", "relationship_type": "A", "score": 16.0, "reason": "Packaging feed line"},
        {"department_a": "DEP_19_AUTO_PACK", "department_b": "DEP_20_OUTB", "relationship_type": "A", "score": 16.0, "reason": "Outbound dock buffering"},
        {"department_a": "DEP_14_CLEAN", "department_b": "DEP_17_INTEG", "relationship_type": "E", "score": 8.0, "reason": "Cleanroom assembly delivery"},
        {"department_a": "DEP_08_PRESS", "department_b": "DEP_18_METRO", "relationship_type": "X", "score": -8.0, "reason": "Vibration isolation between press and CMM"},
        {"department_a": "DEP_12_HEAT", "department_b": "DEP_14_CLEAN", "relationship_type": "X", "score": -8.0, "reason": "Thermal/particulate hazard isolation"},
    ]

    constraints = [
        {"id": "C_NON_OVERLAP", "type": "non_overlapping", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "Strict physical boundary non-overlap"},
        {"id": "C_BOUNDARY", "type": "boundary", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "All departments strictly within facility boundaries"},
        {"id": "C_VIBRATION_SEP", "type": "min_distance", "involved_departments": ["DEP_08_PRESS", "DEP_18_METRO"], "parameters": {"distance": 40.0}, "classification": "soft", "penalty": 5000.0, "description": "Vibration damping buffer between press and CMM"},
    ]

    return {
        "id": "HIGH_DENSITY_20",
        "name": "Synthetic High-Density Advanced Manufacturing Complex (20 Departments)",
        "facility": {
            "id": "FAC_HD_20",
            "name": "Advanced Manufacturing Complex",
            "width": 200.0,
            "height": 120.0,
            "area": 24000.0,
            "metadata": {"synthetic": True, "created_for": "Phase 13 Industrial Validation"}
        },
        "departments": departments,
        "flows": flows,
        "relationships": relationships,
        "constraints": constraints,
        "metadata": {
            "is_synthetic": True,
            "validation_suite": "Phase 13 Industrial Benchmark Suite",
            "density_category": "very_high_density",
            "department_count": 20,
            "target_utilization": 0.9167,
        }
    }


def build_constrained_factory_12():
    """Build synthetic CONSTRAINED_FACTORY_12 benchmark problem with fixed departments and reserved zones."""
    departments = [
        {
            "id": "DEP_01_GATE",
            "name": "Main Logistics Intake Gate",
            "required_area": 1200.0,
            "min_width": 25.0,
            "max_width": 35.0,
            "min_height": 35.0,
            "max_height": 45.0,
            "min_aspect_ratio": 1.0,
            "max_aspect_ratio": 1.6,
            "fixed_position": {"x": 0.0, "y": 0.0}
        },
        {"id": "DEP_02_PRESS", "name": "Heavy Stamping Press Cell", "required_area": 1400.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_03_MACH", "name": "5-Axis CNC Machining", "required_area": 1200.0, "min_width": 20.0, "max_width": 55.0, "min_height": 20.0, "max_height": 55.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_04_WELD", "name": "Automated Welding Cell", "required_area": 1100.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_05_CLEAN", "name": "Part Washing & Degreasing", "required_area": 800.0, "min_width": 15.0, "max_width": 45.0, "min_height": 15.0, "max_height": 45.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_06_PAINT", "name": "Powder Coating & Painting", "required_area": 1000.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_07_SUB1", "name": "Chassis Sub-Assembly", "required_area": 1100.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_08_SUB2", "name": "Electrical Harness Line", "required_area": 900.0, "min_width": 15.0, "max_width": 45.0, "min_height": 15.0, "max_height": 45.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_09_ASSY", "name": "Final Conveyor Assembly", "required_area": 1500.0, "min_width": 25.0, "max_width": 65.0, "min_height": 25.0, "max_height": 65.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_10_METRO", "name": "Optical Metrology & QC", "required_area": 700.0, "min_width": 15.0, "max_width": 40.0, "min_height": 15.0, "max_height": 40.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 1.8},
        {"id": "DEP_11_PACK", "name": "Boxing & Wrapping Cell", "required_area": 900.0, "min_width": 15.0, "max_width": 45.0, "min_height": 15.0, "max_height": 45.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_12_SHIP", "name": "Outbound Logistics Dock", "required_area": 1200.0, "min_width": 20.0, "max_width": 50.0, "min_height": 20.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
    ]

    flows = [
        {"source_department": "DEP_01_GATE", "target_department": "DEP_02_PRESS", "quantity": 90.0, "cost_per_unit_distance": 1.2, "unit": "loads/day"},
        {"source_department": "DEP_01_GATE", "target_department": "DEP_03_MACH", "quantity": 80.0, "cost_per_unit_distance": 1.2, "unit": "loads/day"},
        {"source_department": "DEP_02_PRESS", "target_department": "DEP_04_WELD", "quantity": 70.0, "cost_per_unit_distance": 1.3, "unit": "totes/day"},
        {"source_department": "DEP_03_MACH", "target_department": "DEP_05_CLEAN", "quantity": 65.0, "cost_per_unit_distance": 1.0, "unit": "baskets/day"},
        {"source_department": "DEP_04_WELD", "target_department": "DEP_06_PAINT", "quantity": 60.0, "cost_per_unit_distance": 1.2, "unit": "frames/day"},
        {"source_department": "DEP_05_CLEAN", "target_department": "DEP_07_SUB1", "quantity": 55.0, "cost_per_unit_distance": 1.0, "unit": "crates/day"},
        {"source_department": "DEP_06_PAINT", "target_department": "DEP_07_SUB1", "quantity": 55.0, "cost_per_unit_distance": 1.1, "unit": "frames/day"},
        {"source_department": "DEP_07_SUB1", "target_department": "DEP_09_ASSY", "quantity": 75.0, "cost_per_unit_distance": 1.4, "unit": "modules/day"},
        {"source_department": "DEP_08_SUB2", "target_department": "DEP_09_ASSY", "quantity": 75.0, "cost_per_unit_distance": 1.2, "unit": "modules/day"},
        {"source_department": "DEP_09_ASSY", "target_department": "DEP_10_METRO", "quantity": 80.0, "cost_per_unit_distance": 1.1, "unit": "units/day"},
        {"source_department": "DEP_10_METRO", "target_department": "DEP_11_PACK", "quantity": 78.0, "cost_per_unit_distance": 1.0, "unit": "units/day"},
        {"source_department": "DEP_11_PACK", "target_department": "DEP_12_SHIP", "quantity": 78.0, "cost_per_unit_distance": 1.0, "unit": "pallets/day"},
    ]

    relationships = [
        {"department_a": "DEP_01_GATE", "department_b": "DEP_02_PRESS", "relationship_type": "A", "score": 16.0, "reason": "Immediate material supply"},
        {"department_a": "DEP_09_ASSY", "department_b": "DEP_10_METRO", "relationship_type": "A", "score": 16.0, "reason": "100% end-of-line testing"},
        {"department_a": "DEP_11_PACK", "department_b": "DEP_12_SHIP", "relationship_type": "A", "score": 16.0, "reason": "Packed inventory direct load"},
        {"department_a": "DEP_02_PRESS", "department_b": "DEP_10_METRO", "relationship_type": "X", "score": -8.0, "reason": "Vibration isolation between stamping and metrology"},
    ]

    reserved_zones = [
        {
            "id": "RZ_CENTRAL_SPINE",
            "type": "aisle_corridor",
            "bounding_box": {
                "x_min": 75.0,
                "y_min": 0.0,
                "x_max": 85.0,
                "y_max": 100.0
            },
            "strict": True
        }
    ]

    constraints = [
        {"id": "C_NON_OVERLAP", "type": "non_overlapping", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "Strict physical boundary non-overlap"},
        {"id": "C_BOUNDARY", "type": "boundary", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "All departments strictly within facility boundaries"},
        {"id": "C_VIB_SEP", "type": "min_distance", "involved_departments": ["DEP_02_PRESS", "DEP_10_METRO"], "parameters": {"distance": 35.0}, "classification": "soft", "penalty": 4000.0, "description": "Vibration buffer between press and optical metrology"},
    ]

    return {
        "id": "CONSTRAINED_FACTORY_12",
        "name": "Synthetic Constrained Plant with Spine Corridor & Fixed Dock (12 Departments)",
        "facility": {
            "id": "FAC_CONST_12",
            "name": "Constrained Industrial Facility",
            "width": 160.0,
            "height": 100.0,
            "area": 16000.0,
            "reserved_zones": reserved_zones,
            "metadata": {"synthetic": True, "created_for": "Phase 13 Industrial Validation"}
        },
        "departments": departments,
        "flows": flows,
        "relationships": relationships,
        "constraints": constraints,
        "metadata": {
            "is_synthetic": True,
            "validation_suite": "Phase 13 Industrial Benchmark Suite",
            "density_category": "constrained_mixed",
            "department_count": 12,
            "target_utilization": 0.8125,
        }
    }


def build_logistics_factory_15():
    """Build synthetic LOGISTICS_FACTORY_15 benchmark problem with asymmetric and directional flows."""
    departments = [
        {"id": "DEP_01_INB", "name": "Primary Inbound Docks", "required_area": 1200.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_02_BULK", "name": "Bulk High-Bay Storage", "required_area": 2000.0, "min_width": 30.0, "max_width": 80.0, "min_height": 25.0, "max_height": 70.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_03_DEVAN", "name": "De-Vanning & De-Palletizing", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_04_KITTING", "name": "Component Kitting & Sort", "required_area": 1100.0, "min_width": 18.0, "max_width": 55.0, "min_height": 18.0, "max_height": 55.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_05_SMT1", "name": "Surface Mount Line 1", "required_area": 1000.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_06_SMT2", "name": "Surface Mount Line 2", "required_area": 1000.0, "min_width": 18.0, "max_width": 50.0, "min_height": 18.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_07_ROBOT", "name": "Robotic Insertion Cell", "required_area": 800.0, "min_width": 15.0, "max_width": 45.0, "min_height": 15.0, "max_height": 45.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_08_WAVE", "name": "Selective Wave Soldering", "required_area": 800.0, "min_width": 15.0, "max_width": 45.0, "min_height": 15.0, "max_height": 45.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_09_TEST", "name": "Automated ICT & Burn-in", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_10_FINAL", "name": "Box-Build Final Assembly", "required_area": 1300.0, "min_width": 20.0, "max_width": 60.0, "min_height": 20.0, "max_height": 60.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_11_PACK", "name": "Retail Packaging Line", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_12_FG", "name": "Finished Goods Automated Bay", "required_area": 1500.0, "min_width": 22.0, "max_width": 65.0, "min_height": 22.0, "max_height": 65.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.5},
        {"id": "DEP_13_DISP", "name": "Cross-Dock Dispatch Bays", "required_area": 900.0, "min_width": 15.0, "max_width": 50.0, "min_height": 15.0, "max_height": 50.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.2},
        {"id": "DEP_14_RET", "name": "Reverse Logistics & RMA", "required_area": 500.0, "min_width": 12.0, "max_width": 35.0, "min_height": 12.0, "max_height": 35.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
        {"id": "DEP_15_MAINT", "name": "Facility Maintenance Central", "required_area": 500.0, "min_width": 12.0, "max_width": 35.0, "min_height": 12.0, "max_height": 35.0, "min_aspect_ratio": 1.0, "max_aspect_ratio": 2.0},
    ]

    # Asymmetric directional flows
    flows = [
        {"source_department": "DEP_01_INB", "target_department": "DEP_02_BULK", "quantity": 140.0, "cost_per_unit_distance": 1.0, "unit": "pallets/day"},
        {"source_department": "DEP_02_BULK", "target_department": "DEP_03_DEVAN", "quantity": 90.0, "cost_per_unit_distance": 1.1, "unit": "pallets/day"},
        {"source_department": "DEP_03_DEVAN", "target_department": "DEP_04_KITTING", "quantity": 85.0, "cost_per_unit_distance": 1.0, "unit": "totes/day"},
        {"source_department": "DEP_04_KITTING", "target_department": "DEP_05_SMT1", "quantity": 40.0, "cost_per_unit_distance": 1.2, "unit": "reels/day"},
        {"source_department": "DEP_04_KITTING", "target_department": "DEP_06_SMT2", "quantity": 40.0, "cost_per_unit_distance": 1.2, "unit": "reels/day"},
        # Empty tote return reverse flow (asymmetric volume)
        {"source_department": "DEP_05_SMT1", "target_department": "DEP_03_DEVAN", "quantity": 15.0, "cost_per_unit_distance": 0.5, "unit": "empty_totes/day"},
        {"source_department": "DEP_06_SMT2", "target_department": "DEP_03_DEVAN", "quantity": 15.0, "cost_per_unit_distance": 0.5, "unit": "empty_totes/day"},
        {"source_department": "DEP_05_SMT1", "target_department": "DEP_07_ROBOT", "quantity": 38.0, "cost_per_unit_distance": 1.0, "unit": "pcb_magazines/day"},
        {"source_department": "DEP_06_SMT2", "target_department": "DEP_07_ROBOT", "quantity": 38.0, "cost_per_unit_distance": 1.0, "unit": "pcb_magazines/day"},
        {"source_department": "DEP_07_ROBOT", "target_department": "DEP_08_WAVE", "quantity": 72.0, "cost_per_unit_distance": 1.1, "unit": "carriers/day"},
        {"source_department": "DEP_08_WAVE", "target_department": "DEP_09_TEST", "quantity": 70.0, "cost_per_unit_distance": 1.0, "unit": "carriers/day"},
        {"source_department": "DEP_09_TEST", "target_department": "DEP_10_FINAL", "quantity": 68.0, "cost_per_unit_distance": 1.3, "unit": "tested_boards/day"},
        # RMA test feedback flow
        {"source_department": "DEP_14_RET", "target_department": "DEP_09_TEST", "quantity": 10.0, "cost_per_unit_distance": 1.0, "unit": "returns/day"},
        {"source_department": "DEP_10_FINAL", "target_department": "DEP_11_PACK", "quantity": 80.0, "cost_per_unit_distance": 1.1, "unit": "devices/day"},
        {"source_department": "DEP_11_PACK", "target_department": "DEP_12_FG", "quantity": 80.0, "cost_per_unit_distance": 1.0, "unit": "cartons/day"},
        {"source_department": "DEP_12_FG", "target_department": "DEP_13_DISP", "quantity": 110.0, "cost_per_unit_distance": 1.0, "unit": "pallets/day"},
    ]

    relationships = [
        {"department_a": "DEP_01_INB", "department_b": "DEP_02_BULK", "relationship_type": "A", "score": 16.0, "reason": "Immediate intake high-bay feed"},
        {"department_a": "DEP_12_FG", "department_b": "DEP_13_DISP", "relationship_type": "A", "score": 16.0, "reason": "Direct loading to dispatch bay"},
        {"department_a": "DEP_10_FINAL", "department_b": "DEP_11_PACK", "relationship_type": "A", "score": 16.0, "reason": "Continuous assembly offload"},
        {"department_a": "DEP_01_INB", "department_b": "DEP_13_DISP", "relationship_type": "O", "score": 2.0, "reason": "Facility exterior perimeter layout"},
    ]

    constraints = [
        {"id": "C_NON_OVERLAP", "type": "non_overlapping", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "Strict physical boundary non-overlap"},
        {"id": "C_BOUNDARY", "type": "boundary", "involved_departments": [], "classification": "hard", "penalty": 10000.0, "description": "All departments strictly within facility boundaries"},
    ]

    return {
        "id": "LOGISTICS_FACTORY_15",
        "name": "Synthetic High-Throughput Electronics Logistics & Assembly Plant (15 Departments)",
        "facility": {
            "id": "FAC_LOG_15",
            "name": "Electronics Contract Assembly Facility",
            "width": 200.0,
            "height": 90.0,
            "area": 18000.0,
            "metadata": {"synthetic": True, "created_for": "Phase 13 Industrial Validation"}
        },
        "departments": departments,
        "flows": flows,
        "relationships": relationships,
        "constraints": constraints,
        "metadata": {
            "is_synthetic": True,
            "validation_suite": "Phase 13 Industrial Benchmark Suite",
            "density_category": "high_throughput_logistics",
            "department_count": 15,
            "target_utilization": 0.85,
        }
    }


def main():
    benchmarks = [
        build_high_density_15(),
        build_high_density_20(),
        build_constrained_factory_12(),
        build_logistics_factory_15(),
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filenames = [
        "synthetic_high_density_15.json",
        "synthetic_high_density_20.json",
        "synthetic_constrained_factory_12.json",
        "synthetic_logistics_factory_15.json",
    ]

    for data, fname in zip(benchmarks, filenames):
        out_path = DATA_DIR / fname
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Generated {fname}: {data['id']} (Depts: {len(data['departments'])}, Area: {data['facility']['area']}m2)")


if __name__ == "__main__":
    main()
