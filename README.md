# Template-Based Medical Document Extraction

Production-ready system for extracting structured data from medical documents using PaddleOCR + LLM + Templates.

**Performance:** 100% completeness on CBC lab reports with both 7B models.

## Quick Start

```bash
# 1. Run setup (installs dependencies + pulls models)
./setup.sh

# 2. Test single document
source venv/bin/activate
python benchmark.py test.pdf

# 3. Batch process multiple documents
python benchmark.py ~/Desktop/test-docs

# 4. View results
open results/results_*.html
```

## System Architecture

```
PDF Document
    ↓
[PaddleOCR] - Table-aware text extraction (~30s)
    ↓
[Template Manager] - Auto-detect test type
    ↓
[LLM Extraction] - Two-stage extraction (~160s per model)
    ↓
[Template Mapping] - Map to JSON structure + validation
    ↓
Structured JSON (100% complete)
```

## Configuration

- **OCR Engine:** PaddleOCR (CPU-based, no GPU needed)
- **LLM Models:** Qwen 2.5 7B, Mistral 7B (via Ollama)
- **Templates:** 3 medical test types
- **Modes:** 2 per model (extraction-only, validation+extraction)
- **Total:** 4 combinations per document

## Supported Document Types

### 1. Hematology CBC (Complete Blood Count)
- **Parameters:** 20 (Hemoglobin, PCV, RBC, WBC, Platelets, etc.)
- **Features:** Gender/age-specific reference ranges
- **Template:** `templates/hematology_cbc.json`

### 2. Serology Dengue Profile
- **Parameters:** 3 (NS1 Antigen, IgG, IgM)
- **Features:** Clinical interpretation patterns
- **Template:** `templates/serology_dengue.json`

### 3. Biochemistry Lipid Profile
- **Parameters:** 9 (Total Cholesterol, HDL, LDL, Triglycerides, etc.)
- **Features:** Cardiovascular risk stratification
- **Template:** `templates/biochemistry_lipid.json`

## Performance

**Per Document (3 pages):**
- OCR (PaddleOCR): ~30s
- LLM Extraction: ~160-170s per model
- **Total per model:** ~190-200s
- **Completeness:** 100%
- **Abnormal detection:** Automatic HIGH/LOW/NORMAL status

**Batch (10 documents):**
- Total time: ~30-35 minutes
- Results: Individual JSON + HTML per document
- Dashboard: Consolidated batch summary

## Usage

### Single Document Test

```bash
python benchmark.py path/to/document.pdf
```

**Output:**
```
results/
├── results_FILENAME_TIMESTAMP.json  # Raw results
└── results_FILENAME_TIMESTAMP.html  # Interactive dashboard
```

**Dashboard includes:**
- Model performance comparison
- Completeness scores
- Abnormal findings
- Extraction timing
- Parameter-by-parameter view

### Batch Processing

```bash
python benchmark.py ~/Desktop/test-docs
```

**Output:**
```
batch_results_TIMESTAMP/
├── results_document1_TIMESTAMP.json
├── results_document2_TIMESTAMP.json
├── ...
└── batch_summary.json  # Consolidated summary
```

## Example Output

### JSON Structure
```json
{
  "documentMetadata": {
    "patientName": "Mr. John Doe",
    "age": "45 Y 1 M 23 D",
    "gender": "M",
    "collectionDate": "2024-10-17"
  },
  "testResults": {
    "templateId": "HEMATOLOGY_CBC_v1.0",
    "sections": [{
      "sectionId": "CBC_PRIMARY",
      "parameters": [{
        "parameterId": "HEMOGLOBIN",
        "value": 13.5,
        "unit": "g/dL",
        "referenceRange": {"min": 13.0, "max": 17.0},
        "status": "NORMAL",
        "flags": []
      }, {
        "parameterId": "WBC_COUNT",
        "value": 3680,
        "unit": "cells/cu.mm",
        "referenceRange": {"min": 4000, "max": 10000},
        "status": "LOW",
        "flags": ["LOW"]
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

## Files

### Core Scripts (3 files)
- **benchmark.py** - Unified entry point (single file or batch directory)
- **template_extractor_v2.py** - Two-stage extraction engine
- **template_manager.py** - Template utilities

### Templates (3 JSON files)
- **templates/hematology_cbc.json** - CBC template
- **templates/serology_dengue.json** - Dengue template
- **templates/biochemistry_lipid.json** - Lipid template

### Configuration
- **setup.sh** - Automated setup script
- **requirements.txt** - Python dependencies
- **README.md** - This file
- **MODELS.md** - Detailed model information

## Key Features

### PaddleOCR Integration
- Deep learning OCR with table layout preservation
- Keeps parameter-value pairs adjacent (critical for extraction)
- CPU-based, no GPU required
- ~30s for 3-page document

### Template System
- JSON schemas for each test type
- Parameter aliases (e.g., "HAEMOGLOBIN" = "Hemoglobin" = "HB")
- Gender/age-specific reference ranges
- Automatic status calculation (HIGH/LOW/NORMAL)
- Abnormal finding detection

### Two-Stage Extraction
- **Stage 1:** LLM free-form extraction (no constraints)
- **Stage 2:** Python mapping to template structure
- Achieves 100% completeness vs 40-70% single-stage

## Requirements

**System:**
- macOS (tested on MacBook Air M4)
- Ollama for LLM inference
- Poppler for PDF rendering

**Python:**
- Python 3.13+
- PaddlePaddle, PaddleOCR
- pdf2image, Pillow, requests

**LLM Models (via Ollama):**
- Qwen 2.5 7B (4.7GB)
- Mistral 7B (4.1GB)

**Installation:**
```bash
# System dependencies
brew install ollama poppler

# LLM models
ollama pull qwen2.5:7b
ollama pull mistral:7b

# Python dependencies
./setup.sh
```

## Processing Modes

### Mode 1: Extraction-Only
- Direct parameter extraction
- Faster processing
- Use when: Speed priority, standard documents

### Mode 2: Validation + Extraction
- Two-stage with validation
- Stricter template adherence
- Use when: Maximum accuracy required

## Why PaddleOCR?

**Tesseract (Old):**
- Read table columns separately
- Parameter and value 40+ lines apart
- LLM couldn't match them
- Result: 40-70% completeness

**PaddleOCR (Current):**
- Preserves table layout
- Parameter and value adjacent
- LLM can match correctly
- Result: 100% completeness

**Tradeoff:**
- PaddleOCR: 2x slower (~30s vs ~15s)
- But total time: ~190s vs ~175s (8% difference)
- Accuracy: 100% vs 40-70% (critical improvement)

## Performance Benchmarks

| Metric | Tesseract | PaddleOCR |
|--------|-----------|-----------|
| **Qwen 7B Completeness** | 40% | **100%** |
| **Mistral 7B Completeness** | 70% | **100%** |
| **OCR Time** | ~15s | ~30s |
| **Layout Preservation** | Poor | Excellent |

## License

All components use Apache 2.0 license - fully permissive for commercial use.

- PaddleOCR: Apache 2.0
- Qwen 2.5: Apache 2.0
- Mistral 7B: Apache 2.0

## Next Steps

1. **Add more templates** - Create templates for other test types
2. **Production API** - Wrap in REST API for Verisist platform
3. **GPU optimization** - Optional GPU support for faster OCR
4. **Template editor** - UI for creating/editing templates

## Troubleshooting

**Ollama not running:**
```bash
# Check status
curl http://localhost:11434/api/tags

# Start Ollama
open -a Ollama
```

**Models not found:**
```bash
# List installed models
ollama list

# Pull missing models
ollama pull qwen2.5:7b
ollama pull mistral:7b
```

**PaddleOCR errors:**
```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade paddlepaddle paddleocr
```

For detailed model information and benchmarks, see [MODELS.md](MODELS.md).
