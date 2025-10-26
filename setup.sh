#!/bin/bash

echo "================================================"
echo "  Verisist LLM Testing - Setup Script"
echo "================================================"
echo ""

# Check Ollama
echo "1️⃣  Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "   ❌ Ollama not found"
    echo "   📦 Install with: brew install ollama"
    exit 1
fi

if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ⚠️  Ollama is not running"
    echo "   🚀 Ollama should start automatically in background"
    echo "   If not, check: launchctl list | grep ollama"
else
    echo "   ✅ Ollama is running"
fi

# Check models
echo ""
echo "2️⃣  Checking Ollama models..."

# Check available models
AVAILABLE_MODELS=$(curl -sf http://localhost:11434/api/tags 2>/dev/null || echo "")

# Recommended models
RECOMMENDED_MODELS=("qwen2.5:3b" "qwen2.5:7b" "mistral:7b" "meditron:7b" "adrienbrault/biomistral-7b:Q6_K" "m/biomistral")

echo "   Recommended models for benchmarking:"
for model in "${RECOMMENDED_MODELS[@]}"; do
    if echo "$AVAILABLE_MODELS" | grep -q "$model"; then
        echo "      ✅ $model (installed)"
    else
        echo "      ⚠️  $model (not installed - run: ollama pull $model)"
    fi
done

# Check poppler
echo ""
echo "3️⃣  Checking poppler (PDF support)..."
if ! command -v pdftoppm &> /dev/null; then
    echo "   ❌ Poppler not found"
    echo "   📦 Install with: brew install poppler"
    exit 1
fi
echo "   ✅ Poppler is installed"

# Check Tesseract
echo ""
echo "4️⃣  Checking Tesseract OCR..."
if ! command -v tesseract &> /dev/null; then
    echo "   ⚠️  Tesseract not found"
    echo "   📦 Install with: brew install tesseract"
    echo "   ℹ️  Optional but recommended for OCR benchmarks"
else
    echo "   ✅ Tesseract is installed"
fi

# Setup Python venv
echo ""
echo "5️⃣  Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ℹ️  Virtual environment already exists"
fi

# Install dependencies
echo ""
echo "6️⃣  Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip

# Install base dependencies
echo "   📦 Installing base dependencies..."
pip install -q -r requirements.txt

# Optional: Install DeepSeek-OCR support
echo ""
echo "   ⚠️  DeepSeek-OCR Support (Optional):"
echo "      DeepSeek-OCR requires:"
echo "      - GPU with ≥16GB VRAM (may not work on MacBook Air M4)"
echo "      - PyTorch with CUDA or MPS support"
echo "      - Flash Attention (requires compilation)"
echo ""
read -p "   Install DeepSeek-OCR support? (y/N): " install_deepseek

if [[ $install_deepseek =~ ^[Yy]$ ]]; then
    echo "   📦 Installing PyTorch for Apple Silicon (MPS)..."
    pip install -q torch==2.6.0 torchvision==0.21.0

    echo "   📦 Installing Transformers and utilities..."
    pip install -q transformers==4.46.3 tokenizers==0.20.3 einops addict easydict

    echo "   ⚠️  Flash Attention (requires compilation, may take 5-10 minutes)..."
    read -p "   Install Flash Attention? (y/N): " install_flash
    if [[ $install_flash =~ ^[Yy]$ ]]; then
        pip install flash-attn==2.7.3 --no-build-isolation
        if [ $? -eq 0 ]; then
            echo "   ✅ Flash Attention installed"
        else
            echo "   ⚠️  Flash Attention installation failed (will fall back to eager mode)"
        fi
    else
        echo "   ℹ️  Skipping Flash Attention (will use eager mode)"
    fi

    echo "   ✅ DeepSeek-OCR support installed"
else
    echo "   ℹ️  Skipping DeepSeek-OCR installation"
fi

echo ""
echo "================================================"
echo "✅ Setup complete!"
echo "================================================"
echo ""
echo "USAGE:"
echo ""
echo "1. Single model test:"
echo "   source venv/bin/activate"
echo "   python test_ollama.py /path/to/document.pdf"
echo ""
echo "2. Compare 3B vs 7B models:"
echo "   python benchmark_models.py /path/to/document.pdf"
echo "   python evaluate_results.py benchmark_results_*.json"
echo ""
echo "3. Comprehensive benchmark (all OCR × LLM combinations):"
echo "   python comprehensive_benchmark.py /path/to/document.pdf"
echo "   python evaluate_comprehensive.py comprehensive_results_*.json"
echo ""
echo "See MODELS.md for full list of available models and licenses."
echo ""
