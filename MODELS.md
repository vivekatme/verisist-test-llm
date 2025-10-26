# Models and Licenses for Benchmarking

## OSS LLM Models (Download Commands)

### General Purpose Models (Apache 2.0 License)
```bash
# Qwen 2.5 Series - Apache 2.0
ollama pull qwen2.5:3b      # 2.6GB - Fast
ollama pull qwen2.5:7b      # 4.7GB - Balanced

# Mistral AI Models - Apache 2.0
ollama pull mistral:7b      # 4.1GB - Efficient, strong performance
```

### Alternative Models
```bash
# Llama 3.2 - Llama 3 Community License (some restrictions)
ollama pull llama3.2:3b     # 2GB - Fast

# Gemma 2 - Gemma Terms of Use (generally permissive)
ollama pull gemma2:9b       # 5.4GB - Google model
```

## OCR Engines

### Supported OCR Engines (Apache 2.0 License)

#### Tesseract OCR
- Most mature, widely used
- Good accuracy on printed documents
- Fast, CPU-based (4-5 seconds/page)
- No GPU required
- 100+ languages supported
- **Best for:** Speed priority, printed documents

**Installation:**
```bash
# macOS
brew install tesseract
pip install pytesseract
```

#### EasyOCR
- Deep learning based
- Excellent accuracy on complex layouts
- Slower but more accurate (60-90 seconds/page)
- CPU-based (GPU optional but not required)
- 80+ languages supported
- **Best for:** Accuracy priority, complex layouts, handwriting

**Installation:**
```bash
pip install easyocr
```

---

### ❌ Removed OCR Engines

#### PaddleOCR - REMOVED
- **Reason:** Incompatible with Python 3.13
  - v3.3.0: Persistent segmentation faults on macOS
  - v2.7.3: Requires numpy < 2.0 (not compatible with Python 3.13)
  - Docker solution: Too much overhead for production
- **Alternative:** Use EasyOCR for complex layouts, Tesseract for speed

#### Surya OCR - REMOVED
- **Reason:** Persistent API instability
  - v0.17.0+ has breaking API changes
  - Initialization errors: `'function' object has no attribute 'config'`
  - Multiple breaking changes between versions
- **Alternative:** Use EasyOCR for multilingual support

#### DeepSeek-OCR - REMOVED
- **Reason:** Not practical for MacBook Air M4
  - Requires GPU with ≥16GB VRAM
  - Causes thermal throttling on Mac
- **Alternative:** Use EasyOCR or Tesseract

---

## Recommended Combinations

### Speed Priority
- **OCR:** Tesseract
- **LLM:** qwen2.5:3b
- **Expected:** ~25-35s/document on MacBook Air M4

### Accuracy Priority
- **OCR:** Tesseract (for LLM benchmark) or EasyOCR (for OCR comparison)
- **LLM:** Qwen 2.5 7B or Mistral 7B
- **Expected:** ~50-60s/document on MacBook Air M4

### Balanced
- **OCR:** Tesseract
- **LLM:** qwen2.5:7b
- **Expected:** ~50-60s/document on MacBook Air M4

---

## Benchmark Matrix

### LLM Benchmark (comprehensive_benchmark.py)
Uses **Tesseract OCR** as baseline × **3 LLM models** × **2 modes**:
- **Total combinations:** 6

**OCR Engine:**
- Tesseract OCR (fast baseline, ~4-5s/page)

**LLM Models:**
1. Qwen 2.5 3B (general-purpose)
2. Qwen 2.5 7B (general-purpose)
3. Mistral 7B (general-purpose)

### OCR Comparison (ocr_comparison.py)
Compares **2 OCR engines** side-by-side (no LLM):
1. Tesseract OCR (speed priority)
2. EasyOCR (accuracy priority)

---

## License Summary

| Component | License | Commercial Use | Restrictions |
|-----------|---------|----------------|--------------|
| **Tesseract** | **Apache 2.0** | ✅ **Yes** | **None** |
| **EasyOCR** | **Apache 2.0** | ✅ **Yes** | **None** |
| ~~PaddleOCR~~ | ~~Apache 2.0~~ | ❌ **Removed** | **Python 3.13 incompatible** |
| ~~Surya OCR~~ | ~~Apache 2.0~~ | ❌ **Removed** | **API unstable** |
| ~~DeepSeek-OCR~~ | ~~MIT~~ | ❌ **Removed** | **Requires GPU** |
| Qwen 2.5 | Apache 2.0 | ✅ Yes | None |
| Mistral 7B | Apache 2.0 | ✅ Yes | None |
| ~~Meditron~~ | ~~Apache 2.0~~ | ❌ **Removed** | **Outdated model** |
| ~~BioMistral Q6_K~~ | ~~Apache 2.0~~ | ❌ **Removed** | **Model corruption** |
| ~~BioMistral Q4~~ | ~~Apache 2.0~~ | ❌ **Removed** | **Model corruption** |
| Llama 3.2 | Llama 3 License | ⚠️ Yes* | *Restrictions if >700M users |
| Gemma 2 | Gemma ToU | ⚠️ Yes* | *Some model restrictions |

---

## Notes

### Two Benchmark Types

**1. LLM Benchmark** (`comprehensive_benchmark.py`)
- **Purpose:** Compare LLM model performance for medical document extraction
- **OCR:** Tesseract only (fast baseline, minimizes OCR variable)
- **Focus:** LLM accuracy, speed, and extraction quality
- **Combinations:** 6 (1 OCR × 3 LLMs × 2 modes)
- **Use when:** Testing different LLM models for production

**2. OCR Comparison** (`ocr_comparison.py`)
- **Purpose:** Compare OCR engine accuracy and speed
- **OCR:** Tesseract vs EasyOCR (no LLM processing)
- **Focus:** OCR text extraction quality
- **Combinations:** 2 OCR engines
- **Use when:** Evaluating OCR engine selection

### General Notes
- **2 OCR engines supported:** Tesseract (speed), EasyOCR (accuracy)
- **3 LLM models supported:** 3 general-purpose models
- All supported components are **Apache 2.0 licensed** - fully permissive for commercial use
- Removed engines (PaddleOCR, Surya OCR, DeepSeek-OCR) have compatibility or resource issues
- Removed models:
  - Meditron (outdated)
  - BioMistral Q6_K (model corruption - returns empty responses)
  - BioMistral Q4 (model corruption - returns empty responses)
- For best results:
  - **LLM benchmark:** Uses Tesseract for consistent baseline
  - **OCR comparison:** Compare Tesseract (fast) vs EasyOCR (accurate)
  - **Speed priority:** Use Qwen 2.5 3B
  - **Accuracy priority:** Use Qwen 2.5 7B or Mistral 7B
