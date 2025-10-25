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

# Check model
echo ""
echo "2️⃣  Checking qwen2.5vl:7b model..."
if curl -sf http://localhost:11434/api/tags | grep -q "qwen2.5vl:7b"; then
    echo "   ✅ qwen2.5vl:7b is installed"
else
    echo "   ❌ Model not found"
    echo "   📦 Pull model with: ollama pull qwen2.5vl:7b"
    echo "   ⏱️  This will download ~6GB"
    exit 1
fi

# Check poppler
echo ""
echo "3️⃣  Checking poppler..."
if ! command -v pdftoppm &> /dev/null; then
    echo "   ❌ Poppler not found"
    echo "   📦 Install with: brew install poppler"
    exit 1
fi
echo "   ✅ Poppler is installed"

# Setup Python venv
echo ""
echo "4️⃣  Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ℹ️  Virtual environment already exists"
fi

# Install dependencies
echo ""
echo "5️⃣  Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed"

echo ""
echo "================================================"
echo "✅ Setup complete!"
echo "================================================"
echo ""
echo "To test with a PDF:"
echo "   source venv/bin/activate"
echo "   python test_ollama.py /path/to/document.pdf"
echo ""
