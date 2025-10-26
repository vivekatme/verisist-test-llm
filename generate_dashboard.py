#!/usr/bin/env python3
"""
Generate interactive HTML dashboard for batch benchmark results.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_all_results(results_dir: str) -> dict:
    """Load all result files from the batch directory"""
    results_path = Path(results_dir)

    # Load batch summary
    summary_file = results_path / "batch_summary.json"
    if not summary_file.exists():
        print(f"❌ Batch summary not found: {summary_file}")
        return None

    with open(summary_file, 'r') as f:
        batch_summary = json.load(f)

    # Load individual result files
    all_results = []
    for result_entry in batch_summary.get("results", []):
        if result_entry["status"] == "success":
            result_file = Path(result_entry["results_file"])
            if result_file.exists():
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    data["_source_file"] = str(result_file)
                    all_results.append(data)

    return {
        "batch_summary": batch_summary,
        "results": all_results
    }


def generate_html_dashboard(data: dict, output_path: str):
    """Generate interactive HTML dashboard"""

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Dashboard</title>
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

        .header .subtitle {
            opacity: 0.9;
            font-size: 1rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
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
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #1d1d1f;
        }

        .tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid #e5e5e7;
        }

        .tab {
            padding: 1rem 1.5rem;
            background: none;
            border: none;
            font-size: 1rem;
            font-weight: 500;
            color: #86868b;
            cursor: pointer;
            position: relative;
            transition: color 0.3s;
        }

        .tab.active {
            color: #667eea;
        }

        .tab.active::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .card h2 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #1d1d1f;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: #f5f5f7;
        }

        th {
            text-align: left;
            padding: 1rem;
            font-weight: 600;
            color: #1d1d1f;
            border-bottom: 2px solid #e5e5e7;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid #e5e5e7;
        }

        tr:hover {
            background: #f9f9fb;
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

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }

        .modal-close {
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 1.5rem;
            background: none;
            border: none;
            cursor: pointer;
            color: #86868b;
        }

        .modal-close:hover {
            color: #1d1d1f;
        }

        pre {
            background: #f5f5f7;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.875rem;
            line-height: 1.5;
        }

        .btn {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: none;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
        }

        .matrix {
            overflow-x: auto;
        }

        .matrix table {
            min-width: 800px;
        }

        .filter-bar {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .filter-bar select {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid #e5e5e7;
            font-size: 0.875rem;
        }

        .speed-cell {
            font-weight: 600;
        }

        .items-cell {
            color: #667eea;
            font-weight: 500;
        }

        .error-card {
            background: #fff8f8;
            border: 1px solid #ffd3d3;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .error-card h4 {
            color: #c41e3a;
            margin-bottom: 0.5rem;
        }

        .error-message {
            background: white;
            padding: 0.75rem;
            border-radius: 4px;
            margin: 0.5rem 0;
            font-family: monospace;
            font-size: 0.875rem;
            color: #1d1d1f;
        }

        .fix-box {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 4px;
            padding: 0.75rem;
            margin-top: 0.5rem;
        }

        .fix-box h5 {
            color: #0369a1;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }

        .fix-box code {
            background: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            display: inline-block;
            margin: 0.25rem 0;
        }

        .error-summary {
            background: #fff8f8;
            border-left: 4px solid #c41e3a;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 4px;
        }

        .error-summary h3 {
            color: #c41e3a;
            margin-bottom: 0.5rem;
        }

        .clickable-error {
            cursor: pointer;
            text-decoration: underline;
        }

        .clickable-error:hover {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🚀 LLM Benchmark Dashboard</h1>
            <p class="subtitle">Comprehensive analysis across OCR engines, LLM models, and documents</p>
        </div>
    </div>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Documents Tested</h3>
                <div class="value" id="stat-documents">-</div>
            </div>
            <div class="stat-card">
                <h3>Total Tests</h3>
                <div class="value" id="stat-tests">-</div>
            </div>
            <div class="stat-card">
                <h3>OCR Engines</h3>
                <div class="value" id="stat-ocr">-</div>
            </div>
            <div class="stat-card">
                <h3>LLM Models</h3>
                <div class="value" id="stat-llm">-</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('errors')">Errors & Fixes</button>
            <button class="tab" onclick="showTab('documents')">By Document</button>
            <button class="tab" onclick="showTab('ocr')">OCR Comparison</button>
            <button class="tab" onclick="showTab('llm')">LLM Comparison</button>
            <button class="tab" onclick="showTab('raw')">Raw Outputs</button>
        </div>

        <div id="tab-overview" class="tab-content active">
            <div class="card">
                <h2>Performance Overview</h2>
                <div class="matrix" id="overview-matrix"></div>
            </div>
        </div>

        <div id="tab-errors" class="tab-content">
            <div class="card">
                <h2>Errors & Troubleshooting</h2>
                <p style="margin-bottom: 1rem; color: #86868b;">Detailed error messages and how to fix them</p>
                <div id="errors-list"></div>
            </div>
        </div>

        <div id="tab-documents" class="tab-content">
            <div class="card">
                <h2>Results by Document</h2>
                <div class="filter-bar">
                    <select id="doc-filter" onchange="filterDocuments()">
                        <option value="">All Documents</option>
                    </select>
                </div>
                <div id="documents-table"></div>
            </div>
        </div>

        <div id="tab-ocr" class="tab-content">
            <div class="card">
                <h2>OCR Engine Comparison</h2>
                <p style="margin-bottom: 1rem; color: #86868b;">Compare OCR accuracy and speed across all documents</p>
                <div id="ocr-comparison"></div>
            </div>
        </div>

        <div id="tab-llm" class="tab-content">
            <div class="card">
                <h2>LLM Model Comparison</h2>
                <p style="margin-bottom: 1rem; color: #86868b;">Compare LLM extraction quality and performance</p>
                <div id="llm-comparison"></div>
            </div>
        </div>

        <div id="tab-raw" class="tab-content">
            <div class="card">
                <h2>Raw LLM Outputs</h2>
                <div class="filter-bar">
                    <select id="raw-doc-filter" onchange="filterRawOutputs()">
                        <option value="">All Documents</option>
                    </select>
                    <select id="raw-model-filter" onchange="filterRawOutputs()">
                        <option value="">All Models</option>
                    </select>
                </div>
                <div id="raw-outputs"></div>
            </div>
        </div>
    </div>

    <div id="modal" class="modal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        // Data will be injected here
        const BENCHMARK_DATA = """ + json.dumps(data, indent=2) + """;

        // Initialize dashboard
        function initDashboard() {
            const results = BENCHMARK_DATA.results || [];
            const batch = BENCHMARK_DATA.batch_summary || {};

            // Update stats
            document.getElementById('stat-documents').textContent = results.length;

            let totalTests = 0;
            let ocrEngines = new Set();
            let llmModels = new Set();

            results.forEach(doc => {
                totalTests += doc.total_combinations || 0;
                (doc.combinations || []).forEach(combo => {
                    ocrEngines.add(combo.ocr_display);
                    llmModels.add(combo.llm_display);
                });
            });

            document.getElementById('stat-tests').textContent = totalTests;
            document.getElementById('stat-ocr').textContent = ocrEngines.size;
            document.getElementById('stat-llm').textContent = llmModels.size;

            // Populate filters
            populateFilters(results);

            // Render all tabs
            renderOverview(results);
            renderErrors(results);
            renderDocuments(results);
            renderOCRComparison(results);
            renderLLMComparison(results);
            renderRawOutputs(results);
        }

        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // Show selected tab
            document.getElementById('tab-' + tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function populateFilters(results) {
            const docFilter = document.getElementById('doc-filter');
            const rawDocFilter = document.getElementById('raw-doc-filter');
            const rawModelFilter = document.getElementById('raw-model-filter');

            const docs = new Set();
            const models = new Set();

            results.forEach(doc => {
                const docName = doc.document.split('/').pop();
                docs.add(docName);

                (doc.combinations || []).forEach(combo => {
                    models.add(combo.llm_display);
                });
            });

            docs.forEach(doc => {
                docFilter.innerHTML += `<option value="${doc}">${doc}</option>`;
                rawDocFilter.innerHTML += `<option value="${doc}">${doc}</option>`;
            });

            models.forEach(model => {
                rawModelFilter.innerHTML += `<option value="${model}">${model}</option>`;
            });
        }

        function renderOverview(results) {
            let html = '<table><thead><tr>';
            html += '<th>Document</th>';
            html += '<th>OCR Engine</th>';
            html += '<th>LLM Model</th>';
            html += '<th>Mode</th>';
            html += '<th>Time</th>';
            html += '<th>Items</th>';
            html += '<th>Status</th>';
            html += '</tr></thead><tbody>';

            results.forEach(doc => {
                const docName = doc.document.split('/').pop();
                (doc.combinations || []).forEach(combo => {
                    const time = combo.timings?.total || 0;
                    const items = combo.extraction?.parameters?.length || combo.extraction?.medications?.length || 0;
                    const error = combo.error;

                    const speedBadge = time < 30 ? 'fast' : time < 60 ? 'medium' : 'slow';

                    html += '<tr>';
                    html += `<td>${docName}</td>`;
                    html += `<td>${combo.ocr_display}</td>`;
                    html += `<td>${combo.llm_display}</td>`;
                    html += `<td>${combo.mode || 'N/A'}</td>`;
                    html += `<td class="speed-cell"><span class="badge ${speedBadge}">${time.toFixed(2)}s</span></td>`;
                    html += `<td class="items-cell">${items} items</td>`;
                    if (error) {
                        html += `<td><span class="badge error clickable-error" onclick="showTab('errors')" title="${error}">Error ⓘ</span></td>`;
                    } else {
                        html += `<td><span class="badge success">Success</span></td>`;
                    }
                    html += '</tr>';
                });
            });

            html += '</tbody></table>';
            document.getElementById('overview-matrix').innerHTML = html;
        }

        function renderErrors(results) {
            const errors = [];

            results.forEach(doc => {
                const docName = doc.document.split('/').pop();
                (doc.combinations || []).forEach(combo => {
                    if (combo.error) {
                        errors.push({
                            document: docName,
                            ocr: combo.ocr_display,
                            llm: combo.llm_display,
                            llm_name: combo.llm_name,
                            mode: combo.mode || 'N/A',
                            error: combo.error
                        });
                    }
                });
            });

            let html = '';

            if (errors.length === 0) {
                html = '<div class="error-summary" style="background: #d1f4e0; border-left-color: #0a6640;">';
                html += '<h3 style="color: #0a6640;">✅ No Errors!</h3>';
                html += '<p>All tests completed successfully.</p>';
                html += '</div>';
            } else {
                html = '<div class="error-summary">';
                html += `<h3>⚠️ ${errors.length} Test(s) Failed</h3>`;
                html += '<p>The following combinations encountered errors. See below for details and fixes.</p>';
                html += '</div>';

                // Group errors by type
                const errorsByModel = {};
                errors.forEach(err => {
                    const key = err.llm;
                    if (!errorsByModel[key]) {
                        errorsByModel[key] = [];
                    }
                    errorsByModel[key].push(err);
                });

                Object.entries(errorsByModel).forEach(([model, errs]) => {
                    html += '<div class="error-card">';
                    html += `<h4>🔴 ${model} (${errs.length} failure${errs.length > 1 ? 's' : ''})</h4>`;

                    errs.forEach(err => {
                        html += `<div style="margin: 0.75rem 0; padding-left: 1rem; border-left: 2px solid #ffd3d3;">`;
                        html += `<p><strong>Document:</strong> ${err.document} | <strong>OCR:</strong> ${err.ocr} | <strong>Mode:</strong> ${err.mode}</p>`;
                        html += `<div class="error-message">${err.error}</div>`;

                        // Provide fix suggestions based on error type
                        html += '<div class="fix-box">';
                        html += '<h5>💡 How to Fix:</h5>';

                        if (err.error.includes('not available')) {
                            html += '<p>This model is not installed. Download it with:</p>';
                            html += `<code>ollama pull ${err.llm_name}</code>`;
                        } else if (err.error.includes('JSON')) {
                            html += '<p>The model returned invalid JSON. This could be:</p>';
                            html += '<ul style="margin-left: 1.5rem; margin-top: 0.5rem;">';
                            html += '<li>Model not following instructions properly</li>';
                            html += '<li>OCR text contains special characters breaking JSON</li>';
                            html += '<li>Try a different model or OCR engine</li>';
                            html += '</ul>';
                        } else if (err.error.includes('timeout') || err.error.includes('timed out')) {
                            html += '<p>The request timed out. Try:</p>';
                            html += '<ul style="margin-left: 1.5rem; margin-top: 0.5rem;">';
                            html += '<li>Use a smaller/faster model (e.g., qwen2.5:3b)</li>';
                            html += '<li>Increase timeout in comprehensive_benchmark.py</li>';
                            html += '<li>Check system resources (CPU/Memory)</li>';
                            html += '</ul>';
                        } else if (err.error.includes('HTTP')) {
                            html += '<p>HTTP error from Ollama server. Check:</p>';
                            html += '<ul style="margin-left: 1.5rem; margin-top: 0.5rem;">';
                            html += '<li>Ollama is running: <code>curl http://localhost:11434/api/tags</code></li>';
                            html += '<li>Model is loaded properly</li>';
                            html += '<li>Server logs for details</li>';
                            html += '</ul>';
                        } else {
                            html += '<p>Unexpected error. Try:</p>';
                            html += '<ul style="margin-left: 1.5rem; margin-top: 0.5rem;">';
                            html += '<li>Check Ollama logs</li>';
                            html += '<li>Verify model installation: <code>ollama list</code></li>';
                            html += '<li>Try re-pulling the model</li>';
                            html += '</ul>';
                        }

                        html += '</div>';
                        html += '</div>';
                    });

                    html += '</div>';
                });
            }

            document.getElementById('errors-list').innerHTML = html;
        }

        function renderDocuments(results) {
            let html = '<table><thead><tr>';
            html += '<th>Document</th>';
            html += '<th>Combinations</th>';
            html += '<th>Avg Time</th>';
            html += '<th>Success Rate</th>';
            html += '<th>Actions</th>';
            html += '</tr></thead><tbody>';

            results.forEach(doc => {
                const docName = doc.document.split('/').pop();
                const combos = doc.combinations || [];
                const successful = combos.filter(c => !c.error).length;
                const avgTime = combos.reduce((sum, c) => sum + (c.timings?.total || 0), 0) / combos.length;

                html += '<tr>';
                html += `<td><strong>${docName}</strong></td>`;
                html += `<td>${combos.length}</td>`;
                html += `<td>${avgTime.toFixed(2)}s</td>`;
                html += `<td>${((successful / combos.length) * 100).toFixed(0)}%</td>`;
                html += `<td><button class="btn btn-primary" onclick='showDocumentDetails(${JSON.stringify(doc)})'>View Details</button></td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            document.getElementById('documents-table').innerHTML = html;
        }

        function renderOCRComparison(results) {
            const ocrStats = {};

            results.forEach(doc => {
                (doc.combinations || []).forEach(combo => {
                    const ocr = combo.ocr_display;
                    if (!ocrStats[ocr]) {
                        ocrStats[ocr] = { times: [], items: [], errors: 0, total: 0 };
                    }

                    ocrStats[ocr].total++;
                    if (combo.error) {
                        ocrStats[ocr].errors++;
                    } else {
                        ocrStats[ocr].times.push(combo.timings?.ocr || 0);
                        const items = combo.extraction?.parameters?.length || combo.extraction?.medications?.length || 0;
                        ocrStats[ocr].items.push(items);
                    }
                });
            });

            let html = '<table><thead><tr>';
            html += '<th>OCR Engine</th>';
            html += '<th>Avg OCR Time</th>';
            html += '<th>Avg Items Extracted</th>';
            html += '<th>Success Rate</th>';
            html += '<th>Total Tests</th>';
            html += '</tr></thead><tbody>';

            Object.entries(ocrStats).forEach(([ocr, stats]) => {
                const avgTime = stats.times.reduce((a, b) => a + b, 0) / stats.times.length || 0;
                const avgItems = stats.items.reduce((a, b) => a + b, 0) / stats.items.length || 0;
                const successRate = ((stats.total - stats.errors) / stats.total * 100);

                html += '<tr>';
                html += `<td><strong>${ocr}</strong></td>`;
                html += `<td>${avgTime.toFixed(2)}s</td>`;
                html += `<td>${avgItems.toFixed(1)}</td>`;
                html += `<td>${successRate.toFixed(0)}%</td>`;
                html += `<td>${stats.total}</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            document.getElementById('ocr-comparison').innerHTML = html;
        }

        function renderLLMComparison(results) {
            const llmStats = {};

            results.forEach(doc => {
                (doc.combinations || []).forEach(combo => {
                    const llm = combo.llm_display;
                    const mode = combo.mode || 'unknown';
                    const key = `${llm} [${mode}]`;

                    if (!llmStats[key]) {
                        llmStats[key] = { times: [], items: [], errors: 0, total: 0, type: combo.llm_type };
                    }

                    llmStats[key].total++;
                    if (combo.error) {
                        llmStats[key].errors++;
                    } else {
                        llmStats[key].times.push(combo.timings?.llm_call || 0);
                        const items = combo.extraction?.parameters?.length || combo.extraction?.medications?.length || 0;
                        llmStats[key].items.push(items);
                    }
                });
            });

            let html = '<table><thead><tr>';
            html += '<th>LLM Model</th>';
            html += '<th>Type</th>';
            html += '<th>Avg LLM Time</th>';
            html += '<th>Avg Items</th>';
            html += '<th>Success Rate</th>';
            html += '<th>Tests</th>';
            html += '</tr></thead><tbody>';

            Object.entries(llmStats).forEach(([llm, stats]) => {
                const avgTime = stats.times.reduce((a, b) => a + b, 0) / stats.times.length || 0;
                const avgItems = stats.items.reduce((a, b) => a + b, 0) / stats.items.length || 0;
                const successRate = ((stats.total - stats.errors) / stats.total * 100);

                html += '<tr>';
                html += `<td><strong>${llm}</strong></td>`;
                html += `<td>${stats.type}</td>`;
                html += `<td>${avgTime.toFixed(2)}s</td>`;
                html += `<td>${avgItems.toFixed(1)}</td>`;
                html += `<td>${successRate.toFixed(0)}%</td>`;
                html += `<td>${stats.total}</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            document.getElementById('llm-comparison').innerHTML = html;
        }

        function renderRawOutputs(results) {
            let html = '';

            results.forEach(doc => {
                const docName = doc.document.split('/').pop();

                (doc.combinations || []).forEach((combo, idx) => {
                    html += `<div class="card raw-output" data-doc="${docName}" data-model="${combo.llm_display}">`;
                    html += `<h3>${docName} - ${combo.llm_display} [${combo.mode || 'N/A'}]</h3>`;
                    html += `<p><strong>OCR:</strong> ${combo.ocr_display} | <strong>Time:</strong> ${combo.timings?.total?.toFixed(2)}s</p>`;

                    if (combo.error) {
                        html += `<p style="color: #c41e3a;"><strong>Error:</strong> ${combo.error}</p>`;
                    } else {
                        html += '<h4>Validation:</h4>';
                        html += `<pre>${JSON.stringify(combo.validation, null, 2)}</pre>`;
                        html += '<h4>Extraction:</h4>';
                        html += `<pre>${JSON.stringify(combo.extraction, null, 2)}</pre>`;

                        if (combo.raw_response) {
                            html += '<h4>Raw LLM Response:</h4>';
                            html += `<pre>${combo.raw_response}</pre>`;
                        }
                    }

                    html += '</div>';
                });
            });

            document.getElementById('raw-outputs').innerHTML = html;
        }

        function filterDocuments() {
            const filter = document.getElementById('doc-filter').value;
            // Re-render with filter
            const results = filter ? BENCHMARK_DATA.results.filter(r => r.document.includes(filter)) : BENCHMARK_DATA.results;
            renderDocuments(results);
        }

        function filterRawOutputs() {
            const docFilter = document.getElementById('raw-doc-filter').value;
            const modelFilter = document.getElementById('raw-model-filter').value;

            document.querySelectorAll('.raw-output').forEach(el => {
                const matchDoc = !docFilter || el.dataset.doc === docFilter;
                const matchModel = !modelFilter || el.dataset.model === modelFilter;

                el.style.display = (matchDoc && matchModel) ? 'block' : 'none';
            });
        }

        function showDocumentDetails(doc) {
            const docName = doc.document.split('/').pop();
            let html = `<h2>${docName}</h2>`;
            html += '<table><thead><tr>';
            html += '<th>OCR</th><th>LLM</th><th>Mode</th><th>Time</th><th>Items</th><th>Status</th>';
            html += '</tr></thead><tbody>';

            (doc.combinations || []).forEach(combo => {
                const time = combo.timings?.total || 0;
                const items = combo.extraction?.parameters?.length || combo.extraction?.medications?.length || 0;

                html += '<tr>';
                html += `<td>${combo.ocr_display}</td>`;
                html += `<td>${combo.llm_display}</td>`;
                html += `<td>${combo.mode || 'N/A'}</td>`;
                html += `<td>${time.toFixed(2)}s</td>`;
                html += `<td>${items}</td>`;
                html += `<td>${combo.error ? 'Error' : 'Success'}</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';

            document.getElementById('modal-body').innerHTML = html;
            document.getElementById('modal').classList.add('active');
        }

        function closeModal(event) {
            if (!event || event.target.id === 'modal') {
                document.getElementById('modal').classList.remove('active');
            }
        }

        // Initialize on load
        initDashboard();
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html_content)


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 generate_dashboard.py <batch_results_directory>")
        print("\nEXAMPLE:")
        print("  python3 generate_dashboard.py batch_results_20251026_143022")
        return

    results_dir = sys.argv[1]

    if not Path(results_dir).exists():
        print(f"❌ Directory not found: {results_dir}")
        return

    print(f"📊 Loading results from: {results_dir}")

    data = load_all_results(results_dir)

    if not data:
        print("❌ Failed to load results")
        return

    output_path = Path(results_dir) / "dashboard.html"

    print(f"🎨 Generating dashboard...")
    generate_html_dashboard(data, output_path)

    print(f"✅ Dashboard generated: {output_path}")
    print(f"\n🌐 Open in browser:")
    print(f"   open {output_path}")


if __name__ == "__main__":
    main()
