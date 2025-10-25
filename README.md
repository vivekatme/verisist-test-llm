# Verisist LLM Testing

Test project for comparing two document processing approaches:
1. **Vision LLM** - Direct image processing (slow but accurate)
2. **OCR + Text LLM** - Hybrid approach (~10x faster, similar accuracy)

## Quick Start

```bash
# 1. Install prerequisites (one-time setup)
brew install ollama poppler tesseract

# 2. Pull models (~12GB total, one-time)
ollama pull qwen2.5vl:7b  # Vision model
ollama pull qwen2.5:7b    # Text model

# 3. Run setup script (creates venv, installs Python deps)
./setup.sh

# 4. Test with your PDF (OCR mode - fastest)
source venv/bin/activate
python test_ollama.py /path/to/document.pdf --extract

# 5. Compare both modes side-by-side
python test_ollama.py /path/to/document.pdf --mode=compare --extract
```

## Processing Modes

### Vision Mode (Slow)
- **How it works**: PDF/Image → Vision LLM (Qwen2.5-VL)
- **Speed**: ~2-5 minutes for validation + extraction
- **Accuracy**: Very high
- **Use when**: Need maximum accuracy, don't care about speed

### OCR Mode (Fast) ⚡
- **How it works**: PDF/Image → Tesseract OCR → Text LLM (Qwen2.5)
- **Speed**: ~15-35 seconds for validation + extraction (10x faster!)
- **Accuracy**: High (depends on OCR quality)
- **Use when**: Need fast processing, documents have good print quality

## Usage

```bash
# OCR mode (default, fastest)
python test_ollama.py /path/to/document.pdf --extract

# Vision mode (slowest, most accurate)
python test_ollama.py /path/to/document.pdf --mode=vision --extract

# Compare both modes with timing
python test_ollama.py /path/to/document.pdf --mode=compare --extract
```

## What It Does

### Phase 1: Validation
1. **Vision Mode**: Sends image directly to Qwen2.5-VL vision model
2. **OCR Mode**: Extracts text with Tesseract, sends to Qwen2.5 text model
3. **Result**: Document classification (LAB_REPORT, PRESCRIPTION, etc.)

### Phase 2: Extraction (Optional - use `--extract` flag)
1. **Vision Mode**: Sends image to Qwen2.5-VL with type-specific prompts
2. **OCR Mode**: Sends extracted text to Qwen2.5 with type-specific prompts
3. **Result**: Structured data extraction
   - **Lab Reports**: Test parameters, values, units, ranges, status
   - **Prescriptions**: Medications, dosages, frequency, duration

## Performance Comparison

Based on 2-page PDF lab report:

| Mode | Validation | Extraction | Total | Accuracy |
|------|-----------|-----------|-------|----------|
| **Vision** | ~15-30s | ~2-4min | ~2-5min | Very High |
| **OCR** | ~5-10s | ~10-20s | ~15-35s | High |

**Speed Improvement**: ~10x faster with OCR mode

## Expected Output (OCR Mode)

```
MODE: OCR + TEXT LLM (FAST)
================================================================================

────────────────────────────────────────────────────────────────────────────────
STEP 1: OCR Text Extraction
────────────────────────────────────────────────────────────────────────────────
   Running OCR on document...
   PDF has 2 page(s)
      Page 1: 1243 characters
      Page 2: 987 characters
✅ OCR completed in 2.35s
   Extracted 2230 characters

────────────────────────────────────────────────────────────────────────────────
STEP 2: Validation (Text LLM)
────────────────────────────────────────────────────────────────────────────────
✅ Validation completed in 8.52s

📋 Validation Result:
{
  "is_health_document": true,
  "document_type": "LAB_REPORT",
  "confidence": 0.95,
  "reasoning": "Document contains medical test parameters",
  "lab_name": "Apollo Diagnostics",
  "document_date": "2025-09-30"
}

────────────────────────────────────────────────────────────────────────────────
STEP 3: Extraction (Text LLM) - LAB_REPORT
────────────────────────────────────────────────────────────────────────────────
✅ Extraction completed in 15.23s

📄 Extracted Data:
{
  "title": "Lipid Profile - Apollo Diagnostics - John Doe",
  "documentType": "LAB_REPORT",
  "documentDate": "2025-09-30",
  "labName": "Apollo Diagnostics",
  "patientName": "John Doe",
  "testType": "Lipid Profile",
  "parameters": [
    {
      "name": "Total Cholesterol",
      "value": 245,
      "unit": "mg/dL",
      "referenceRange": {"min": 0, "max": 200},
      "status": "HIGH"
    }
  ]
}

📊 Extracted 8 test parameters

================================================================================
⏱️  TOTAL TIME: 26.10s
================================================================================
```

## Requirements

### Vision Mode
- Ollama with qwen2.5vl:7b model
- pdf2image, Pillow (for PDF processing)

### OCR Mode
- Ollama with qwen2.5:7b model
- Tesseract OCR
- pytesseract, pdf2image, Pillow

## Recommendation

**Use OCR mode for production** - It's 10x faster with similar accuracy. The speed difference is significant:
- Vision: 2-5 minutes per document
- OCR: 15-35 seconds per document

For a batch of 100 documents:
- Vision mode: ~3-8 hours
- OCR mode: ~25-60 minutes ⚡

## Files

- `test_ollama.py` - Main test script with both modes
- `requirements.txt` - Python dependencies
- `setup.sh` - Automated setup script
- `README.md` - This file
