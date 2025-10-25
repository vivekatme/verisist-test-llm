#!/usr/bin/env python3
"""
Evaluation script to compare 3B vs 7B model results.
Shows differences in accuracy, extracted parameters, and performance.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def load_benchmark_results(filepath: str) -> dict:
    """Load benchmark results from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_validation(model1: dict, model2: dict) -> None:
    """Compare validation results between two models"""
    val1 = model1.get("validation", {})
    val2 = model2.get("validation", {})

    print(f"\n{Colors.BOLD}📋 VALIDATION COMPARISON{Colors.RESET}")
    print("─" * 80)

    # Compare fields
    fields = ["is_health_document", "document_type", "confidence", "lab_name", "document_date"]

    for field in fields:
        v1 = val1.get(field)
        v2 = val2.get(field)

        if v1 == v2:
            status = f"{Colors.GREEN}✓ Match{Colors.RESET}"
        else:
            status = f"{Colors.RED}✗ Different{Colors.RESET}"

        print(f"{field:25} {status}")
        print(f"  3B: {v1}")
        print(f"  7B: {v2}")


def compare_parameters(params1: List[Dict], params2: List[Dict]) -> None:
    """Compare extracted parameters between two models"""
    print(f"\n{Colors.BOLD}📊 PARAMETER EXTRACTION COMPARISON{Colors.RESET}")
    print("─" * 80)

    # Create lookup by parameter name
    p1_dict = {p["name"]: p for p in params1}
    p2_dict = {p["name"]: p for p in params2}

    all_param_names = sorted(set(p1_dict.keys()) | set(p2_dict.keys()))

    print(f"\nTotal Parameters: 3B extracted {len(params1)}, 7B extracted {len(params2)}")

    # Compare each parameter
    differences = []

    for param_name in all_param_names:
        p1 = p1_dict.get(param_name)
        p2 = p2_dict.get(param_name)

        if not p1:
            differences.append({
                "name": param_name,
                "issue": "Missing in 3B",
                "3b": None,
                "7b": p2
            })
        elif not p2:
            differences.append({
                "name": param_name,
                "issue": "Missing in 7B",
                "3b": p1,
                "7b": None
            })
        else:
            # Both exist, compare values
            value_match = p1.get("value") == p2.get("value")
            unit_match = p1.get("unit") == p2.get("unit")
            status_match = p1.get("status") == p2.get("status")
            range_match = p1.get("referenceRange") == p2.get("referenceRange")

            if not (value_match and unit_match and status_match and range_match):
                differences.append({
                    "name": param_name,
                    "issue": "Different values",
                    "3b": p1,
                    "7b": p2,
                    "value_match": value_match,
                    "unit_match": unit_match,
                    "status_match": status_match,
                    "range_match": range_match
                })

    # Show results
    if not differences:
        print(f"\n{Colors.GREEN}✅ All parameters match perfectly!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Found {len(differences)} differences:{Colors.RESET}\n")

        for i, diff in enumerate(differences, 1):
            print(f"{i}. {Colors.BOLD}{diff['name']}{Colors.RESET}")
            print(f"   Issue: {diff['issue']}")

            if diff.get("3b"):
                p3b = diff["3b"]
                print(f"   3B: value={p3b.get('value')}, unit={p3b.get('unit')}, status={p3b.get('status')}, range={p3b.get('referenceRange')}")

            if diff.get("7b"):
                p7b = diff["7b"]
                print(f"   7B: value={p7b.get('value')}, unit={p7b.get('unit')}, status={p7b.get('status')}, range={p7b.get('referenceRange')}")

            if diff.get("value_match") is not None:
                matches = []
                if diff["value_match"]:
                    matches.append(f"{Colors.GREEN}value{Colors.RESET}")
                else:
                    matches.append(f"{Colors.RED}value{Colors.RESET}")

                if diff["unit_match"]:
                    matches.append(f"{Colors.GREEN}unit{Colors.RESET}")
                else:
                    matches.append(f"{Colors.RED}unit{Colors.RESET}")

                if diff["status_match"]:
                    matches.append(f"{Colors.GREEN}status{Colors.RESET}")
                else:
                    matches.append(f"{Colors.RED}status{Colors.RESET}")

                if diff["range_match"]:
                    matches.append(f"{Colors.GREEN}range{Colors.RESET}")
                else:
                    matches.append(f"{Colors.RED}range{Colors.RESET}")

                print(f"   Fields: {', '.join(matches)}")

            print()


def compare_medications(meds1: List[Dict], meds2: List[Dict]) -> None:
    """Compare extracted medications between two models"""
    print(f"\n{Colors.BOLD}💊 MEDICATION EXTRACTION COMPARISON{Colors.RESET}")
    print("─" * 80)

    m1_dict = {m["name"]: m for m in meds1}
    m2_dict = {m["name"]: m for m in meds2}

    all_med_names = sorted(set(m1_dict.keys()) | set(m2_dict.keys()))

    print(f"\nTotal Medications: 3B extracted {len(meds1)}, 7B extracted {len(meds2)}")

    differences = []

    for med_name in all_med_names:
        m1 = m1_dict.get(med_name)
        m2 = m2_dict.get(med_name)

        if not m1:
            differences.append({"name": med_name, "issue": "Missing in 3B", "3b": None, "7b": m2})
        elif not m2:
            differences.append({"name": med_name, "issue": "Missing in 7B", "3b": m1, "7b": None})
        else:
            if m1 != m2:
                differences.append({"name": med_name, "issue": "Different", "3b": m1, "7b": m2})

    if not differences:
        print(f"\n{Colors.GREEN}✅ All medications match perfectly!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Found {len(differences)} differences:{Colors.RESET}\n")

        for i, diff in enumerate(differences, 1):
            print(f"{i}. {Colors.BOLD}{diff['name']}{Colors.RESET}")
            print(f"   Issue: {diff['issue']}")
            if diff.get("3b"):
                print(f"   3B: {diff['3b']}")
            if diff.get("7b"):
                print(f"   7B: {diff['7b']}")
            print()


def generate_accuracy_score(model: dict) -> dict:
    """Calculate accuracy metrics for a model"""
    extraction = model.get("extraction", {})

    score = {
        "has_extraction": extraction is not None and len(extraction) > 0,
        "item_count": 0,
        "has_title": bool(extraction.get("title")),
        "has_patient_name": bool(extraction.get("patientName")),
        "has_date": bool(extraction.get("documentDate")),
        "has_lab_name": bool(extraction.get("labName")),
    }

    if "parameters" in extraction:
        score["item_count"] = len(extraction["parameters"])
        score["type"] = "LAB_REPORT"
    elif "medications" in extraction:
        score["item_count"] = len(extraction["medications"])
        score["type"] = "PRESCRIPTION"

    # Calculate completeness score (0-100)
    completeness = 0
    if score["has_extraction"]:
        completeness += 20
    if score["item_count"] > 0:
        completeness += 40
    if score["has_title"]:
        completeness += 10
    if score["has_patient_name"]:
        completeness += 10
    if score["has_date"]:
        completeness += 10
    if score["has_lab_name"]:
        completeness += 10

    score["completeness"] = completeness

    return score


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 evaluate_results.py <benchmark_results.json>")
        print("\nEXAMPLE:")
        print("  python3 evaluate_results.py benchmark_results_20250125_143022.json")
        return

    results_file = sys.argv[1]

    if not Path(results_file).exists():
        print(f"❌ File not found: {results_file}")
        return

    # Load results
    data = load_benchmark_results(results_file)

    print("\n" + "=" * 80)
    print(f"  {Colors.BOLD}MODEL EVALUATION: 3B vs 7B{Colors.RESET}")
    print("=" * 80)

    models = data.get("models", [])

    if len(models) != 2:
        print(f"❌ Expected 2 models, found {len(models)}")
        return

    model_3b = models[0]
    model_7b = models[1]

    # Performance comparison
    print(f"\n{Colors.BOLD}⏱️  PERFORMANCE{Colors.RESET}")
    print("─" * 80)

    ocr_time = data.get("ocr_time", 0)
    time_3b = model_3b.get("timings", {}).get("llm_call", 0)
    time_7b = model_7b.get("timings", {}).get("llm_call", 0)
    total_3b = model_3b.get("timings", {}).get("total", 0)
    total_7b = model_7b.get("timings", {}).get("total", 0)

    print(f"OCR (shared):        {ocr_time:.2f}s")
    print(f"3B LLM call:         {time_3b:.2f}s")
    print(f"7B LLM call:         {time_7b:.2f}s")
    print(f"─" * 40)
    print(f"3B Total:            {Colors.GREEN}{total_3b:.2f}s{Colors.RESET}")
    print(f"7B Total:            {total_7b:.2f}s")

    if time_3b > 0 and time_7b > 0:
        speedup = time_7b / time_3b
        time_saved = time_7b - time_3b
        print(f"\n{Colors.CYAN}3B is {speedup:.2f}x faster (saves {time_saved:.2f}s per document){Colors.RESET}")

    # Accuracy comparison
    score_3b = generate_accuracy_score(model_3b)
    score_7b = generate_accuracy_score(model_7b)

    print(f"\n{Colors.BOLD}🎯 ACCURACY METRICS{Colors.RESET}")
    print("─" * 80)
    print(f"Completeness Score:")
    print(f"  3B: {score_3b['completeness']}/100")
    print(f"  7B: {score_7b['completeness']}/100")

    print(f"\nExtracted Items:")
    print(f"  3B: {score_3b['item_count']} items")
    print(f"  7B: {score_7b['item_count']} items")

    # Validation comparison
    compare_validation(model_3b, model_7b)

    # Extraction comparison
    ext_3b = model_3b.get("extraction", {})
    ext_7b = model_7b.get("extraction", {})

    if "parameters" in ext_3b and "parameters" in ext_7b:
        compare_parameters(ext_3b["parameters"], ext_7b["parameters"])
    elif "medications" in ext_3b and "medications" in ext_7b:
        compare_medications(ext_3b["medications"], ext_7b["medications"])

    # Error comparison
    error_3b = model_3b.get("error")
    error_7b = model_7b.get("error")

    if error_3b or error_7b:
        print(f"\n{Colors.BOLD}❌ ERRORS{Colors.RESET}")
        print("─" * 80)
        if error_3b:
            print(f"3B Error: {Colors.RED}{error_3b}{Colors.RESET}")
        if error_7b:
            print(f"7B Error: {Colors.RED}{error_7b}{Colors.RESET}")

    # Final recommendation
    print(f"\n{Colors.BOLD}💡 RECOMMENDATION{Colors.RESET}")
    print("=" * 80)

    accuracy_diff = abs(score_3b['completeness'] - score_7b['completeness'])
    item_diff = abs(score_3b['item_count'] - score_7b['item_count'])

    if accuracy_diff <= 10 and item_diff <= 1:
        print(f"{Colors.GREEN}✅ 3B model recommended:{Colors.RESET}")
        print(f"   - {speedup:.2f}x faster than 7B")
        print(f"   - Similar accuracy (within {accuracy_diff}%)")
        print(f"   - Extracted {score_3b['item_count']} vs {score_7b['item_count']} items")
        print(f"   - Perfect for production!")
    elif score_7b['completeness'] > score_3b['completeness']:
        print(f"{Colors.YELLOW}⚠️  7B model recommended for accuracy:{Colors.RESET}")
        print(f"   - More complete extraction ({score_7b['completeness']}% vs {score_3b['completeness']}%)")
        print(f"   - {time_7b - time_3b:.2f}s slower per document")
        print(f"   - Use if accuracy is critical")
    else:
        print(f"{Colors.CYAN}Both models perform similarly. Choose based on speed requirements.{Colors.RESET}")

    print("=" * 80)


if __name__ == "__main__":
    main()
