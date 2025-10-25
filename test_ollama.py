#!/usr/bin/env python3
"""
Test script for Ollama with PDFs and images.
Compares two approaches:
1. Vision LLM (direct image processing) - SLOW but accurate
2. OCR + Text LLM (hybrid) - FAST and accurate
"""

import base64
import json
import requests
import time
from pathlib import Path
from io import BytesIO

# Optional: PDF support (install with: pip3 install pdf2image Pillow)
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PDF support not available. Install with: pip3 install pdf2image Pillow")
    print("    Also requires poppler-utils: brew install poppler")

# Optional: OCR support (install with: pip3 install pytesseract)
try:
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False
    print("⚠️  OCR support not available. Install with: pip3 install pytesseract")
    print("    Also requires tesseract: brew install tesseract")

# Configuration
OLLAMA_HOST = "http://localhost:11434"
VISION_MODEL = "qwen2.5vl:7b"  # Vision model for image processing
TEXT_MODEL = "qwen2.5:7b"       # Text-only model for OCR+LLM mode

# Test prompts for Vision LLM mode
VALIDATION_SYSTEM_PROMPT_VISION = """You are a medical document classifier. Analyze the image and determine if it's a health-related document."""

VALIDATION_USER_PROMPT_VISION = """Analyze this document image and respond ONLY with valid JSON in this exact format:

{
  "is_health_document": true or false,
  "document_type": "PRESCRIPTION" or "LAB_REPORT" or "MEDICAL_BILL" or null,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "lab_name": "name if it's a lab report" or null,
  "document_date": "YYYY-MM-DD" or null
}

IMPORTANT: Respond with ONLY the JSON object, no other text."""

# Extraction prompts
EXTRACTION_SYSTEM_PROMPT = """You are a medical data extraction specialist. Extract structured information from medical documents accurately."""

def get_extraction_prompt(document_type: str, validation_result: dict) -> str:
    """Get appropriate extraction prompt based on document type."""

    if document_type == "LAB_REPORT":
        return f"""Extract all test parameters from this lab report image.

**Lab Name**: {validation_result.get('lab_name', 'Unknown')}
**Document Date**: {validation_result.get('document_date', 'Unknown')}

**Output Format (JSON only)**:
```json
{{
  "title": "Test Type - Lab Name - Patient Name",
  "documentType": "LAB_REPORT",
  "documentDate": "YYYY-MM-DD",
  "labName": "Lab name",
  "patientName": "Patient name if visible",
  "testType": "e.g., Lipid Profile, CBC",
  "parameters": [
    {{
      "name": "Total Cholesterol",
      "value": 245,
      "unit": "mg/dL",
      "referenceRange": {{"min": 0, "max": 200}},
      "status": "HIGH"
    }}
  ]
}}
```

**Instructions**:
1. Extract ALL test parameters with values and units
2. Include reference ranges (min/max) for each parameter
3. Determine status: NORMAL, LOW, or HIGH
4. Extract patient name if visible
5. Return ONLY valid JSON, no markdown formatting"""

    elif document_type == "PRESCRIPTION":
        return f"""Extract all medications from this prescription image.

**Document Date**: {validation_result.get('document_date', 'Unknown')}

**Output Format (JSON only)**:
```json
{{
  "title": "Prescription - Doctor Name - Patient Name",
  "documentType": "PRESCRIPTION",
  "documentDate": "YYYY-MM-DD",
  "patientName": "Patient name if visible",
  "doctorName": "Doctor name if visible",
  "medications": [
    {{
      "name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "Thrice daily",
      "duration": "5 days",
      "instructions": "After food"
    }}
  ]
}}
```

**Instructions**:
1. Extract ALL medications listed
2. Include dosage, frequency, duration, and instructions
3. Extract doctor and patient names if visible
4. Return ONLY valid JSON, no markdown formatting"""

    else:
        return """Extract all relevant information from this medical document in JSON format."""


# Text-based prompts for OCR + LLM mode
VALIDATION_SYSTEM_PROMPT_OCR = """You are a medical document classifier. Analyze the extracted text and determine if it's a health-related document."""

def get_validation_prompt_ocr(ocr_text: str) -> str:
    return f"""Analyze this OCR-extracted text from a document and respond ONLY with valid JSON in this exact format:

{{
  "is_health_document": true or false,
  "document_type": "PRESCRIPTION" or "LAB_REPORT" or "MEDICAL_BILL" or null,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "lab_name": "name if it's a lab report" or null,
  "document_date": "YYYY-MM-DD" or null
}}

IMPORTANT: Respond with ONLY the JSON object, no other text.

**OCR Text:**
{ocr_text}
"""

EXTRACTION_SYSTEM_PROMPT_OCR = """You are a medical data extraction specialist. Extract structured information from OCR-extracted text accurately."""

def get_extraction_prompt_ocr(document_type: str, validation_result: dict, ocr_text: str) -> str:
    """Get appropriate extraction prompt for OCR mode based on document type."""

    if document_type == "LAB_REPORT":
        return f"""Extract all test parameters from this lab report text.

**Lab Name**: {validation_result.get('lab_name', 'Unknown')}
**Document Date**: {validation_result.get('document_date', 'Unknown')}

**Output Format (JSON only)**:
```json
{{
  "title": "Test Type - Lab Name - Patient Name",
  "documentType": "LAB_REPORT",
  "documentDate": "YYYY-MM-DD",
  "labName": "Lab name",
  "patientName": "Patient name if visible",
  "testType": "e.g., Lipid Profile, CBC",
  "parameters": [
    {{
      "name": "Total Cholesterol",
      "value": 245,
      "unit": "mg/dL",
      "referenceRange": {{"min": 0, "max": 200}},
      "status": "HIGH"
    }}
  ]
}}
```

**Instructions**:
1. Extract ALL test parameters with values and units
2. Include reference ranges (min/max) for each parameter
3. Determine status: NORMAL, LOW, or HIGH
4. Extract patient name if visible
5. Return ONLY valid JSON, no markdown formatting

**OCR Text:**
{ocr_text}
"""

    elif document_type == "PRESCRIPTION":
        return f"""Extract all medications from this prescription text.

**Document Date**: {validation_result.get('document_date', 'Unknown')}

**Output Format (JSON only)**:
```json
{{
  "title": "Prescription - Doctor Name - Patient Name",
  "documentType": "PRESCRIPTION",
  "documentDate": "YYYY-MM-DD",
  "patientName": "Patient name if visible",
  "doctorName": "Doctor name if visible",
  "medications": [
    {{
      "name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "Thrice daily",
      "duration": "5 days",
      "instructions": "After food"
    }}
  ]
}}
```

**Instructions**:
1. Extract ALL medications listed
2. Include dosage, frequency, duration, and instructions
3. Extract doctor and patient names if visible
4. Return ONLY valid JSON, no markdown formatting

**OCR Text:**
{ocr_text}
"""

    else:
        return f"""Extract all relevant information from this medical document text in JSON format.

**OCR Text:**
{ocr_text}
"""


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


def convert_pdf_to_image_base64(pdf_bytes: bytes) -> str:
    """Convert PDF to base64-encoded image (all pages combined vertically)"""
    if not PDF_SUPPORT:
        raise Exception("PDF support not installed. Run: pip3 install pdf2image Pillow && brew install poppler")

    print(f"   Converting PDF to images...")
    images = convert_from_bytes(pdf_bytes, dpi=200)
    if not images:
        raise ValueError("PDF conversion produced no images")

    print(f"   PDF has {len(images)} page(s)")

    # Single page - just return it
    if len(images) == 1:
        img_buffer = BytesIO()
        images[0].save(img_buffer, format='JPEG', quality=95)
        img_bytes = img_buffer.getvalue()
        print(f"   Single page converted: {len(img_bytes)} bytes")
        return base64.b64encode(img_bytes).decode()

    # Multi-page - combine vertically
    total_width = max(img.width for img in images)
    total_height = sum(img.height for img in images)

    print(f"   Combining {len(images)} pages into one image...")
    combined = Image.new('RGB', (total_width, total_height), 'white')
    y_offset = 0
    for img in images:
        x_offset = (total_width - img.width) // 2
        combined.paste(img, (x_offset, y_offset))
        y_offset += img.height

    img_buffer = BytesIO()
    combined.save(img_buffer, format='JPEG', quality=95)
    img_bytes = img_buffer.getvalue()

    print(f"   Combined image: {len(img_bytes)} bytes ({total_width}x{total_height})")
    return base64.b64encode(img_bytes).decode()


def extract_text_ocr(file_bytes: bytes) -> str:
    """Extract text from PDF or image using OCR"""
    if not OCR_SUPPORT:
        raise Exception("OCR support not installed. Run: pip3 install pytesseract && brew install tesseract")

    if not PDF_SUPPORT:
        raise Exception("PDF support not installed. Run: pip3 install pdf2image Pillow && brew install poppler")

    print(f"   Running OCR on document...")

    # Check if PDF
    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        # Convert PDF to images
        images = convert_from_bytes(file_bytes, dpi=300)  # Higher DPI for better OCR
        print(f"   PDF has {len(images)} page(s)")

        # OCR each page
        extracted_texts = []
        for i, img in enumerate(images, 1):
            text = pytesseract.image_to_string(img)
            extracted_texts.append(f"=== Page {i} ===\n{text}")
            print(f"      Page {i}: {len(text)} characters")

        full_text = "\n\n".join(extracted_texts)
    else:
        # Direct image OCR
        from PIL import Image
        img = Image.open(BytesIO(file_bytes))
        full_text = pytesseract.image_to_string(img)
        print(f"   Extracted {len(full_text)} characters")

    return full_text


def test_extraction(image_base64: str, validation_result: dict):
    """Test extraction phase after successful validation"""
    document_type = validation_result.get("document_type")

    if not document_type or document_type not in ["LAB_REPORT", "PRESCRIPTION"]:
        print(f"\n⚠️  Skipping extraction - document type '{document_type}' not supported for extraction test")
        return

    print(f"\n" + "=" * 80)
    print(f"  PHASE 2: EXTRACTION - {document_type}")
    print("=" * 80)

    # Get appropriate extraction prompt
    extraction_prompt = get_extraction_prompt(document_type, validation_result)

    # Prepare Ollama request
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": VISION_MODEL,
        "prompt": extraction_prompt,
        "system": EXTRACTION_SYSTEM_PROMPT,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }

    print(f"\n📤 Sending extraction request to Ollama...")
    print(f"   Model: {VISION_MODEL}")
    print(f"   Document Type: {document_type}")

    try:
        response = requests.post(url, json=payload, timeout=180)  # 3 min timeout for extraction

        print(f"\n📥 Extraction response received:")
        print(f"   Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("response", "")

            print(f"   ✅ Success!")
            print(f"\n📄 Extracted Data:")
            print("-" * 80)
            print(llm_response)
            print("-" * 80)

            # Try to parse as JSON
            try:
                parsed = json.loads(llm_response)
                print(f"\n✅ Valid JSON response:")
                print(json.dumps(parsed, indent=2))

                # Show summary of extracted data
                if document_type == "LAB_REPORT" and "parameters" in parsed:
                    print(f"\n📊 Extracted {len(parsed['parameters'])} test parameters")
                elif document_type == "PRESCRIPTION" and "medications" in parsed:
                    print(f"\n💊 Extracted {len(parsed['medications'])} medications")

            except json.JSONDecodeError as e:
                print(f"\n⚠️  Response is not valid JSON: {e}")
        else:
            print(f"   ❌ Error response:")
            print(f"   {response.text}")

    except requests.exceptions.Timeout:
        print(f"❌ Extraction timed out after 180 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Extraction request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during extraction: {e}")


def test_ollama_with_sample_file(file_path: str, test_extraction_phase: bool = False):
    """Test Ollama with a sample PDF or image file"""
    print(f"\n" + "=" * 80)
    print(f"  PHASE 1: VALIDATION")
    print("=" * 80)
    print(f"\nTesting Ollama vision model: {VISION_MODEL}")
    print(f"Ollama host: {OLLAMA_HOST}")
    print(f"Document: {file_path}")

    # Read file
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"✅ File loaded: {len(file_bytes)} bytes")

        # Check if PDF
        is_pdf = file_bytes.startswith(b'%PDF')
        print(f"   File type: {'PDF' if is_pdf else 'Image'}")

        # Convert to base64 image
        if is_pdf:
            image_base64 = convert_pdf_to_image_base64(file_bytes)
        else:
            image_base64 = base64.b64encode(file_bytes).decode()

        print(f"   Base64 length: {len(image_base64)} chars")

    except Exception as e:
        print(f"❌ Failed to process file: {e}")
        return

    # Prepare Ollama API request
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": VISION_MODEL,
        "prompt": VALIDATION_USER_PROMPT_VISION,
        "system": VALIDATION_SYSTEM_PROMPT_VISION,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }

    print(f"\n📤 Sending validation request to Ollama...")
    print(f"   Model: {VISION_MODEL}")
    print(f"   Stream: False")
    print(f"   Temperature: 0.1")

    validation_result = None

    try:
        # Call Ollama
        response = requests.post(url, json=payload, timeout=120)

        print(f"\n📥 Validation response received:")
        print(f"   Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("response", "")

            print(f"   ✅ Success!")
            print(f"\n📄 LLM Response:")
            print("-" * 80)
            print(llm_response)
            print("-" * 80)

            # Try to parse as JSON
            try:
                validation_result = json.loads(llm_response)
                print(f"\n✅ Valid JSON response:")
                print(json.dumps(validation_result, indent=2))
            except json.JSONDecodeError as e:
                print(f"\n⚠️  Response is not valid JSON: {e}")
        else:
            print(f"   ❌ Error response:")
            print(f"   {response.text}")

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 120 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Test extraction if requested and validation succeeded
    if test_extraction_phase and validation_result and validation_result.get("is_health_document"):
        test_extraction(image_base64, validation_result)


def test_ollama_status():
    """Check if Ollama is running and required models are available"""
    print("\n🔍 Checking Ollama status...")
    print("=" * 80)

    try:
        # Check Ollama is running
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get("models", [])
            model_names = [m.get("name") for m in models]

            print(f"✅ Ollama is running")
            print(f"   Available models: {len(models)}")

            # Check for vision model
            vision_found = False
            text_found = False

            for model in models:
                model_name = model.get("name")
                if model_name == VISION_MODEL:
                    vision_found = True
                    print(f"   ✅ Vision Model '{VISION_MODEL}' is available")
                    print(f"      Size: {model.get('size') / 1e9:.2f} GB")
                elif model_name == TEXT_MODEL:
                    text_found = True
                    print(f"   ✅ Text Model '{TEXT_MODEL}' is available")
                    print(f"      Size: {model.get('size') / 1e9:.2f} GB")

            if not vision_found:
                print(f"   ⚠️  Vision model '{VISION_MODEL}' not found")
                print(f"   Run: ollama pull {VISION_MODEL}")

            if not text_found:
                print(f"   ⚠️  Text model '{TEXT_MODEL}' not found")
                print(f"   Run: ollama pull {TEXT_MODEL}")

            if not vision_found and not text_found:
                print("\n❌ No required models found. Install at least one:")
                print(f"   ollama pull {VISION_MODEL}  # For vision mode")
                print(f"   ollama pull {TEXT_MODEL}    # For OCR mode")
                return False

            return True
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {OLLAMA_HOST}")
        print(f"   Make sure Ollama is running")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


def test_ocr_mode(file_path: str, test_extraction_phase: bool = False):
    """Test OCR + Text LLM mode"""
    print(f"\n" + "=" * 80)
    print(f"  MODE: OCR + TEXT LLM (FAST)")
    print("=" * 80)
    print(f"Document: {file_path}")

    total_start = time.time()

    # Read file
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"✅ File loaded: {len(file_bytes)} bytes")
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return

    # Phase 1: OCR Extraction
    print(f"\n{'─' * 80}")
    print("STEP 1: OCR Text Extraction")
    print('─' * 80)
    ocr_start = time.time()
    try:
        ocr_text = extract_text_ocr(file_bytes)
        ocr_time = time.time() - ocr_start
        print(f"✅ OCR completed in {ocr_time:.2f}s")
        print(f"   Extracted {len(ocr_text)} characters")
        print(f"\n   First 200 characters:")
        print(f"   {ocr_text[:200]}...")
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return

    # Phase 2: Validation with Text LLM
    print(f"\n{'─' * 80}")
    print("STEP 2: Validation (Text LLM)")
    print('─' * 80)

    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": TEXT_MODEL,
        "prompt": get_validation_prompt_ocr(ocr_text),
        "system": VALIDATION_SYSTEM_PROMPT_OCR,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9}
    }

    validation_start = time.time()
    validation_result = None

    try:
        response = requests.post(url, json=payload, timeout=60)
        validation_time = time.time() - validation_start

        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("response", "")
            print(f"✅ Validation completed in {validation_time:.2f}s")

            try:
                validation_result = json.loads(llm_response)
                print(f"\n📋 Validation Result:")
                print(json.dumps(validation_result, indent=2))
            except json.JSONDecodeError as e:
                print(f"⚠️  Response is not valid JSON: {e}")
                print(f"Raw response: {llm_response}")
        else:
            print(f"❌ Validation failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return

    # Phase 3: Extraction (if requested)
    if test_extraction_phase and validation_result and validation_result.get("is_health_document"):
        document_type = validation_result.get("document_type")

        if document_type in ["LAB_REPORT", "PRESCRIPTION"]:
            print(f"\n{'─' * 80}")
            print(f"STEP 3: Extraction (Text LLM) - {document_type}")
            print('─' * 80)

            extraction_prompt = get_extraction_prompt_ocr(document_type, validation_result, ocr_text)

            payload = {
                "model": TEXT_MODEL,
                "prompt": extraction_prompt,
                "system": EXTRACTION_SYSTEM_PROMPT_OCR,
                "stream": False,
                "options": {"temperature": 0.1, "top_p": 0.9}
            }

            extraction_start = time.time()

            try:
                response = requests.post(url, json=payload, timeout=120)
                extraction_time = time.time() - extraction_start

                if response.status_code == 200:
                    result = response.json()
                    llm_response = result.get("response", "")
                    print(f"✅ Extraction completed in {extraction_time:.2f}s")

                    try:
                        extracted = json.loads(llm_response)
                        print(f"\n📄 Extracted Data:")
                        print(json.dumps(extracted, indent=2))

                        if document_type == "LAB_REPORT" and "parameters" in extracted:
                            print(f"\n📊 Extracted {len(extracted['parameters'])} test parameters")
                        elif document_type == "PRESCRIPTION" and "medications" in extracted:
                            print(f"\n💊 Extracted {len(extracted['medications'])} medications")
                    except json.JSONDecodeError:
                        print(f"⚠️  Response is not valid JSON")
                        print(f"Raw response: {llm_response}")
                else:
                    print(f"❌ Extraction failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Extraction error: {e}")

    total_time = time.time() - total_start
    print(f"\n{'=' * 80}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'=' * 80}")


def test_ocr_single_call(file_path: str):
    """Test OCR + Single Combined Call for validation AND extraction"""
    print(f"\n" + "=" * 80)
    print(f"  MODE: OCR + SINGLE COMBINED CALL (FASTEST)")
    print("=" * 80)
    print(f"Document: {file_path}")

    total_start = time.time()

    # Read file
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"✅ File loaded: {len(file_bytes)} bytes")
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return

    # Step 1: OCR Extraction
    print(f"\n{'─' * 80}")
    print("STEP 1: OCR Text Extraction")
    print('─' * 80)
    ocr_start = time.time()
    try:
        ocr_text = extract_text_ocr(file_bytes)
        ocr_time = time.time() - ocr_start
        print(f"✅ OCR completed in {ocr_time:.2f}s")
        print(f"   Extracted {len(ocr_text)} characters")
        print(f"\n   First 200 characters:")
        print(f"   {ocr_text[:200]}...")
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return

    # Step 2: Single Combined LLM Call (Validation + Extraction)
    print(f"\n{'─' * 80}")
    print("STEP 2: Combined Validation + Extraction (Single LLM Call)")
    print('─' * 80)

    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": TEXT_MODEL,
        "prompt": get_combined_prompt(ocr_text),
        "system": COMBINED_SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9}
    }

    combined_start = time.time()

    try:
        response = requests.post(url, json=payload, timeout=120)
        combined_time = time.time() - combined_start

        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("response", "")
            print(f"✅ Combined call completed in {combined_time:.2f}s")

            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                cleaned_response = llm_response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()

                combined_result = json.loads(cleaned_response)

                # Display validation results
                if "validation" in combined_result:
                    print(f"\n📋 Validation Result:")
                    print(json.dumps(combined_result["validation"], indent=2))

                # Display extraction results
                if "extraction" in combined_result:
                    print(f"\n📄 Extraction Result:")
                    print(json.dumps(combined_result["extraction"], indent=2))

                    # Show summary
                    extraction = combined_result["extraction"]
                    if "parameters" in extraction:
                        print(f"\n📊 Extracted {len(extraction['parameters'])} test parameters")
                    elif "medications" in extraction:
                        print(f"\n💊 Extracted {len(extraction['medications'])} medications")
                else:
                    print(f"\n✅ Full Response:")
                    print(json.dumps(combined_result, indent=2))

            except json.JSONDecodeError as e:
                print(f"⚠️  Response is not valid JSON: {e}")
                print(f"\nRaw response:")
                print(llm_response)
        else:
            print(f"❌ Combined call failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Combined call error: {e}")

    total_time = time.time() - total_start
    print(f"\n{'=' * 80}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'=' * 80}")

    # Show time savings
    print(f"\n💡 Time Breakdown:")
    print(f"   OCR:           {ocr_time:.2f}s")
    print(f"   Combined Call: {combined_time:.2f}s")
    print(f"   Total:         {total_time:.2f}s")
    print(f"\n   Note: Single call does validation + extraction together!")
    print(f"   Compare with separate calls mode to see time savings.")


def test_vision_mode(file_path: str, test_extraction_phase: bool = False):
    """Test Vision LLM mode (renamed from test_ollama_with_sample_file)"""
    print(f"\n" + "=" * 80)
    print(f"  MODE: VISION LLM (SLOW)")
    print("=" * 80)
    print(f"Document: {file_path}")

    total_start = time.time()

    # ... rest of existing test_ollama_with_sample_file function
    # (This is the existing function, just renamed for clarity)
    test_ollama_with_sample_file(file_path, test_extraction_phase)

    total_time = time.time() - total_start
    print(f"\n{'=' * 80}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 80)
    print("  OLLAMA DOCUMENT PROCESSING TEST")
    print("  Compare: Vision LLM vs OCR + Text LLM")
    print("=" * 80)

    # Check Ollama status first
    if not test_ollama_status():
        print("\n❌ Ollama check failed. Please fix the issues above.")
        exit(1)

    # Parse arguments
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

        # Check for flags
        test_extraction_phase = '--extract' in sys.argv or '-e' in sys.argv
        mode = None
        for arg in sys.argv:
            if arg.startswith('--mode='):
                mode = arg.split('=')[1]

        if not Path(file_path).exists():
            print(f"\n❌ File not found: {file_path}")
            exit(1)

        # Run test based on mode
        if mode == 'vision':
            test_vision_mode(file_path, test_extraction_phase)
        elif mode == 'ocr':
            if not OCR_SUPPORT:
                print("\n❌ OCR mode requires pytesseract. Install with:")
                print("   pip3 install pytesseract")
                print("   brew install tesseract")
                exit(1)
            test_ocr_mode(file_path, test_extraction_phase)
        elif mode == 'single':
            if not OCR_SUPPORT:
                print("\n❌ Single call mode requires pytesseract. Install with:")
                print("   pip3 install pytesseract")
                print("   brew install tesseract")
                exit(1)
            test_ocr_single_call(file_path)
        elif mode == 'compare':
            # Run both and compare
            print("\n" + "╔" + "═" * 78 + "╗")
            print("║" + " " * 25 + "COMPARISON MODE" + " " * 38 + "║")
            print("╚" + "═" * 78 + "╝")

            if not OCR_SUPPORT:
                print("\n❌ OCR mode requires pytesseract. Install with:")
                print("   pip3 install pytesseract")
                print("   brew install tesseract")
                print("\n⚠️  Falling back to vision-only mode...")
                test_vision_mode(file_path, test_extraction_phase)
            else:
                # Test all three modes
                # 1. OCR + Single Call (fastest)
                test_ocr_single_call(file_path)

                print("\n\n")

                # 2. OCR mode with separate calls
                test_ocr_mode(file_path, test_extraction_phase)

                print("\n\n")

                # 3. Vision mode (slowest)
                test_vision_mode(file_path, test_extraction_phase)

                print("\n" + "╔" + "═" * 78 + "╗")
                print("║" + " " * 28 + "COMPARISON SUMMARY" + " " * 31 + "║")
                print("╚" + "═" * 78 + "╝")
                print("\n📊 Compare the timing and accuracy of all three approaches above:")
                print("   1. OCR + Single Call: Fastest (validation + extraction in one call)")
                print("   2. OCR + Separate Calls: Fast (two separate LLM calls)")
                print("   3. Vision LLM: Slowest but most accurate (image processing)")
        else:
            # Default: run OCR mode if available, else vision
            if OCR_SUPPORT:
                test_ocr_mode(file_path, test_extraction_phase)
            else:
                print("\n⚠️  OCR not available, using Vision LLM mode...")
                test_vision_mode(file_path, test_extraction_phase)
    else:
        print("\n" + "=" * 80)
        print("USAGE:")
        print("  python3 test_ollama.py <pdf_or_image_path> [OPTIONS]")
        print()
        print("OPTIONS:")
        print("  --extract, -e          Also test extraction phase (Phase 2)")
        print("  --mode=vision          Use Vision LLM mode (image → LLM)")
        print("  --mode=ocr             Use OCR + Text LLM mode (separate calls)")
        print("  --mode=single          Use OCR + Single Combined Call (FASTEST)")
        print("  --mode=compare         Run all modes and compare results")
        print()
        print("EXAMPLES:")
        print("  # Test OCR + Single Call mode (fastest, recommended)")
        print("  python3 test_ollama.py /path/to/lab_report.pdf --mode=single")
        print()
        print("  # Test OCR mode with separate calls")
        print("  python3 test_ollama.py /path/to/lab_report.pdf --mode=ocr --extract")
        print()
        print("  # Test vision mode (slowest, most accurate)")
        print("  python3 test_ollama.py /path/to/lab_report.pdf --mode=vision --extract")
        print()
        print("  # Compare all three modes side-by-side")
        print("  python3 test_ollama.py /path/to/lab_report.pdf --mode=compare --extract")
        print()
        print("MODES COMPARISON:")
        print("  single:  OCR + 1 LLM call  → ~40-50s  (FASTEST, recommended)")
        print("  ocr:     OCR + 2 LLM calls → ~60-70s  (separate validation/extraction)")
        print("  vision:  Vision LLM        → ~140s    (slowest, most accurate)")
        print()
        print("REQUIREMENTS:")
        print("  Vision mode: qwen2.5vl:7b")
        print("  OCR modes:   qwen2.5:7b, pytesseract, tesseract")
        print("=" * 80)
        print()
        print("⚠️  No file path provided. Only Ollama status was checked.")
