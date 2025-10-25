#!/usr/bin/env python3
"""
Evaluation script for comprehensive benchmark results.
Compares all OCR × LLM combinations and provides recommendations.
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
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def load_results(filepath: str) -> dict:
    """Load benchmark results from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_accuracy_score(result: dict) -> dict:
    """Calculate accuracy metrics for a combination"""
    extraction = result.get("extraction", {})

    score = {
        "has_extraction": extraction is not None and len(extraction) > 0,
        "item_count": 0,
        "has_title": bool(extraction.get("title")),
        "has_patient_name": bool(extraction.get("patientName")),
        "has_date": bool(extraction.get("documentDate")),
        "has_lab_name": bool(extraction.get("labName")),
        "has_error": bool(result.get("error"))
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

    if score["has_error"]:
        completeness = 0

    score["completeness"] = completeness

    return score


def print_performance_matrix(data: dict) -> None:
    """Print performance comparison matrix"""
    print(f"\n{Colors.BOLD}⏱️  PERFORMANCE MATRIX (Total Time in seconds){Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])

    # Get unique OCR engines and LLM models
    ocr_engines = sorted(set(c["ocr_display"] for c in combinations))
    llm_models = sorted(set(c["llm_display"] for c in combinations))

    # Print header
    print(f"\n{'OCR Engine':25}", end="")
    for llm in llm_models:
        print(f"{llm:20}", end="")
    print()
    print("─" * 100)

    # Print rows
    for ocr in ocr_engines:
        print(f"{ocr:25}", end="")
        for llm in llm_models:
            # Find matching combination
            match = next((c for c in combinations
                         if c["ocr_display"] == ocr and c["llm_display"] == llm), None)

            if match:
                total_time = match["timings"].get("total", 0)
                error = match.get("error")

                if error:
                    print(f"{Colors.RED}ERROR{Colors.RESET:13}", end="")
                else:
                    # Color code based on speed
                    if total_time < 30:
                        color = Colors.GREEN
                    elif total_time < 60:
                        color = Colors.YELLOW
                    else:
                        color = Colors.RED

                    print(f"{color}{total_time:6.2f}s{Colors.RESET:13}", end="")
            else:
                print(f"{'N/A':20}", end="")

        print()


def print_accuracy_matrix(data: dict) -> None:
    """Print accuracy comparison matrix"""
    print(f"\n{Colors.BOLD}🎯 ACCURACY MATRIX (Items Extracted){Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])

    # Get unique OCR engines and LLM models
    ocr_engines = sorted(set(c["ocr_display"] for c in combinations))
    llm_models = sorted(set(c["llm_display"] for c in combinations))

    # Print header
    print(f"\n{'OCR Engine':25}", end="")
    for llm in llm_models:
        print(f"{llm:20}", end="")
    print()
    print("─" * 100)

    # Print rows
    for ocr in ocr_engines:
        print(f"{ocr:25}", end="")
        for llm in llm_models:
            # Find matching combination
            match = next((c for c in combinations
                         if c["ocr_display"] == ocr and c["llm_display"] == llm), None)

            if match:
                score = generate_accuracy_score(match)
                item_count = score["item_count"]
                error = match.get("error")

                if error:
                    print(f"{Colors.RED}ERROR{Colors.RESET:13}", end="")
                else:
                    # Color code based on item count
                    if item_count >= 10:
                        color = Colors.GREEN
                    elif item_count >= 5:
                        color = Colors.YELLOW
                    else:
                        color = Colors.RED

                    print(f"{color}{item_count:3} items{Colors.RESET:13}", end="")
            else:
                print(f"{'N/A':20}", end="")

        print()


def print_completeness_matrix(data: dict) -> None:
    """Print completeness score matrix"""
    print(f"\n{Colors.BOLD}📊 COMPLETENESS SCORE MATRIX (0-100){Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])

    # Get unique OCR engines and LLM models
    ocr_engines = sorted(set(c["ocr_display"] for c in combinations))
    llm_models = sorted(set(c["llm_display"] for c in combinations))

    # Print header
    print(f"\n{'OCR Engine':25}", end="")
    for llm in llm_models:
        print(f"{llm:20}", end="")
    print()
    print("─" * 100)

    # Print rows
    for ocr in ocr_engines:
        print(f"{ocr:25}", end="")
        for llm in llm_models:
            # Find matching combination
            match = next((c for c in combinations
                         if c["ocr_display"] == ocr and c["llm_display"] == llm), None)

            if match:
                score = generate_accuracy_score(match)
                completeness = score["completeness"]
                error = match.get("error")

                if error:
                    print(f"{Colors.RED}ERROR{Colors.RESET:13}", end="")
                else:
                    # Color code based on completeness
                    if completeness >= 80:
                        color = Colors.GREEN
                    elif completeness >= 60:
                        color = Colors.YELLOW
                    else:
                        color = Colors.RED

                    print(f"{color}{completeness:3}/100{Colors.RESET:13}", end="")
            else:
                print(f"{'N/A':20}", end="")

        print()


def find_best_combinations(data: dict) -> dict:
    """Find best combinations by different criteria"""
    combinations = data.get("combinations", [])

    # Filter out errors
    valid_combinations = [c for c in combinations if not c.get("error")]

    if not valid_combinations:
        return {
            "fastest": None,
            "most_accurate": None,
            "best_balanced": None
        }

    # Find fastest
    fastest = min(valid_combinations, key=lambda c: c["timings"].get("total", float('inf')))

    # Find most accurate (by item count)
    most_accurate = max(valid_combinations,
                        key=lambda c: generate_accuracy_score(c)["item_count"])

    # Find best balanced (completeness / time ratio)
    def balance_score(c):
        score = generate_accuracy_score(c)
        time = c["timings"].get("total", 1)
        return score["completeness"] / time if time > 0 else 0

    best_balanced = max(valid_combinations, key=balance_score)

    return {
        "fastest": fastest,
        "most_accurate": most_accurate,
        "best_balanced": best_balanced
    }


def print_recommendations(data: dict) -> None:
    """Print recommendations based on analysis"""
    print(f"\n{Colors.BOLD}💡 RECOMMENDATIONS{Colors.RESET}")
    print("=" * 100)

    best = find_best_combinations(data)

    if not best["fastest"]:
        print(f"\n{Colors.RED}❌ No valid combinations found (all errored){Colors.RESET}")
        return

    # Fastest
    fastest = best["fastest"]
    fastest_score = generate_accuracy_score(fastest)
    print(f"\n{Colors.GREEN}🚀 FASTEST COMBINATION:{Colors.RESET}")
    print(f"   OCR: {fastest['ocr_display']}")
    print(f"   LLM: {fastest['llm_display']}")
    print(f"   Time: {fastest['timings']['total']:.2f}s")
    print(f"   Items: {fastest_score['item_count']}")
    print(f"   Completeness: {fastest_score['completeness']}/100")
    print(f"   {Colors.CYAN}Best for: Speed-critical applications{Colors.RESET}")

    # Most accurate
    accurate = best["most_accurate"]
    accurate_score = generate_accuracy_score(accurate)
    print(f"\n{Colors.BLUE}🎯 MOST ACCURATE COMBINATION:{Colors.RESET}")
    print(f"   OCR: {accurate['ocr_display']}")
    print(f"   LLM: {accurate['llm_display']}")
    print(f"   Time: {accurate['timings']['total']:.2f}s")
    print(f"   Items: {accurate_score['item_count']}")
    print(f"   Completeness: {accurate_score['completeness']}/100")
    print(f"   {Colors.CYAN}Best for: Maximum data extraction{Colors.RESET}")

    # Best balanced
    balanced = best["best_balanced"]
    balanced_score = generate_accuracy_score(balanced)
    print(f"\n{Colors.MAGENTA}⚖️  BEST BALANCED COMBINATION:{Colors.RESET}")
    print(f"   OCR: {balanced['ocr_display']}")
    print(f"   LLM: {balanced['llm_display']}")
    print(f"   Time: {balanced['timings']['total']:.2f}s")
    print(f"   Items: {balanced_score['item_count']}")
    print(f"   Completeness: {balanced_score['completeness']}/100")
    print(f"   Efficiency: {balanced_score['completeness'] / balanced['timings']['total']:.2f} points/sec")
    print(f"   {Colors.CYAN}Best for: Production use (speed + accuracy){Colors.RESET}")


def print_ocr_comparison(data: dict) -> None:
    """Compare OCR engines across all LLMs"""
    print(f"\n{Colors.BOLD}🔍 OCR ENGINE COMPARISON{Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])
    ocr_results = data.get("ocr_results", {})

    # Group by OCR engine
    ocr_stats = {}
    for combo in combinations:
        ocr = combo["ocr_display"]
        if ocr not in ocr_stats:
            ocr_stats[ocr] = {
                "times": [],
                "item_counts": [],
                "errors": 0,
                "ocr_time": combo["timings"].get("ocr", 0)
            }

        if combo.get("error"):
            ocr_stats[ocr]["errors"] += 1
        else:
            ocr_stats[ocr]["times"].append(combo["timings"].get("total", 0))
            score = generate_accuracy_score(combo)
            ocr_stats[ocr]["item_counts"].append(score["item_count"])

    # Print comparison
    for ocr, stats in sorted(ocr_stats.items()):
        print(f"\n{Colors.BOLD}{ocr}:{Colors.RESET}")
        print(f"   OCR Time: {stats['ocr_time']:.2f}s")

        if stats["times"]:
            avg_time = sum(stats["times"]) / len(stats["times"])
            avg_items = sum(stats["item_counts"]) / len(stats["item_counts"])
            print(f"   Avg Total Time: {avg_time:.2f}s")
            print(f"   Avg Items Extracted: {avg_items:.1f}")
        else:
            print(f"   {Colors.RED}All combinations errored{Colors.RESET}")

        if stats["errors"] > 0:
            print(f"   {Colors.YELLOW}Errors: {stats['errors']}{Colors.RESET}")


def print_llm_comparison(data: dict) -> None:
    """Compare LLM models across all OCR engines"""
    print(f"\n{Colors.BOLD}🤖 LLM MODEL COMPARISON{Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])

    # Group by LLM model
    llm_stats = {}
    for combo in combinations:
        llm = combo["llm_display"]
        llm_type = combo.get("llm_type", "unknown")

        if llm not in llm_stats:
            llm_stats[llm] = {
                "type": llm_type,
                "llm_times": [],
                "item_counts": [],
                "errors": 0
            }

        if combo.get("error"):
            llm_stats[llm]["errors"] += 1
        else:
            llm_stats[llm]["llm_times"].append(combo["timings"].get("llm_call", 0))
            score = generate_accuracy_score(combo)
            llm_stats[llm]["item_counts"].append(score["item_count"])

    # Print comparison
    for llm, stats in sorted(llm_stats.items()):
        print(f"\n{Colors.BOLD}{llm}{Colors.RESET} ({stats['type']})")

        if stats["llm_times"]:
            avg_llm_time = sum(stats["llm_times"]) / len(stats["llm_times"])
            avg_items = sum(stats["item_counts"]) / len(stats["item_counts"])
            print(f"   Avg LLM Time: {avg_llm_time:.2f}s")
            print(f"   Avg Items Extracted: {avg_items:.1f}")

            # Calculate efficiency
            efficiency = avg_items / avg_llm_time if avg_llm_time > 0 else 0
            print(f"   Efficiency: {efficiency:.2f} items/sec")
        else:
            print(f"   {Colors.RED}All combinations errored{Colors.RESET}")

        if stats["errors"] > 0:
            print(f"   {Colors.YELLOW}Errors: {stats['errors']}{Colors.RESET}")


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 evaluate_comprehensive.py <comprehensive_results.json>")
        print("\nEXAMPLE:")
        print("  python3 evaluate_comprehensive.py comprehensive_results_20250125_143022.json")
        return

    results_file = sys.argv[1]

    if not Path(results_file).exists():
        print(f"❌ File not found: {results_file}")
        return

    # Load results
    data = load_results(results_file)

    print("\n" + "=" * 100)
    print(f"  {Colors.BOLD}COMPREHENSIVE EVALUATION: OCR × LLM Analysis{Colors.RESET}")
    print("=" * 100)

    combinations = data.get("combinations", [])
    print(f"\n📊 Analyzed {len(combinations)} combinations")
    print(f"   OCR Engines: {data.get('ocr_engines_tested', 0)}")
    print(f"   LLM Models: {data.get('llm_models_tested', 0)}")
    print(f"   Document: {data.get('document', 'N/A')}")

    # Print all analysis
    print_performance_matrix(data)
    print_accuracy_matrix(data)
    print_completeness_matrix(data)
    print_recommendations(data)
    print_ocr_comparison(data)
    print_llm_comparison(data)

    print("\n" + "=" * 100)
    print(f"{Colors.GREEN}✅ Evaluation complete!{Colors.RESET}")
    print("=" * 100)


if __name__ == "__main__":
    main()
