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

## Benchmarking Framework

### Compare 3B vs 7B Models

Test the speed/accuracy tradeoff between smaller and larger models:

```bash
# Run benchmark (tests both models with same document)
python benchmark_models.py /path/to/document.pdf

# Analyze results
python evaluate_results.py benchmark_results_*.json
```

**Expected Output:**
- Performance comparison (3B is ~2x faster)
- Accuracy metrics (completeness score, item count)
- Field-by-field comparison
- Recommendation based on your priorities

### Comprehensive OCR × LLM Benchmark

Test all combinations of OCR engines and LLM models:

```bash
# Run comprehensive benchmark
python comprehensive_benchmark.py /path/to/document.pdf

# Analyze results with detailed matrices
python evaluate_comprehensive.py comprehensive_results_*.json
```

**What it tests:**
- **OCR Engines**: Tesseract, PaddleOCR, EasyOCR, DeepSeek-OCR (optional)
- **LLM Models**: Qwen 2.5 (3B, 7B), Meditron 7B, BioMistral 7B (Q6_K & Q4)
- **All combinations**: OCR × LLM matrix analysis

**Analysis includes:**
- Performance matrix (timing for each combination)
- Accuracy matrix (items extracted)
- Completeness scores (0-100)
- Best combination recommendations (fastest, most accurate, balanced)
- OCR engine comparison
- LLM model comparison

### Available Models

See [MODELS.md](MODELS.md) for full list of models, licenses, and installation instructions.

**Quick Downloads:**
```bash
# General purpose models
ollama pull qwen2.5:3b      # Fast (2.6GB)
ollama pull qwen2.5:7b      # Balanced (4.7GB)

# Medical-specialized models
ollama pull meditron:7b                      # Medical specialist (4.1GB, OFFICIAL)
ollama pull adrienbrault/biomistral-7b:Q6_K  # BioMistral Q6_K (5.9GB, higher quality)
ollama pull m/biomistral                     # BioMistral Q4 (4.4GB, faster)
```

All models are **Apache 2.0 licensed** (free for commercial use).

## OCR-Only Comparison

### Single Document

Compare OCR engines side-by-side without LLM processing:

```bash
# Compare all available OCR engines
python ocr_comparison.py /path/to/document.pdf

# Generates:
# - ocr_comparison_YYYYMMDD_HHMMSS.json (raw results)
# - ocr_comparison_YYYYMMDD_HHMMSS.html (visual comparison)

# Open HTML to view results
open ocr_comparison_*.html
```

### Batch OCR Comparison (Multiple Documents)

Process all documents in a directory and compare OCR engines:

```bash
# Process all documents with OCR comparison
python batch_ocr_comparison.py ~/Desktop/test-docs

# Generates:
# - batch_ocr_results_YYYYMMDD_HHMMSS/batch_ocr_summary.json
# - batch_ocr_results_YYYYMMDD_HHMMSS/ocr_dashboard.html

# Open dashboard
open batch_ocr_results_*/ocr_dashboard.html
```

**Dashboard Features:**
- Results grouped by document
- Filter by document or OCR engine
- View raw OCR text output for each engine
- Compare performance across all documents
- Speed/accuracy metrics for each engine

**OCR Engines Compared:**
- **Tesseract** - Fast, mature, CPU-based
- **PaddleOCR** - State-of-the-art accuracy, complex layouts
- **EasyOCR** - Deep learning, handwriting support
- **Surya OCR** - Modern multilingual (90+ languages), layout analysis
- **DeepSeek-OCR** - VLM-based (requires GPU ≥16GB VRAM)

**What You See:**
- Side-by-side OCR output text
- Character/word counts
- Processing times
- Quality comparison for manual assessment

**Use Case:** Determine which OCR engine gives best text quality before LLM processing.

## Batch Processing & Visual Dashboard

Process multiple documents and get interactive visual analysis:

```bash
# 1. Place your test documents in a directory
mkdir ~/Desktop/test-docs
# Add your PDF/image files here

# 2. Run batch benchmark (tests all documents)
python batch_benchmark.py ~/Desktop/test-docs

# This will:
# - Process each document individually
# - Test all OCR × LLM × Mode combinations
# - Generate individual result files
# - Create interactive HTML dashboard
# - Save to: batch_results_YYYYMMDD_HHMMSS/

# 3. Open the dashboard
open batch_results_*/dashboard.html
```

### Dashboard Features

The interactive HTML dashboard provides:

**📊 Overview Tab**
- All results in one table
- Performance across all documents
- Speed badges (fast/medium/slow)
- Success/error status

**📄 By Document Tab**
- Results grouped by document
- Average performance metrics
- Success rates
- Detailed drill-down views

**🔍 OCR Comparison Tab**
- Compare OCR engines across all documents
- Average OCR times
- Extraction accuracy
- Success rates

**🤖 LLM Comparison Tab**
- Compare models across documents
- extraction-only vs validation+extraction modes
- Speed and accuracy metrics
- Medical vs general model performance

**📝 Raw Outputs Tab**
- View full LLM responses for manual verification
- Filter by document or model
- See validation and extraction JSON
- View raw LLM text output
- Perfect for debugging and quality assurance

### Modes Tested

Each combination is tested in **2 modes**:

1. **extraction-only**: Skip validation, direct extraction (faster)
2. **validation+extraction**: Full validation + extraction (complete)

This shows the speed/accuracy tradeoff for each model.

## Files

**Single Document Testing:**
- `test_ollama.py` - Single model test (Vision vs OCR modes)
- `benchmark_models.py` - Compare 3B vs 7B models
- `evaluate_results.py` - Evaluate 3B vs 7B comparison

**Comprehensive Testing:**
- `comprehensive_benchmark.py` - Test all OCR × LLM × Mode combinations
- `evaluate_comprehensive.py` - Analyze comprehensive results

**OCR-Only Comparison:**
- `ocr_comparison.py` - Compare OCR engines for single document
- `batch_ocr_comparison.py` - Compare OCR engines across multiple documents
- `ocr_comparison_*.html` - Single document OCR comparison (auto-generated)
- `ocr_dashboard.html` - Batch OCR comparison dashboard (auto-generated)

**Batch Processing & Dashboard:**
- `batch_benchmark.py` - Process multiple documents automatically
- `generate_dashboard.py` - Generate interactive HTML dashboard
- `dashboard.html` - Visual results explorer (auto-generated)

**Configuration:**
- `requirements.txt` - Python dependencies
- `setup.sh` - Automated setup script
- `MODELS.md` - Full model list and licenses
- `README.md` - This file
