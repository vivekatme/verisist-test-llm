# Models and Configuration for Template-Based Extraction

## Current Configuration

### LLM Models (2 Best-Performing 7B Models)
```bash
# Qwen 2.5 7B - Apache 2.0
ollama pull qwen2.5:7b      # 4.7GB - Excellent accuracy, 100% completeness

# Mistral 7B - Apache 2.0
ollama pull mistral:7b      # 4.1GB - Excellent accuracy, 100% completeness
```

**Performance Results:**
- **Qwen 2.5 7B**: 100% completeness, ~160s extraction time
- **Mistral 7B**: 100% completeness, ~165s extraction time

### OCR Engine

#### PaddleOCR (Default and Recommended)
- Deep learning based OCR with excellent table layout preservation
- Handles medical report tables correctly (parameter-value pairing)
- CPU-based, no GPU required
- 80+ languages supported
- **Processing time:** ~30s for 3-page document at 300 DPI

**Why PaddleOCR:**
- Preserves table structure: parameters and values on adjacent lines
- Critical for medical reports where data is in tabular format
- Previous OCR engines (Tesseract) separated columns by 40+ lines, breaking extraction

**Installation:**
```bash
pip install paddlepaddle paddleocr pdf2image
```

**Python 3.13 Compatibility:**
- Created imghdr compatibility shim in `venv/lib/python3.13/site-packages/imghdr.py`
- Successfully tested and working

---

## Removed Components

### Removed Models
| Model | Reason |
|-------|--------|
| Qwen 2.5 3B | Only 10% completeness (insufficient for production) |
| Meditron 7B | Outdated model, removed per user request |
| BioMistral Q6_K | Model corruption - empty responses |
| BioMistral Q4 | Model corruption - empty responses |

### Removed OCR Engines
| Engine | Reason |
|--------|--------|
| Tesseract OCR | Poor table layout handling - reads columns separately (40+ line gap between parameters and values) |
| EasyOCR | Not tested, Tesseract already showed layout issues |

---

## Benchmark Matrix

### Template-Based Extraction Benchmark

**Configuration:**
- **OCR Engine:** PaddleOCR (30s/document)
- **LLM Models:** 2 (Qwen 2.5 7B, Mistral 7B)
- **Modes:** 2 (extraction-only, validation+extraction)
- **Total combinations:** 4 (2 models × 2 modes)

**Modes:**
1. **Extraction-only**: Direct parameter extraction from OCR text
2. **Validation+extraction**: Two-stage approach with validation and mapping

**Expected Performance:**
- **Total time per document:** ~190-200s (30s OCR + 160-170s LLM extraction)
- **Completeness:** 100% for both 7B models
- **Accuracy:** High (detects abnormal values, reference ranges)

---

## Template System

### Template Types
1. **Hematology CBC** (HEMATOLOGY_CBC_v1.0)
   - 20 parameters across 4 sections
   - Gender/age-specific reference ranges
   - Critical value detection

2. **Serology Dengue** (SEROLOGY_DENGUE_PROFILE_v1.0)
   - 3 parameters (NS1, IgG, IgM)
   - Clinical interpretation patterns

3. **Biochemistry Lipid** (BIOCHEMISTRY_LIPID_PROFILE_v1.0)
   - 9 parameters
   - Cardiovascular risk stratification

### Extraction Approach: Two-Stage V2
**Stage 1:** Free-form LLM extraction (no template constraints)
**Stage 2:** Python mapping to template structure

**Why two-stage:**
- LLMs struggle with strict JSON schema adherence in single shot
- Separating extraction from structure mapping improves completeness
- Achieves 100% vs 40-70% with single-stage approach

---

## License Summary

| Component | License | Commercial Use | Status |
|-----------|---------|----------------|--------|
| **PaddleOCR** | **Apache 2.0** | ✅ **Yes** | **Active** |
| **Qwen 2.5 7B** | **Apache 2.0** | ✅ **Yes** | **Active** |
| **Mistral 7B** | **Apache 2.0** | ✅ **Yes** | **Active** |
| Tesseract OCR | Apache 2.0 | - | Removed (poor layout) |
| Qwen 2.5 3B | Apache 2.0 | - | Removed (low accuracy) |

All active components are **Apache 2.0 licensed** - fully permissive for commercial use.

---

## Performance Benchmarks

### PaddleOCR vs Tesseract Comparison

| Metric | Tesseract | PaddleOCR | Improvement |
|--------|-----------|-----------|-------------|
| **Layout Preservation** | Poor (40+ line gaps) | Excellent (adjacent lines) | Critical fix |
| **Qwen 7B Completeness** | 40% | 100% | +60% |
| **Mistral 7B Completeness** | 70% | 100% | +30% |
| **Processing Time** | ~5s/page | ~30s/document | Acceptable tradeoff |

### Model Performance (with PaddleOCR)

| Model | Completeness | Extraction Time | Total Time | Abnormal Detection |
|-------|--------------|-----------------|------------|-------------------|
| Qwen 2.5 7B | 100% (20/20) | ~160s | ~190s | 6 abnormal findings |
| Mistral 7B | 100% (20/20) | ~165s | ~195s | 5 abnormal findings |

**Conclusion:** Both 7B models achieve perfect extraction with PaddleOCR. Choose based on preference or speed requirements.
