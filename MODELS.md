# Models and Configuration for Template-Based Extraction

## Current Configuration

### LLM Model (Production-Ready)
```bash
# Qwen 2.5 7B - Apache 2.0
ollama pull qwen2.5:7b      # 4.7GB - 100% completeness, excellent instruction following
```

**Performance Results:**
- **Qwen 2.5 7B**: 100% completeness (20/20 CBC parameters)
- **Extraction Time**: ~85s per template
- **Total Time**: ~112s (27s OCR + 85s extraction)
- **Multi-Test**: ~130s for 2 tests (shared OCR)

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
| Mistral 7B | Unstable performance (85% → 30% regression with prompt changes), weaker instruction-following |
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

## System Architecture

### Multi-Template Extraction Pipeline

**Configuration:**
- **OCR Engine:** PaddleOCR (27s/document)
- **LLM Model:** Qwen 2.5 7B (85s per template)
- **Multi-Test Support:** Automatic detection and extraction of multiple tests per document
- **Timing Breakdown:** Detailed metrics for each stage

**Processing Stages:**
1. **OCR Extraction** (~27s): PaddleOCR extracts text from all pages
2. **Test Identification** (~0.05s): Keyword-based matching identifies ALL test types
3. **Template Extraction** (~85s per test): Two-stage extraction for each identified template
   - Stage 1: LLM free-form extraction (~84s)
   - Stage 2: Python template mapping (~1s)

**Performance:**
- **Single Test (CBC):** ~112s total (27s OCR + 0.05s ID + 85s extraction)
- **Multi-Test (CBC + Dengue):** ~130s total (shared OCR + 2 extractions)
- **Completeness:** 100% on all templates (CBC, Dengue, Lipid)
- **Accuracy:** Detects abnormal values, reference ranges, critical flags

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
| Mistral 7B | Apache 2.0 | - | Removed (unstable) |
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
| **Processing Time** | ~5s/page | ~27s/document | Acceptable tradeoff |

### Current System Performance (PaddleOCR + Qwen 2.5 7B)

| Document Type | Tests | Completeness | Timing Breakdown | Total Time |
|--------------|-------|--------------|------------------|------------|
| **Single Test (CBC)** | 1 | 100% (20/20) | OCR: 27s + ID: 0.05s + Extract: 85s | ~112s |
| **Multi-Test (CBC + Dengue)** | 2 | 100% (23/23) | OCR: 27s + ID: 0.05s + Extract: 98s (85s + 13s) | ~130s |

**Timing Breakdown per Test:**
- **OCR**: ~27s (shared across all tests)
- **Identification**: ~0.05s (shared, detects all tests)
- **Stage 1 (LLM)**: ~84s (CBC), ~12s (Dengue)
- **Stage 2 (Mapping)**: ~1s per test
- **Total**: 27s OCR + 0.05s ID + (85s × num_tests)

**Key Features:**
- ✅ Multi-template detection (automatically finds all tests in document)
- ✅ 100% completeness on all templates (CBC, Dengue, Lipid)
- ✅ Homogenized parameter IDs for trend analysis
- ✅ Detailed timing metrics for performance optimization
- ✅ Abnormal value detection with HIGH/LOW flags

**Production Ready:** Single model (Qwen 2.5 7B) provides consistent 100% completeness with excellent instruction-following.
