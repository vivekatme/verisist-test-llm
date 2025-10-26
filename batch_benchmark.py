#!/usr/bin/env python3
"""
Batch benchmark script - Process multiple documents and generate consolidated results.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def find_pdf_files(directory: str) -> list:
    """Find all PDF and image files in directory"""
    pdf_dir = Path(directory)
    if not pdf_dir.exists():
        return []

    # Support PDF and common image formats
    patterns = ["*.pdf", "*.PDF", "*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG"]
    files = []

    for pattern in patterns:
        files.extend(pdf_dir.glob(pattern))

    return sorted([str(f) for f in files])


def run_benchmark_for_file(file_path: str, output_dir: str) -> dict:
    """Run comprehensive benchmark for a single file"""
    print(f"\n{'=' * 80}")
    print(f"Processing: {Path(file_path).name}")
    print('=' * 80)

    try:
        # Run comprehensive benchmark using the same Python interpreter
        result = subprocess.run(
            [sys.executable, "comprehensive_benchmark.py", file_path],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes max
        )

        if result.returncode != 0:
            print(f"❌ Benchmark failed:")
            print(result.stderr)
            return {
                "file": file_path,
                "status": "failed",
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }

        # Find the generated results file (most recent comprehensive_results_*.json)
        # Results are now saved in results/ directory
        results_files = sorted(Path("results").glob("comprehensive_results_*.json"),
                              key=os.path.getmtime, reverse=True)

        if not results_files:
            return {
                "file": file_path,
                "status": "failed",
                "error": "No results file generated",
                "timestamp": datetime.now().isoformat()
            }

        latest_result = results_files[0]

        # Move to output directory with descriptive name
        file_basename = Path(file_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"results_{file_basename}_{timestamp}.json"
        output_path = Path(output_dir) / new_name

        # Copy the results file
        with open(latest_result, 'r') as f:
            results_data = json.load(f)

        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        # Clean up original
        latest_result.unlink()

        print(f"✅ Results saved to: {output_path}")

        return {
            "file": file_path,
            "status": "success",
            "results_file": str(output_path),
            "timestamp": datetime.now().isoformat(),
            "combinations_tested": results_data.get("total_combinations", 0)
        }

    except subprocess.TimeoutExpired:
        return {
            "file": file_path,
            "status": "timeout",
            "error": "Benchmark exceeded 30 minute timeout",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "file": file_path,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 batch_benchmark.py <directory_with_pdfs>")
        print("\nEXAMPLE:")
        print("  python3 batch_benchmark.py ~/Desktop/test-docs")
        print("\nNOTE:")
        print("  - Processes all PDF and image files in the directory")
        print("  - Generates individual results for each document")
        print("  - Creates consolidated HTML dashboard for visualization")
        return

    input_dir = os.path.expanduser(sys.argv[1])

    if not os.path.exists(input_dir):
        print(f"❌ Directory not found: {input_dir}")
        return

    # Find all files
    files = find_pdf_files(input_dir)

    if not files:
        print(f"❌ No PDF or image files found in: {input_dir}")
        return

    print("\n" + "=" * 80)
    print("  BATCH BENCHMARK: Multiple Documents")
    print("=" * 80)
    print(f"\n📁 Input Directory: {input_dir}")
    print(f"📄 Files Found: {len(files)}")
    for i, f in enumerate(files, 1):
        print(f"   {i}. {Path(f).name}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"batch_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📂 Output Directory: {output_dir}")

    # Process each file
    batch_summary = {
        "batch_timestamp": datetime.now().isoformat(),
        "input_directory": input_dir,
        "total_files": len(files),
        "output_directory": output_dir,
        "results": []
    }

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {Path(file_path).name}")

        result = run_benchmark_for_file(file_path, output_dir)
        batch_summary["results"].append(result)

        # Save incremental batch summary
        summary_file = Path(output_dir) / "batch_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(batch_summary, f, indent=2)

    # Print final summary
    print("\n" + "=" * 80)
    print("  BATCH SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in batch_summary["results"] if r["status"] == "success")
    failed = sum(1 for r in batch_summary["results"] if r["status"] != "success")

    print(f"\n✅ Successful: {successful}/{len(files)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(files)}")
        print("\nFailed files:")
        for result in batch_summary["results"]:
            if result["status"] != "success":
                print(f"   - {Path(result['file']).name}: {result.get('error', 'Unknown error')}")

    print(f"\n📊 Results Directory: {output_dir}")
    print(f"📋 Summary File: {summary_file}")

    # Generate HTML dashboard
    print(f"\n🎨 Generating HTML dashboard...")
    try:
        subprocess.run(
            ["python", "generate_dashboard.py", output_dir],
            check=True
        )
        print(f"✅ Dashboard generated: {output_dir}/dashboard.html")
        print(f"\n🌐 Open dashboard in browser:")
        print(f"   open {output_dir}/dashboard.html")
    except Exception as e:
        print(f"⚠️  Dashboard generation failed: {e}")
        print(f"   Run manually: python generate_dashboard.py {output_dir}")

    print("=" * 80)


if __name__ == "__main__":
    main()
