#!/usr/bin/env python3
"""
Benchmark script to compare 3B vs 7B models for OCR + Single Call mode.
Logs detailed results including timing, accuracy, and extracted data.
"""

import base64
import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Optional: PDF support
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PDF support not available. Install with: pip3 install pdf2image Pillow")

# Optional: OCR support
try:
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False
    print("⚠️  OCR support not available. Install with: pip3 install pytesseract")

# Configuration
OLLAMA_HOST = "http://localhost:11434"
MODELS_TO_TEST = [
    {"name": "qwen2.5:3b", "size": "3B"},
    {"name": "qwen2.5:7b", "size": "7B"}
]

# Combined prompt for single-call validation + extraction
COMBINED_SYSTEM_PROMPT = """You are a medical document processing AI. You will validate AND extract data in a SINGLE response."""

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


def extract_text_ocr(file_bytes: bytes) -> str:
    """Extract text from PDF or image using OCR"""
    if not OCR_SUPPORT:
        raise Exception("OCR support not installed")
    if not PDF_SUPPORT:
        raise Exception("PDF support not installed")

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            text = pytesseract.image_to_string(img)
            extracted_texts.append(f"=== Page {i} ===\n{text}")
        full_text = "\n\n".join(extracted_texts)
    else:
        from PIL import Image
        img = Image.open(BytesIO(file_bytes))
        full_text = pytesseract.image_to_string(img)

    return full_text


def clean_json_response(response: str) -> str:
    """Remove markdown code blocks from LLM response"""
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def run_benchmark(file_path: str, model_name: str, model_size: str, ocr_text: str) -> dict:
    """Run benchmark for a single model"""
    print(f"\n{'=' * 80}")
    print(f"  BENCHMARKING: {model_size} Model ({model_name})")
    print('=' * 80)

    result = {
        "model_name": model_name,
        "model_size": model_size,
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "timings": {},
        "validation": None,
        "extraction": None,
        "raw_response": None,
        "error": None
    }

    # Single Combined LLM Call
    print(f"\n📤 Calling {model_size} model for combined validation + extraction...")

    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model_name,
        "prompt": get_combined_prompt(ocr_text),
        "system": COMBINED_SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9}
    }

    llm_start = time.time()

    try:
        response = requests.post(url, json=payload, timeout=180)
        llm_time = time.time() - llm_start
        result["timings"]["llm_call"] = round(llm_time, 2)

        if response.status_code == 200:
            llm_response = response.json().get("response", "")
            result["raw_response"] = llm_response

            print(f"✅ {model_size} completed in {llm_time:.2f}s")

            # Parse JSON
            try:
                cleaned_response = clean_json_response(llm_response)
                parsed = json.loads(cleaned_response)

                result["validation"] = parsed.get("validation", {})
                result["extraction"] = parsed.get("extraction", {})

                # Show summary
                if result["validation"]:
                    print(f"   Document Type: {result['validation'].get('document_type')}")
                    print(f"   Confidence: {result['validation'].get('confidence')}")

                if result["extraction"] and "parameters" in result["extraction"]:
                    print(f"   Extracted Parameters: {len(result['extraction']['parameters'])}")
                elif result["extraction"] and "medications" in result["extraction"]:
                    print(f"   Extracted Medications: {len(result['extraction']['medications'])}")

            except json.JSONDecodeError as e:
                result["error"] = f"JSON parsing failed: {str(e)}"
                print(f"⚠️  JSON parsing failed: {e}")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Failed with status {response.status_code}")

    except Exception as e:
        llm_time = time.time() - llm_start
        result["timings"]["llm_call"] = round(llm_time, 2)
        result["error"] = str(e)
        print(f"❌ Error: {e}")

    return result


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 benchmark_models.py <pdf_or_image_path>")
        print("\nEXAMPLE:")
        print("  python3 benchmark_models.py /path/to/lab_report.pdf")
        return

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return

    if not OCR_SUPPORT or not PDF_SUPPORT:
        print("❌ Missing dependencies. Run: pip3 install pytesseract pdf2image Pillow")
        return

    print("\n" + "=" * 80)
    print("  MODEL BENCHMARK: 3B vs 7B Comparison")
    print("=" * 80)

    # Step 1: OCR (shared across both models)
    print(f"\n📄 Document: {file_path}")
    print(f"\n{'─' * 80}")
    print("STEP 1: OCR Text Extraction (Shared)")
    print('─' * 80)

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    ocr_start = time.time()
    try:
        ocr_text = extract_text_ocr(file_bytes)
        ocr_time = time.time() - ocr_start
        print(f"✅ OCR completed in {ocr_time:.2f}s")
        print(f"   Extracted {len(ocr_text)} characters")
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return

    # Step 2: Run benchmarks for each model
    results = []

    for model_config in MODELS_TO_TEST:
        result = run_benchmark(
            file_path=file_path,
            model_name=model_config["name"],
            model_size=model_config["size"],
            ocr_text=ocr_text
        )
        result["timings"]["ocr"] = round(ocr_time, 2)
        result["timings"]["total"] = round(ocr_time + result["timings"].get("llm_call", 0), 2)
        results.append(result)

    # Step 3: Save results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"benchmark_results_{timestamp}.json"

    output_data = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "document": file_path,
        "ocr_time": round(ocr_time, 2),
        "ocr_text_length": len(ocr_text),
        "models": results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Step 4: Print Summary
    print("\n" + "=" * 80)
    print("  BENCHMARK SUMMARY")
    print("=" * 80)

    print(f"\n⏱️  Timing Comparison:")
    print(f"   OCR (shared): {ocr_time:.2f}s")
    for result in results:
        model_size = result["model_size"]
        llm_time = result["timings"].get("llm_call", 0)
        total_time = result["timings"].get("total", 0)
        print(f"   {model_size} LLM call: {llm_time:.2f}s (Total: {total_time:.2f}s)")

    # Speed comparison
    if len(results) == 2:
        time_3b = results[0]["timings"].get("llm_call", 0)
        time_7b = results[1]["timings"].get("llm_call", 0)
        if time_3b > 0 and time_7b > 0:
            speedup = time_7b / time_3b
            print(f"\n   3B is {speedup:.2f}x faster than 7B")

    print(f"\n📊 Accuracy Comparison:")
    for result in results:
        model_size = result["model_size"]
        validation = result.get("validation", {})
        extraction = result.get("extraction", {})

        doc_type = validation.get("document_type", "Unknown")
        confidence = validation.get("confidence", 0)

        param_count = 0
        if extraction and "parameters" in extraction:
            param_count = len(extraction["parameters"])
        elif extraction and "medications" in extraction:
            param_count = len(extraction["medications"])

        print(f"   {model_size}: {doc_type} (confidence: {confidence:.2f}, extracted: {param_count} items)")

    print(f"\n💾 Results saved to: {output_file}")
    print(f"\n📝 Next step: Run evaluation script to compare accuracy:")
    print(f"   python3 evaluate_results.py {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
