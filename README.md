# Verisist LLM Testing - Template-Based Medical Document Extraction

Test project for template-based extraction of medical documents using PaddleOCR + LLM models.

## Current System

**Architecture:** PaddleOCR (table-aware) + LLM (Qwen 7B / Mistral 7B) + Template Mapping

**Performance:** 100% completeness on CBC lab reports with both 7B models

## Quick Start

```bash
# 1. Install system dependencies
brew install ollama poppler

# 2. Pull LLM models (~9.5GB total)
ollama pull qwen2.5:7b    # 4.7GB - Primary model
ollama pull mistral:7b    # 4.1GB - Alternative model

# 3. Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install paddlepaddle paddleocr pdf2image Pillow requests

# 4. Run single document test
python multi_model_v2_benchmark.py test.pdf

# 5. Run batch processing
python batch_benchmark.py ~/Desktop/test-docs

# 6. View results
open results/multi_model_v2_*.html
```

## What It Does

### Template-Based Extraction

1. **OCR (PaddleOCR)**: Extracts text from PDF with proper table layout preservation
   - Time: ~30s for 3-page document
   - Critical: Keeps parameter names and values adjacent (not 40+ lines apart like Tesseract)

2. **Template Identification**: Auto-detects test type from OCR text
   - Supported: Hematology CBC, Dengue Profile, Lipid Profile

3. **Two-Stage LLM Extraction**:
   - **Stage 1**: Free-form parameter extraction (no template constraints)
   - **Stage 2**: Python mapping to template structure with validation
   - Time: ~160-170s per document
   - Result: 100% completeness

### Supported Document Types

1. **Hematology CBC** (Complete Blood Count)
   - 20 parameters across 4 sections
   - Gender/age-specific reference ranges
   - Abnormal value detection (HIGH/LOW/NORMAL)

2. **Serology Dengue Profile**
   - 3 parameters (NS1, IgG, IgM)
   - Clinical interpretation patterns

3. **Biochemistry Lipid Profile**
   - 9 parameters
   - Cardiovascular risk stratification

## Processing Modes

### Mode 1: Extraction-Only
- Direct parameter extraction
- Fastest processing
- Use when: Speed priority

### Mode 2: Validation + Extraction
- Two-stage approach with validation
- Mapping to strict template structure
- Use when: Maximum accuracy required

## Performance

**Per Document (3 pages):**
- OCR (PaddleOCR): ~30s
- LLM Extraction: ~160-170s
- **Total**: ~190-200s
- **Completeness**: 100%

**Batch Processing (10 documents):**
- Total time: ~30-35 minutes
- Parallel OCR + sequential LLM per document

## Usage

### Single Document

```bash
# Test with default models (both 7B models in 2 modes each = 4 runs)
python multi_model_v2_benchmark.py test.pdf

# Output:
# - results/multi_model_v2_TIMESTAMP.json
# - results/multi_model_v2_TIMESTAMP.html (interactive dashboard)
```

### Batch Processing

```bash
# Process all PDFs in a directory
python batch_benchmark.py ~/Desktop/test-docs

# Output:
# - batch_results_TIMESTAMP/results_DOCNAME_TIMESTAMP.json (per doc)
# - batch_results_TIMESTAMP/batch_summary.json
# - batch_results_TIMESTAMP/batch_dashboard.html
```

### View Results

```bash
# Open latest result dashboard
open results/multi_model_v2_*.html

# Open batch dashboard
open batch_results_*/batch_dashboard.html
```

## Key Features

### PaddleOCR Integration
- Deep learning OCR with table layout preservation
- Handles medical report tables correctly
- 2x slower than Tesseract but critical for accuracy
- Python 3.13 compatible (with imghdr shim)

### Template System
- JSON schemas for each test type
- Parameter aliases for matching variations
- Reference range lookup (gender/age-specific)
- Status calculation (HIGH/LOW/NORMAL)
- Abnormal finding detection

### Two-Stage Extraction
- Stage 1: LLM extracts all parameters freely
- Stage 2: Python maps to template structure
- Achieves 100% vs 40-70% with single-stage

## Models

### Active Models (2)
- **Qwen 2.5 7B**: 100% completeness, ~160s extraction
- **Mistral 7B**: 100% completeness, ~165s extraction

Both models achieve identical 100% completeness with PaddleOCR.

### Removed Models
- Qwen 2.5 3B: Only 10% completeness (insufficient)
- Meditron 7B: Outdated, removed per user request
- BioMistral variants: Model corruption issues

See [MODELS.md](MODELS.md) for detailed model information.

## Benchmark Results

**PaddleOCR vs Tesseract:**
| Metric | Tesseract | PaddleOCR |
|--------|-----------|-----------|
| Qwen 7B Completeness | 40% | **100%** (+60%) |
| Mistral 7B Completeness | 70% | **100%** (+30%) |
| Processing Time | ~15s | ~30s (+15s) |
| Layout Preservation | Poor | Excellent |

**Conclusion:** PaddleOCR's 15s overhead is negligible compared to 160s LLM time, and it's critical for 100% accuracy.

## Files

**Core Scripts:**
- `multi_model_v2_benchmark.py` - Single document benchmark (2 models × 2 modes)
- `batch_benchmark.py` - Batch processing for multiple documents
- `template_manager.py` - Template loading and management
- `template_extractor_v2.py` - Two-stage extraction logic

**Templates:**
- `templates/hematology_cbc.json` - CBC template (20 parameters)
- `templates/serology_dengue.json` - Dengue profile (3 parameters)
- `templates/biochemistry_lipid.json` - Lipid profile (9 parameters)

**Documentation:**
- `README.md` - This file
- `MODELS.md` - Model details and performance
- `TEMPLATE_SYSTEM_README.md` - Template architecture
- `QUICK_START_TEMPLATE.md` - Template creation guide

## Requirements

**System:**
- macOS (tested on MacBook Air M4)
- Ollama for LLM inference
- Poppler for PDF rendering

**Python:**
- Python 3.13 (with imghdr compatibility shim)
- PaddlePaddle & PaddleOCR
- pdf2image, Pillow, requests

**Models:**
- Qwen 2.5 7B (4.7GB)
- Mistral 7B (4.1GB)

## Output Examples

### JSON Result
```json
{
  "documentMetadata": {
    "patientName": "Mr.VIVEK GUPTA",
    "age": "45 Y 1 M 23 D",
    "gender": "M"
  },
  "testResults": {
    "sections": [{
      "parameters": [{
        "parameterId": "HEMOGLOBIN",
        "value": 13.5,
        "unit": "g/dL",
        "referenceRange": {"min": 13.0, "max": 17.0},
        "status": "NORMAL"
      }]
    }]
  },
  "completeness": {
    "completenessScore": 100.0,
    "extractedParameters": 20,
    "totalParameters": 20
  }
}
```

### HTML Dashboard
- Model performance comparison
- Completeness scores
- Abnormal findings detected
- Extraction timing breakdown
- Side-by-side parameter comparison

## Next Steps

1. **Add More Templates**: Create templates for other test types
2. **Optimize LLM Speed**: Explore quantized models or GPU acceleration
3. **Enhance Validation**: Add more sophisticated abnormal finding rules
4. **Production Integration**: API wrapper for Verisist platform

## License

All components use Apache 2.0 license - fully permissive for commercial use.
