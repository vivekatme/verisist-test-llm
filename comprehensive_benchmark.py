#!/usr/bin/env python3
"""
Comprehensive benchmark script to compare:
- OCR engine: Tesseract (fast, reliable baseline)
- LLM models: Qwen 2.5 (3B, 7B), Mistral, Meditron, BioMistral
- All combinations tested with OCR + Single Call approach

All components are Apache 2.0 licensed (OSS, commercial-friendly).

Note: For OCR engine comparison, use ocr_comparison.py which tests both Tesseract and EasyOCR.
"""

import base64
import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional

# PDF support
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PDF support not available. Install with: pip3 install pdf2image Pillow")

# OCR engines
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️  Tesseract not available")

# Configuration
OLLAMA_HOST = "http://localhost:11434"

# OCR engine for LLM benchmarking (Tesseract only - fast baseline)
# For OCR engine comparison, use ocr_comparison.py
OCR_ENGINES = []
if TESSERACT_AVAILABLE:
    OCR_ENGINES.append({"name": "tesseract", "display": "Tesseract OCR"})

# LLM models to test (all Apache 2.0 licensed)
# Note: Both BioMistral variants (Q6_K and Q4) are broken - return empty responses
LLM_MODELS = [
    {"name": "qwen2.5:3b", "display": "Qwen 2.5 3B", "type": "general"},
    {"name": "qwen2.5:7b", "display": "Qwen 2.5 7B", "type": "general"},
    {"name": "mistral:7b", "display": "Mistral 7B", "type": "general"},
]

# Combined system prompt
COMBINED_SYSTEM_PROMPT = """You are a medical document processing AI. You will validate AND extract data in a SINGLE response."""

def get_extraction_only_prompt(ocr_text: str) -> str:
    """Get extraction-only prompt (skip validation step)."""
    return f"""Extract structured data from this medical document.

**Task: Extract ALL relevant information**
- Automatically detect document type (LAB_REPORT, PRESCRIPTION, MEDICAL_BILL)
- If LAB_REPORT: Extract ALL test parameters with values, units, reference ranges, and status
- If PRESCRIPTION: Extract ALL medications with dosage, frequency, duration, instructions
- Extract metadata: patient name, lab name, date, title

**Output Format (JSON only, no markdown)**:
{{
  "title": "Lipid Profile - Apollo Diagnostics - Mr. VIVEK GUPTA",
  "documentType": "LAB_REPORT",
  "documentDate": "2025-03-14",
  "labName": "Apollo Diagnostics",
  "patientName": "Mr. VIVEK GUPTA",
  "testType": "Lipid Profile",
  "parameters": [
    {{
      "name": "Total Cholesterol",
      "value": 166,
      "unit": "mg/dL",
      "referenceRange": {{"min": 0, "max": 200}},
      "status": "NORMAL"
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object, no markdown code blocks, no additional text.

**OCR Text:**
{ocr_text}
"""


def get_combined_prompt(ocr_text: str) -> str:
    """Get combined prompt for validation + extraction in one call."""
    return f"""Analyze this medical document and provide BOTH validation AND extraction in ONE JSON response.

**Task 1: Validate the document**
- Determine if this is a health-related document
- Classify the document type (LAB_REPORT, PRESCRIPTION, MEDICAL_BILL, or OTHER)
- Extract basic metadata (lab name, date, confidence)

**Task 2: Extract structured data**
- If LAB_REPORT: Extract ALL test parameters with values, units, reference ranges, and status
- If PRESCRIPTION: Extract ALL medications with dosage, frequency, duration, instructions
- If not a health document or unsupported type: Return empty extraction

**Output Format (JSON only, no markdown)**:
{{
  "validation": {{
    "is_health_document": true,
    "document_type": "LAB_REPORT",
    "confidence": 0.95,
    "reasoning": "Brief explanation",
    "lab_name": "Apollo Diagnostics",
    "document_date": "2025-03-14"
  }},
  "extraction": {{
    "title": "Lipid Profile - Apollo Diagnostics - Mr. VIVEK GUPTA",
    "documentType": "LAB_REPORT",
    "documentDate": "2025-03-14",
    "labName": "Apollo Diagnostics",
    "patientName": "Mr. VIVEK GUPTA",
    "testType": "Lipid Profile",
    "parameters": [
      {{
        "name": "Total Cholesterol",
        "value": 166,
        "unit": "mg/dL",
        "referenceRange": {{"min": 0, "max": 200}},
        "status": "NORMAL"
      }}
    ]
  }}
}}

IMPORTANT: Return ONLY the JSON object, no markdown code blocks, no additional text.

**OCR Text:**
{ocr_text}
"""


def extract_text_tesseract(file_bytes: bytes) -> str:
    """Extract text using Tesseract OCR"""
    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            text = pytesseract.image_to_string(img)
            extracted_texts.append(f"=== Page {i} ===\n{text}")
        return "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


def extract_text_with_ocr(file_bytes: bytes, ocr_engine: str) -> tuple[str, float]:
    """Extract text using Tesseract OCR, return (text, time_taken)"""
    start_time = time.time()

    if ocr_engine == "tesseract":
        text = extract_text_tesseract(file_bytes)
    else:
        raise ValueError(f"Unknown OCR engine: {ocr_engine} (only 'tesseract' supported)")

    time_taken = time.time() - start_time
    return text, time_taken


def clean_json_response(response: str) -> str:
    """Remove markdown code blocks and fix common JSON errors from LLM response"""
    import re

    cleaned = response.strip()

    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    # Try to fix unquoted property names (common error in Qwen 2.5 7B)
    # This regex finds patterns like:  propertyName: value
    # and converts to: "propertyName": value
    try:
        # Fix unquoted keys before colons
        cleaned = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)
    except Exception:
        pass  # If regex fails, return cleaned as-is

    return cleaned


def check_model_available(model_name: str) -> bool:
    """Check if Ollama model is available"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(m.get("name") == model_name for m in models)
    except:
        pass
    return False


def run_combination(file_path: str, ocr_engine: str, ocr_display: str,
                    llm_name: str, llm_display: str, llm_type: str,
                    ocr_text: str, ocr_time: float, extraction_only: bool = False) -> dict:
    """Run benchmark for one OCR + LLM combination"""

    print(f"\n{'─' * 80}")
    print(f"Testing: {ocr_display} + {llm_display}")
    print('─' * 80)

    result = {
        "ocr_engine": ocr_engine,
        "ocr_display": ocr_display,
        "llm_name": llm_name,
        "llm_display": llm_display,
        "llm_type": llm_type,
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "timings": {
            "ocr": round(ocr_time, 2),
        },
        "validation": None,
        "extraction": None,
        "raw_response": None,
        "error": None
    }

    # Check if model is available
    if not check_model_available(llm_name):
        result["error"] = f"Model {llm_name} not available. Run: ollama pull {llm_name}"
        print(f"⚠️  Model not available: {llm_name}")
        print(f"   Run: ollama pull {llm_name}")
        return result

    # Call LLM
    print(f"📤 Calling {llm_display}... (mode: {'extraction-only' if extraction_only else 'validation+extraction'})")

    url = f"{OLLAMA_HOST}/api/generate"

    # Choose prompt based on mode
    if extraction_only:
        prompt = get_extraction_only_prompt(ocr_text)
        system_prompt = "You are a medical document processing AI. Extract structured data accurately."
    else:
        prompt = get_combined_prompt(ocr_text)
        system_prompt = COMBINED_SYSTEM_PROMPT

    payload = {
        "model": llm_name,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9}
    }

    llm_start = time.time()

    try:
        response = requests.post(url, json=payload, timeout=300)
        llm_time = time.time() - llm_start
        result["timings"]["llm_call"] = round(llm_time, 2)
        result["timings"]["total"] = round(ocr_time + llm_time, 2)

        if response.status_code == 200:
            llm_response = response.json().get("response", "")
            result["raw_response"] = llm_response

            print(f"✅ Completed in {llm_time:.2f}s (Total: {result['timings']['total']:.2f}s)")

            # Parse JSON
            try:
                cleaned_response = clean_json_response(llm_response)
                parsed = json.loads(cleaned_response)

                if extraction_only:
                    # Direct extraction format
                    result["validation"] = None
                    result["extraction"] = parsed
                else:
                    # Combined format (validation + extraction)
                    result["validation"] = parsed.get("validation", {})
                    result["extraction"] = parsed.get("extraction", {})

                # Show summary
                if result["validation"]:
                    print(f"   Document Type: {result['validation'].get('document_type')}")
                    print(f"   Confidence: {result['validation'].get('confidence')}")

                extraction = result["extraction"]
                if extraction and "parameters" in extraction:
                    print(f"   Extracted Parameters: {len(extraction['parameters'])}")
                elif extraction and "medications" in extraction:
                    print(f"   Extracted Medications: {len(extraction['medications'])}")

            except json.JSONDecodeError as e:
                result["error"] = f"JSON parsing failed: {str(e)}"
                print(f"⚠️  JSON parsing failed: {e}")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Failed with status {response.status_code}")

    except Exception as e:
        llm_time = time.time() - llm_start
        result["timings"]["llm_call"] = round(llm_time, 2)
        result["timings"]["total"] = round(ocr_time + llm_time, 2)
        result["error"] = str(e)
        print(f"❌ Error: {e}")

    return result


def generate_html_report(output_data: dict, html_file: Path):
    """Generate an HTML visualization of the benchmark results."""

    # Calculate statistics
    total_combinations = len(output_data["combinations"])
    successful = [r for r in output_data["combinations"] if not r.get("error")]
    failed = [r for r in output_data["combinations"] if r.get("error")]
    success_rate = (len(successful) / total_combinations * 100) if total_combinations > 0 else 0

    # Calculate average times
    avg_times = {}
    for result in successful:
        model = result["llm_display"]
        if model not in avg_times:
            avg_times[model] = []
        total_time = result["timings"].get("total", 0)
        avg_times[model].append(total_time)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Results - {output_data["benchmark_timestamp"][:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .results-grid {{
            display: grid;
            gap: 20px;
        }}
        .result-card {{
            background: #f8f9fa;
            border-left: 5px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .result-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .result-card.error {{
            border-left-color: #e74c3c;
            background: #fee;
        }}
        .result-card.success {{
            border-left-color: #27ae60;
            background: #f0fff4;
        }}
        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .model-name {{
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
        }}
        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-badge.success {{
            background: #27ae60;
            color: white;
        }}
        .status-badge.error {{
            background: #e74c3c;
            color: white;
        }}
        .result-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .detail-item {{
            background: white;
            padding: 12px;
            border-radius: 6px;
        }}
        .detail-label {{
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
        }}
        .detail-value {{
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
        }}
        .error-message {{
            background: #fff;
            border: 1px solid #e74c3c;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            color: #c0392b;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .extraction-preview {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            max-height: 200px;
            overflow-y: auto;
        }}
        .extraction-preview pre {{
            font-size: 0.85em;
            color: #555;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .mode-tag {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 LLM Benchmark Results</h1>
            <p>Document: {Path(output_data["document"]).name}</p>
            <p>Timestamp: {output_data["benchmark_timestamp"]}</p>
        </div>

        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{output_data["llm_models_tested"]}</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_combinations}</div>
                <div class="stat-label">Total Combinations</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(successful)}</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(failed)}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.0f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2 class="section-title">📊 Benchmark Results</h2>
                <div class="results-grid">
"""

    # Sort results by model and mode
    sorted_results = sorted(output_data["combinations"], key=lambda x: (x["llm_display"], x.get("mode", "")))

    for result in sorted_results:
        is_error = "error" in result and result["error"]
        status_class = "error" if is_error else "success"
        status_text = "ERROR" if is_error else "SUCCESS"

        mode = result.get("mode", "N/A")
        model_name = result["llm_display"]

        html_content += f"""
                    <div class="result-card {status_class}">
                        <div class="result-header">
                            <div>
                                <span class="model-name">{model_name}</span>
                                <span class="mode-tag">{mode}</span>
                            </div>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </div>
"""

        if is_error:
            html_content += f"""
                        <div class="error-message">
                            ❌ {result["error"]}
                        </div>
"""
        else:
            # Show timings and extraction details
            timings = result.get("timings", {})
            total_time = timings.get("total", 0)
            ocr_time = timings.get("ocr", 0)
            llm_time = timings.get("llm_call", 0)

            # Count extracted items
            extraction = result.get("extraction", {})
            item_count = 0
            if extraction and "parameters" in extraction:
                item_count = len(extraction["parameters"])
            elif extraction and "medications" in extraction:
                item_count = len(extraction["medications"])

            html_content += f"""
                        <div class="result-details">
                            <div class="detail-item">
                                <div class="detail-label">Total Time</div>
                                <div class="detail-value">{total_time:.2f}s</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">OCR Time</div>
                                <div class="detail-value">{ocr_time:.2f}s</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">LLM Time</div>
                                <div class="detail-value">{llm_time:.2f}s</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Items Extracted</div>
                                <div class="detail-value">{item_count}</div>
                            </div>
                        </div>
"""

            # Show extraction preview if available
            if extraction:
                extraction_json = json.dumps(extraction, indent=2)[:500]  # Limit preview
                html_content += f"""
                        <div class="extraction-preview">
                            <strong>Extraction Preview:</strong>
                            <pre>{extraction_json}</pre>
                        </div>
"""

        html_content += """
                    </div>
"""

    html_content += """
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(html_file, 'w') as f:
        f.write(html_content)

    print(f"📊 HTML report saved to: {html_file}")


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 comprehensive_benchmark.py <pdf_or_image_path>")
        print("\nEXAMPLE:")
        print("  python3 comprehensive_benchmark.py /path/to/lab_report.pdf")
        print("\nNOTE:")
        print("  - Tests BOTH modes: extraction-only vs validation+extraction")
        print("  - Compares speed/accuracy tradeoffs for all combinations")
        print("  - Make sure to install dependencies: pip3 install -r requirements.txt")
        print("  - Download LLM models with: ollama pull <model_name>")
        print("  - See MODELS.md for full list of models and licenses")
        return

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return

    if not PDF_SUPPORT:
        print("❌ PDF support not installed. Run: pip3 install pdf2image Pillow")
        return

    if not OCR_ENGINES:
        print("❌ Tesseract OCR not available. Install it:")
        print("   macOS: brew install tesseract")
        print("   Python: pip3 install pytesseract")
        return

    print("\n" + "=" * 80)
    print("  COMPREHENSIVE LLM BENCHMARK: Tesseract OCR × LLM Models × Modes")
    print("=" * 80)
    print(f"\n📄 Document: {file_path}")
    print(f"\n📊 Test Matrix:")
    print(f"   OCR Engine: Tesseract (fast baseline)")
    print(f"   LLM Models: {len(LLM_MODELS)} ({', '.join(m['display'] for m in LLM_MODELS)})")
    print(f"   Modes: 2 (extraction-only, validation+extraction)")
    print(f"   Total Combinations: {len(LLM_MODELS) * 2}")
    print(f"\n💡 Tip: For OCR engine comparison, use: python3 ocr_comparison.py")

    # Load file
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    # Run OCR with Tesseract
    print(f"\n{'=' * 80}")
    print("STEP 1: OCR Text Extraction (Tesseract)")
    print('=' * 80)

    ocr_results = {}
    for ocr_config in OCR_ENGINES:
        print(f"\n🔍 Running {ocr_config['display']}...")
        try:
            ocr_text, ocr_time = extract_text_with_ocr(file_bytes, ocr_config["name"])
            ocr_results[ocr_config["name"]] = {
                "text": ocr_text,
                "time": ocr_time,
                "length": len(ocr_text)
            }
            print(f"✅ Completed in {ocr_time:.2f}s ({len(ocr_text)} characters)")
        except Exception as e:
            print(f"❌ Failed: {e}")
            ocr_results[ocr_config["name"]] = {
                "text": None,
                "time": 0,
                "length": 0,
                "error": str(e)
            }

    # Run all combinations (test both modes for each OCR × LLM pair)
    print(f"\n{'=' * 80}")
    print("STEP 2: LLM Processing (All Combinations × Both Modes)")
    print('=' * 80)

    all_results = []
    modes = [
        (False, "validation+extraction"),
        (True, "extraction-only")
    ]

    for ocr_config in OCR_ENGINES:
        ocr_name = ocr_config["name"]
        ocr_data = ocr_results.get(ocr_name)

        if not ocr_data or not ocr_data.get("text"):
            print(f"\n⚠️  Skipping {ocr_config['display']} - OCR failed")
            continue

        for llm_config in LLM_MODELS:
            for extraction_only, mode_name in modes:
                result = run_combination(
                    file_path=file_path,
                    ocr_engine=ocr_name,
                    ocr_display=ocr_config["display"],
                    llm_name=llm_config["name"],
                    llm_display=llm_config["display"],
                    llm_type=llm_config["type"],
                    ocr_text=ocr_data["text"],
                    ocr_time=ocr_data["time"],
                    extraction_only=extraction_only
                )
                result["mode"] = mode_name  # Add mode to result
                all_results.append(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create results directory if it doesn't exist
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"comprehensive_results_{timestamp}.json"

    output_data = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "document": file_path,
        "modes_tested": 2,
        "ocr_engine": "tesseract",
        "llm_models_tested": len(LLM_MODELS),
        "total_combinations": len(all_results),
        "ocr_results": ocr_results,
        "combinations": all_results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Generate HTML report
    html_file = results_dir / f"comprehensive_results_{timestamp}.html"
    generate_html_report(output_data, html_file)

    # Print summary
    print("\n" + "=" * 80)
    print("  BENCHMARK SUMMARY")
    print("=" * 80)

    print(f"\n📊 Results Matrix ({len(all_results)} combinations):\n")

    # Group by OCR engine
    for ocr_config in OCR_ENGINES:
        ocr_name = ocr_config["name"]
        ocr_results_filtered = [r for r in all_results if r["ocr_engine"] == ocr_name]

        if not ocr_results_filtered:
            continue

        print(f"\n{ocr_config['display']}:")
        for result in ocr_results_filtered:
            llm_display = result["llm_display"]
            mode = result.get("mode", "unknown")
            total_time = result["timings"].get("total", 0)
            error = result.get("error")

            if error:
                print(f"  ❌ {llm_display:20} [{mode:22}] - ERROR")
                print(f"     Error: {error}")
            else:
                extraction = result.get("extraction", {})
                item_count = 0
                if extraction and "parameters" in extraction:
                    item_count = len(extraction["parameters"])
                elif extraction and "medications" in extraction:
                    item_count = len(extraction["medications"])

                print(f"  ✅ {llm_display:20} [{mode:22}] - {total_time:6.2f}s ({item_count} items)")

    # Print error summary
    errors_found = [r for r in all_results if r.get("error")]
    if errors_found:
        print("\n" + "=" * 80)
        print("  ERROR SUMMARY")
        print("=" * 80)

        error_groups = {}
        for result in errors_found:
            key = result["llm_display"]
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(result)

        for model, errors in error_groups.items():
            print(f"\n🔴 {model} ({len(errors)} failure(s)):")
            for err in errors:
                print(f"   {err['ocr_display']} + {err.get('mode', 'N/A')}")
                print(f"   Error: {err['error']}")

                # Provide fix suggestion
                if 'not available' in err['error']:
                    print(f"   💡 Fix: ollama pull {err['llm_name']}")
                elif 'JSON' in err['error']:
                    print(f"   💡 Fix: Try different model or check OCR output quality")
                print()

    print(f"\n💾 Results saved:")
    print(f"   JSON: {output_file}")
    print(f"   HTML: {html_file}")
    print(f"\n📊 Open HTML report in browser:")
    print(f"   open {html_file}")
    print(f"\n📝 Or run evaluation to compare combinations:")
    print(f"   python3 evaluate_comprehensive.py {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
