# Models and Licenses for Benchmarking

## OSS LLM Models (Download Commands)

### General Purpose Models (Apache 2.0 License)
```bash
# Qwen 2.5 Series - Apache 2.0
ollama pull qwen2.5:3b      # 2.6GB - Fast
ollama pull qwen2.5:7b      # 4.7GB - Balanced
ollama pull qwen2.5:14b     # 9GB - Accurate
```

### Medical-Specialized Models (Apache 2.0 License)
```bash
# Meditron - Apache 2.0 (Llama-2 fine-tuned on medical literature)
ollama pull meditron:7b     # 4.1GB - Medical specialist

# BioMistral - Apache 2.0 (Mistral fine-tuned on PubMed)
ollama pull biomistral:7b   # 4.1GB - Medical specialist
```

### Alternative Models
```bash
# Llama 3.2 - Llama 3 Community License (some restrictions)
ollama pull llama3.2:3b     # 2GB - Fast

# Gemma 2 - Gemma Terms of Use (generally permissive)
ollama pull gemma2:9b       # 5.4GB - Google model
```

## OCR Engines

### Traditional OCR Engines

#### Tesseract OCR (Apache 2.0)
- Most mature, widely used
- Good accuracy on printed documents
- Fast, CPU-based
- No GPU required

#### PaddleOCR (Apache 2.0)
- State-of-the-art accuracy
- Better for complex layouts
- Supports 80+ languages
- Slightly slower than Tesseract
- Can use GPU (optional)

#### EasyOCR (Apache 2.0)
- Deep learning based
- Good for handwriting
- 80+ languages
- GPU-accelerated (optional)

### Vision-Language Models (VLM-based OCR)

#### DeepSeek-OCR (MIT License)
- **NEW!** 3B parameter vision-language model
- Context compression for efficient document processing
- Superior accuracy on complex layouts
- **Requires:** GPU with ≥16GB VRAM
- **Warning:** May not work well on MacBook Air M4 (thermal throttling, limited VRAM)
- **Installation:** Via Hugging Face Transformers (not Ollama)
- **Best for:** High-accuracy requirements with GPU infrastructure

## Recommended Combinations

### Speed Priority
- **OCR:** Tesseract
- **LLM:** qwen2.5:3b
- **Expected:** ~25-35s/document on MacBook Air M4

### Accuracy Priority
- **OCR:** PaddleOCR
- **LLM:** meditron:7b (medical specialist)
- **Expected:** ~65-75s/document on MacBook Air M4

### Balanced
- **OCR:** Tesseract
- **LLM:** qwen2.5:7b
- **Expected:** ~50-60s/document on MacBook Air M4

## License Summary

| Component | License | Commercial Use | Restrictions |
|-----------|---------|----------------|--------------|
| Tesseract | Apache 2.0 | ✅ Yes | None |
| PaddleOCR | Apache 2.0 | ✅ Yes | None |
| EasyOCR | Apache 2.0 | ✅ Yes | None |
| **DeepSeek-OCR** | **MIT** | ✅ **Yes** | **None** |
| Qwen 2.5 | Apache 2.0 | ✅ Yes | None |
| Meditron | Apache 2.0 | ✅ Yes | None |
| BioMistral | Apache 2.0 | ✅ Yes | None |
| Llama 3.2 | Llama 3 License | ⚠️ Yes* | *Restrictions if >700M users |
| Gemma 2 | Gemma ToU | ⚠️ Yes* | *Some model restrictions |

## Notes

- **DeepSeek-OCR** is a vision-language model (VLM) that performs OCR via image understanding, not traditional text detection
- All Apache 2.0 and MIT licensed components are **fully permissive** for commercial use
- Llama 3.2 and Gemma 2 have additional restrictions - review licenses before production use
- DeepSeek-OCR requires GPU with ≥16GB VRAM and may not be suitable for MacBook Air M4
