#!/usr/bin/env python3
"""
Comprehensive benchmark script to compare:
- OCR engines: Tesseract, PaddleOCR, EasyOCR
- LLM models: Qwen 2.5 (3B, 7B, 14B), Meditron, BioMistral
- All combinations tested with OCR + Single Call approach

All components are Apache 2.0 licensed (OSS, commercial-friendly).
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

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("⚠️  PaddleOCR not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠️  EasyOCR not available")

try:
    from transformers import AutoModel, AutoTokenizer
    import torch
    DEEPSEEK_OCR_AVAILABLE = True
except ImportError:
    DEEPSEEK_OCR_AVAILABLE = False
    print("⚠️  DeepSeek-OCR not available (transformers/torch not installed)")

# Configuration
OLLAMA_HOST = "http://localhost:11434"

# OCR engines to test
OCR_ENGINES = []
if TESSERACT_AVAILABLE:
    OCR_ENGINES.append({"name": "tesseract", "display": "Tesseract OCR"})
if PADDLEOCR_AVAILABLE:
    OCR_ENGINES.append({"name": "paddleocr", "display": "PaddleOCR"})
if EASYOCR_AVAILABLE:
    OCR_ENGINES.append({"name": "easyocr", "display": "EasyOCR"})
if DEEPSEEK_OCR_AVAILABLE:
    OCR_ENGINES.append({"name": "deepseek", "display": "DeepSeek-OCR (VLM)"})

# LLM models to test (all Apache 2.0 licensed)
LLM_MODELS = [
    {"name": "qwen2.5:3b", "display": "Qwen 2.5 3B", "type": "general"},
    {"name": "qwen2.5:7b", "display": "Qwen 2.5 7B", "type": "general"},
    {"name": "meditron:7b", "display": "Meditron 7B", "type": "medical"},
    {"name": "biomistral:7b", "display": "BioMistral 7B", "type": "medical"},
]

# Combined system prompt
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


def extract_text_paddleocr(file_bytes: bytes) -> str:
    """Extract text using PaddleOCR"""
    # Initialize PaddleOCR (use English model, disable GPU warnings)
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            import numpy as np
            img_array = np.array(img)
            result = ocr.ocr(img_array, cls=True)

            # Extract text from result
            page_text = []
            if result and result[0]:
                for line in result[0]:
                    page_text.append(line[1][0])  # [1][0] contains the text

            extracted_texts.append(f"=== Page {i} ===\n{' '.join(page_text)}")
        return "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        import numpy as np
        img_array = np.array(img)
        result = ocr.ocr(img_array, cls=True)

        text_lines = []
        if result and result[0]:
            for line in result[0]:
                text_lines.append(line[1][0])

        return "\n".join(text_lines)


def extract_text_easyocr(file_bytes: bytes) -> str:
    """Extract text using EasyOCR"""
    # Initialize EasyOCR (English only, GPU disabled for consistency)
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            import numpy as np
            img_array = np.array(img)
            result = reader.readtext(img_array)

            # Extract text from result
            page_text = [item[1] for item in result]  # item[1] contains the text
            extracted_texts.append(f"=== Page {i} ===\n{' '.join(page_text)}")
        return "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        import numpy as np
        img_array = np.array(img)
        result = reader.readtext(img_array)

        text_lines = [item[1] for item in result]
        return "\n".join(text_lines)


def extract_text_deepseek_ocr(file_bytes: bytes) -> str:
    """Extract text using DeepSeek-OCR (VLM-based)"""
    # Load model (cached after first load)
    model_name = 'deepseek-ai/DeepSeek-OCR'

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        # Try to load with flash_attention_2 if available, fall back to eager
        try:
            model = AutoModel.from_pretrained(
                model_name,
                _attn_implementation='flash_attention_2',
                trust_remote_code=True,
                use_safetensors=True
            )
        except Exception:
            # Fall back to eager attention if flash_attention_2 not available
            model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_safetensors=True
            )

        # Move to appropriate device
        if torch.backends.mps.is_available():
            # Use MPS for Apple Silicon
            device = torch.device("mps")
            model = model.eval().to(device).to(torch.float16)
        elif torch.cuda.is_available():
            # Use CUDA if available
            device = torch.device("cuda")
            model = model.eval().to(device).to(torch.bfloat16)
        else:
            # CPU fallback
            device = torch.device("cpu")
            model = model.eval().to(device)

    except Exception as e:
        raise Exception(f"Failed to load DeepSeek-OCR model: {e}")

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []

        for i, img in enumerate(images, 1):
            # DeepSeek-OCR expects PIL images
            # Call the model to extract text (API depends on model implementation)
            # This is a placeholder - actual API may differ
            try:
                # Convert image to format expected by model
                inputs = tokenizer(images=img, return_tensors="pt").to(device)
                with torch.no_grad():
                    outputs = model.generate(**inputs)
                page_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                extracted_texts.append(f"=== Page {i} ===\n{page_text}")
            except Exception as e:
                extracted_texts.append(f"=== Page {i} ===\n[Error: {str(e)}]")

        return "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        try:
            inputs = tokenizer(images=img, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            return f"[Error: {str(e)}]"


def extract_text_with_ocr(file_bytes: bytes, ocr_engine: str) -> tuple[str, float]:
    """Extract text using specified OCR engine, return (text, time_taken)"""
    start_time = time.time()

    if ocr_engine == "tesseract":
        text = extract_text_tesseract(file_bytes)
    elif ocr_engine == "paddleocr":
        text = extract_text_paddleocr(file_bytes)
    elif ocr_engine == "easyocr":
        text = extract_text_easyocr(file_bytes)
    elif ocr_engine == "deepseek":
        text = extract_text_deepseek_ocr(file_bytes)
    else:
        raise ValueError(f"Unknown OCR engine: {ocr_engine}")

    time_taken = time.time() - start_time
    return text, time_taken


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
                    ocr_text: str, ocr_time: float) -> dict:
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
    print(f"📤 Calling {llm_display}...")

    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": llm_name,
        "prompt": get_combined_prompt(ocr_text),
        "system": COMBINED_SYSTEM_PROMPT,
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
        result["timings"]["total"] = round(ocr_time + llm_time, 2)
        result["error"] = str(e)
        print(f"❌ Error: {e}")

    return result


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 comprehensive_benchmark.py <pdf_or_image_path>")
        print("\nEXAMPLE:")
        print("  python3 comprehensive_benchmark.py /path/to/lab_report.pdf")
        print("\nNOTE:")
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
        print("❌ No OCR engines available. Install at least one:")
        print("   pip3 install pytesseract")
        print("   pip3 install paddleocr paddlepaddle")
        print("   pip3 install easyocr")
        return

    print("\n" + "=" * 80)
    print("  COMPREHENSIVE BENCHMARK: OCR Engines × LLM Models")
    print("=" * 80)
    print(f"\n📄 Document: {file_path}")
    print(f"\n📊 Test Matrix:")
    print(f"   OCR Engines: {len(OCR_ENGINES)} ({', '.join(e['display'] for e in OCR_ENGINES)})")
    print(f"   LLM Models: {len(LLM_MODELS)} ({', '.join(m['display'] for m in LLM_MODELS)})")
    print(f"   Total Combinations: {len(OCR_ENGINES) * len(LLM_MODELS)}")

    # Load file
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    # Run OCR for each engine
    print(f"\n{'=' * 80}")
    print("STEP 1: OCR Text Extraction")
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

    # Run all combinations
    print(f"\n{'=' * 80}")
    print("STEP 2: LLM Processing (All Combinations)")
    print('=' * 80)

    all_results = []

    for ocr_config in OCR_ENGINES:
        ocr_name = ocr_config["name"]
        ocr_data = ocr_results.get(ocr_name)

        if not ocr_data or not ocr_data.get("text"):
            print(f"\n⚠️  Skipping {ocr_config['display']} - OCR failed")
            continue

        for llm_config in LLM_MODELS:
            result = run_combination(
                file_path=file_path,
                ocr_engine=ocr_name,
                ocr_display=ocr_config["display"],
                llm_name=llm_config["name"],
                llm_display=llm_config["display"],
                llm_type=llm_config["type"],
                ocr_text=ocr_data["text"],
                ocr_time=ocr_data["time"]
            )
            all_results.append(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"comprehensive_results_{timestamp}.json"

    output_data = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "document": file_path,
        "ocr_engines_tested": len(OCR_ENGINES),
        "llm_models_tested": len(LLM_MODELS),
        "total_combinations": len(all_results),
        "ocr_results": ocr_results,
        "combinations": all_results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

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
            total_time = result["timings"].get("total", 0)
            error = result.get("error")

            if error:
                print(f"  ❌ {llm_display:20} - {error[:50]}")
            else:
                extraction = result.get("extraction", {})
                item_count = 0
                if extraction and "parameters" in extraction:
                    item_count = len(extraction["parameters"])
                elif extraction and "medications" in extraction:
                    item_count = len(extraction["medications"])

                print(f"  ✅ {llm_display:20} - {total_time:6.2f}s ({item_count} items)")

    print(f"\n💾 Detailed results saved to: {output_file}")
    print(f"\n📝 Next step: Run evaluation to compare combinations:")
    print(f"   python3 evaluate_comprehensive.py {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
