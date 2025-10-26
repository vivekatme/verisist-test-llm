#!/usr/bin/env python3
"""
Batch OCR comparison - Process multiple documents and compare all OCR engines.
Generates consolidated HTML dashboard with results grouped by document.
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

    patterns = ["*.pdf", "*.PDF", "*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG"]
    files = []

    for pattern in patterns:
        files.extend(pdf_dir.glob(pattern))

    return sorted([str(f) for f in files])


def run_ocr_for_file(file_path: str) -> dict:
    """Run OCR comparison for a single file"""
    print(f"\n{'=' * 80}")
    print(f"Processing: {Path(file_path).name}")
    print('=' * 80)

    try:
        result = subprocess.run(
            ["python", "ocr_comparison.py", file_path],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )

        if result.returncode != 0:
            print(f"❌ OCR comparison failed:")
            print(result.stderr)
            return {
                "file": file_path,
                "status": "failed",
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }

        # Find the generated JSON file (most recent ocr_comparison_*.json)
        results_files = sorted(Path(".").glob("ocr_comparison_*.json"),
                              key=os.path.getmtime, reverse=True)

        if not results_files:
            return {
                "file": file_path,
                "status": "failed",
                "error": "No results file generated",
                "timestamp": datetime.now().isoformat()
            }

        latest_result = results_files[0]

        # Load the results
        with open(latest_result, 'r') as f:
            results_data = json.load(f)

        # Clean up the JSON file (we'll regenerate HTML later)
        latest_result.unlink()

        print(f"✅ OCR comparison completed")

        return {
            "file": file_path,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "ocr_results": results_data.get("ocr_results", [])
        }

    except subprocess.TimeoutExpired:
        return {
            "file": file_path,
            "status": "timeout",
            "error": "OCR comparison exceeded 10 minute timeout",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "file": file_path,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def generate_batch_html(all_results: list, output_path: str):
    """Generate consolidated HTML dashboard for all documents"""

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch OCR Comparison Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .stat-card h3 {
            font-size: 0.875rem;
            color: #86868b;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .stat-card .value {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .filter-bar {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .filter-bar select {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid #e5e5e7;
            font-size: 0.875rem;
            margin-right: 1rem;
        }

        .document-section {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .document-section h2 {
            color: #667eea;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }

        .ocr-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }

        .ocr-card {
            background: #f9f9fb;
            border-radius: 8px;
            padding: 1.5rem;
        }

        .ocr-card h3 {
            color: #1d1d1f;
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }

        .ocr-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e5e5e7;
        }

        .ocr-stat {
            text-align: center;
        }

        .ocr-stat .label {
            font-size: 0.75rem;
            color: #86868b;
            text-transform: uppercase;
        }

        .ocr-stat .value {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1d1d1f;
        }

        .ocr-text {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.875rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .badge.success {
            background: #d1f4e0;
            color: #0a6640;
        }

        .badge.error {
            background: #ffd3d3;
            color: #c41e3a;
        }

        .badge.fast {
            background: #d1f4e0;
            color: #0a6640;
        }

        .badge.medium {
            background: #fff4cc;
            color: #946c00;
        }

        .badge.slow {
            background: #ffd3d3;
            color: #c41e3a;
        }

        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 2rem;
        }

        .comparison-table th {
            background: #f5f5f7;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e5e7;
        }

        .comparison-table td {
            padding: 1rem;
            border-bottom: 1px solid #e5e5e7;
        }

        .comparison-table tr:hover {
            background: #f9f9fb;
        }

        .expand-btn {
            padding: 0.5rem 1rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
        }

        .expand-btn:hover {
            background: #5568d3;
        }

        .ocr-details {
            display: none;
            margin-top: 1rem;
        }

        .ocr-details.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🔍 Batch OCR Comparison Dashboard</h1>
            <p>Compare OCR engine performance across multiple documents</p>
        </div>
    </div>

    <div class="container">
        <div class="stats-grid" id="stats"></div>

        <div class="filter-bar">
            <label>Filter by Document:</label>
            <select id="doc-filter" onchange="filterDocuments()">
                <option value="">All Documents</option>
            </select>

            <label>Filter by OCR Engine:</label>
            <select id="ocr-filter" onchange="filterDocuments()">
                <option value="">All Engines</option>
            </select>
        </div>

        <div id="documents-container"></div>
    </div>

    <script>
        const RESULTS = """ + json.dumps(all_results, indent=2) + """;

        function initDashboard() {
            // Calculate stats
            const totalDocs = RESULTS.length;
            const successDocs = RESULTS.filter(r => r.status === 'success').length;

            let allOCREngines = new Set();
            let avgTimes = {};

            RESULTS.forEach(doc => {
                if (doc.status === 'success' && doc.ocr_results) {
                    doc.ocr_results.forEach(ocr => {
                        if (ocr.status === 'success') {
                            allOCREngines.add(ocr.engine);
                            if (!avgTimes[ocr.engine]) {
                                avgTimes[ocr.engine] = [];
                            }
                            avgTimes[ocr.engine].push(ocr.time);
                        }
                    });
                }
            });

            // Render stats
            let statsHTML = `
                <div class="stat-card">
                    <h3>Total Documents</h3>
                    <div class="value">${totalDocs}</div>
                </div>
                <div class="stat-card">
                    <h3>Successfully Processed</h3>
                    <div class="value">${successDocs}</div>
                </div>
                <div class="stat-card">
                    <h3>OCR Engines Tested</h3>
                    <div class="value">${allOCREngines.size}</div>
                </div>
            `;

            // Add avg time for fastest engine
            if (Object.keys(avgTimes).length > 0) {
                let fastestEngine = null;
                let fastestTime = Infinity;

                Object.entries(avgTimes).forEach(([engine, times]) => {
                    const avg = times.reduce((a, b) => a + b, 0) / times.length;
                    if (avg < fastestTime) {
                        fastestTime = avg;
                        fastestEngine = engine;
                    }
                });

                statsHTML += `
                    <div class="stat-card">
                        <h3>Fastest Engine</h3>
                        <div class="value">${fastestEngine}</div>
                        <p style="margin-top: 0.5rem; font-size: 0.875rem; color: #86868b;">
                            ${fastestTime.toFixed(2)}s avg
                        </p>
                    </div>
                `;
            }

            document.getElementById('stats').innerHTML = statsHTML;

            // Populate filters
            const docFilter = document.getElementById('doc-filter');
            const ocrFilter = document.getElementById('ocr-filter');

            RESULTS.forEach(doc => {
                const docName = doc.file.split('/').pop();
                docFilter.innerHTML += `<option value="${docName}">${docName}</option>`;
            });

            allOCREngines.forEach(engine => {
                ocrFilter.innerHTML += `<option value="${engine}">${engine}</option>`;
            });

            // Render documents
            renderDocuments();
        }

        function renderDocuments() {
            const container = document.getElementById('documents-container');
            let html = '';

            RESULTS.forEach((doc, docIdx) => {
                const docName = doc.file.split('/').pop();

                if (doc.status !== 'success') {
                    html += `
                        <div class="document-section" data-doc="${docName}">
                            <h2>${docName}</h2>
                            <p style="color: #c41e3a;">Error: ${doc.error || 'Processing failed'}</p>
                        </div>
                    `;
                    return;
                }

                html += `
                    <div class="document-section" data-doc="${docName}">
                        <h2>${docName}</h2>

                        <table class="comparison-table">
                            <thead>
                                <tr>
                                    <th>OCR Engine</th>
                                    <th>Time</th>
                                    <th>Characters</th>
                                    <th>Words</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                doc.ocr_results.forEach((ocr, ocrIdx) => {
                    const timeClass = ocr.time < 5 ? 'fast' : ocr.time < 10 ? 'medium' : 'slow';

                    html += `
                        <tr data-ocr="${ocr.engine}">
                            <td><strong>${ocr.engine}</strong></td>
                    `;

                    if (ocr.status === 'success') {
                        html += `
                            <td><span class="badge ${timeClass}">${ocr.time}s</span></td>
                            <td>${ocr.metadata.character_count}</td>
                            <td>${ocr.metadata.word_count}</td>
                            <td><span class="badge success">Success</span></td>
                            <td><button class="expand-btn" onclick="toggleDetails(${docIdx}, ${ocrIdx})">View Text</button></td>
                        `;
                    } else {
                        html += `
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                            <td><span class="badge error">Error</span></td>
                            <td>-</td>
                        `;
                    }

                    html += '</tr>';

                    // Add hidden details row
                    if (ocr.status === 'success') {
                        html += `
                            <tr>
                                <td colspan="6">
                                    <div class="ocr-details" id="details-${docIdx}-${ocrIdx}">
                                        <div class="ocr-text">${escapeHtml(ocr.text)}</div>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }
                });

                html += `
                            </tbody>
                        </table>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        function toggleDetails(docIdx, ocrIdx) {
            const details = document.getElementById(`details-${docIdx}-${ocrIdx}`);
            details.classList.toggle('active');
        }

        function filterDocuments() {
            const docFilter = document.getElementById('doc-filter').value;
            const ocrFilter = document.getElementById('ocr-filter').value;

            document.querySelectorAll('.document-section').forEach(section => {
                const docName = section.dataset.doc;
                const matchDoc = !docFilter || docName === docFilter;

                if (!matchDoc) {
                    section.style.display = 'none';
                    return;
                }

                section.style.display = 'block';

                // Filter OCR rows within document
                section.querySelectorAll('tr[data-ocr]').forEach(row => {
                    const ocrEngine = row.dataset.ocr;
                    const matchOCR = !ocrFilter || ocrEngine === ocrFilter;
                    row.style.display = matchOCR ? '' : 'none';

                    // Hide corresponding details row
                    const nextRow = row.nextElementSibling;
                    if (nextRow && nextRow.querySelector('.ocr-details')) {
                        nextRow.style.display = matchOCR ? '' : 'none';
                    }
                });
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        initDashboard();
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 batch_ocr_comparison.py <directory_with_pdfs>")
        print("\nEXAMPLE:")
        print("  python3 batch_ocr_comparison.py ~/Desktop/test-docs")
        print("\nNOTE:")
        print("  - Processes all PDF and image files in the directory")
        print("  - Compares all available OCR engines for each document")
        print("  - Generates consolidated HTML dashboard")
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
    print("  BATCH OCR COMPARISON")
    print("=" * 80)
    print(f"\n📁 Input Directory: {input_dir}")
    print(f"📄 Files Found: {len(files)}")
    for i, f in enumerate(files, 1):
        print(f"   {i}. {Path(f).name}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"batch_ocr_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📂 Output Directory: {output_dir}")

    # Process each file
    all_results = []

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {Path(file_path).name}")
        result = run_ocr_for_file(file_path)
        all_results.append(result)

    # Save JSON results
    json_output = Path(output_dir) / "batch_ocr_summary.json"
    with open(json_output, 'w') as f:
        json.dump({
            "batch_timestamp": datetime.now().isoformat(),
            "input_directory": input_dir,
            "total_files": len(files),
            "results": all_results
        }, f, indent=2)

    print(f"\n💾 JSON results saved to: {json_output}")

    # Generate HTML dashboard
    html_output = Path(output_dir) / "ocr_dashboard.html"
    generate_batch_html(all_results, html_output)

    print(f"🌐 HTML dashboard generated: {html_output}")

    # Print summary
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in all_results if r["status"] == "success")
    failed = sum(1 for r in all_results if r["status"] != "success")

    print(f"\n✅ Successful: {successful}/{len(files)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(files)}")

    print(f"\n📊 Dashboard: {html_output}")
    print(f"\n🌐 Open dashboard:")
    print(f"   open {html_output}")
    print("=" * 80)


if __name__ == "__main__":
    main()
