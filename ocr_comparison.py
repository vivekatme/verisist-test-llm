#!/usr/bin/env python3
"""
OCR-only comparison script - Compare OCR engines without LLM processing.
Generates HTML visualization of OCR outputs for manual quality assessment.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

# PDF support
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PDF support not available. Install with: pip3 install pdf2image Pillow")

# OCR engines
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️  Tesseract not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠️  EasyOCR not available")


def extract_text_tesseract(file_bytes: bytes) -> tuple[str, float, dict]:
    """Extract text using Tesseract OCR"""
    start_time = time.time()

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            text = pytesseract.image_to_string(img)
            extracted_texts.append(f"=== Page {i} ===\n{text}")
        full_text = "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        full_text = pytesseract.image_to_string(img)

    time_taken = time.time() - start_time

    metadata = {
        "engine": "Tesseract",
        "version": pytesseract.get_tesseract_version().public,
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "line_count": len(full_text.splitlines())
    }

    return full_text, time_taken, metadata


def extract_text_easyocr(file_bytes: bytes) -> tuple[str, float, dict]:
    """Extract text using EasyOCR"""
    start_time = time.time()

    reader = easyocr.Reader(['en'], gpu=False, verbose=False)

    is_pdf = file_bytes.startswith(b'%PDF')

    if is_pdf:
        images = convert_from_bytes(file_bytes, dpi=300)
        extracted_texts = []
        for i, img in enumerate(images, 1):
            import numpy as np
            img_array = np.array(img)
            result = reader.readtext(img_array)

            page_text = [item[1] for item in result]
            extracted_texts.append(f"=== Page {i} ===\n{' '.join(page_text)}")
        full_text = "\n\n".join(extracted_texts)
    else:
        img = Image.open(BytesIO(file_bytes))
        import numpy as np
        img_array = np.array(img)
        result = reader.readtext(img_array)

        text_lines = [item[1] for item in result]
        full_text = "\n".join(text_lines)

    time_taken = time.time() - start_time

    metadata = {
        "engine": "EasyOCR",
        "version": "1.7.1",
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "line_count": len(full_text.splitlines())
    }

    return full_text, time_taken, metadata


def run_ocr_comparison(file_path: str) -> dict:
    """Run all available OCR engines and compare results"""
    print(f"\n{'=' * 80}")
    print(f"OCR Comparison: {Path(file_path).name}")
    print('=' * 80)

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    results = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "ocr_results": []
    }

    # Test each available OCR engine
    if TESSERACT_AVAILABLE:
        print("\n🔍 Running Tesseract OCR...")
        try:
            text, time_taken, metadata = extract_text_tesseract(file_bytes)
            results["ocr_results"].append({
                "engine": "Tesseract",
                "text": text,
                "time": round(time_taken, 2),
                "metadata": metadata,
                "status": "success"
            })
            print(f"✅ Completed in {time_taken:.2f}s ({len(text)} characters)")
        except Exception as e:
            results["ocr_results"].append({
                "engine": "Tesseract",
                "text": None,
                "time": 0,
                "metadata": {},
                "status": "error",
                "error": str(e)
            })
            print(f"❌ Failed: {e}")

    if EASYOCR_AVAILABLE:
        print("\n🔍 Running EasyOCR...")
        try:
            text, time_taken, metadata = extract_text_easyocr(file_bytes)
            results["ocr_results"].append({
                "engine": "EasyOCR",
                "text": text,
                "time": round(time_taken, 2),
                "metadata": metadata,
                "status": "success"
            })
            print(f"✅ Completed in {time_taken:.2f}s ({len(text)} characters)")
        except Exception as e:
            results["ocr_results"].append({
                "engine": "EasyOCR",
                "text": None,
                "time": 0,
                "metadata": {},
                "status": "error",
                "error": str(e)
            })
            print(f"❌ Failed: {e}")

    return results


def generate_html_comparison(results: dict, output_path: str):
    """Generate HTML visualization of OCR comparison"""

    file_name = Path(results["file"]).name

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Comparison - {file_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .stat-card h3 {{
            font-size: 0.875rem;
            color: #86868b;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}

        .stat-card .value {{
            font-size: 1.5rem;
            font-weight: 700;
        }}

        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }}

        .ocr-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .ocr-card h2 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.25rem;
        }}

        .ocr-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e5e5e7;
        }}

        .ocr-stat {{
            text-align: center;
        }}

        .ocr-stat .label {{
            font-size: 0.75rem;
            color: #86868b;
            text-transform: uppercase;
        }}

        .ocr-stat .value {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #1d1d1f;
        }}

        .ocr-text {{
            background: #f9f9fb;
            padding: 1rem;
            border-radius: 8px;
            max-height: 500px;
            overflow-y: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.875rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}

        .badge.success {{
            background: #d1f4e0;
            color: #0a6640;
        }}

        .badge.error {{
            background: #ffd3d3;
            color: #c41e3a;
        }}

        .badge.fast {{
            background: #d1f4e0;
            color: #0a6640;
        }}

        .badge.medium {{
            background: #fff4cc;
            color: #946c00;
        }}

        .badge.slow {{
            background: #ffd3d3;
            color: #c41e3a;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🔍 OCR Engine Comparison</h1>
            <p>{file_name}</p>
        </div>
    </div>

    <div class="container">
        <div class="stats">
"""

    # Add summary stats
    for result in results["ocr_results"]:
        if result["status"] == "success":
            time_class = "fast" if result["time"] < 5 else "medium" if result["time"] < 10 else "slow"
            html += f"""
            <div class="stat-card">
                <h3>{result["engine"]}</h3>
                <div class="value"><span class="badge {time_class}">{result["time"]}s</span></div>
                <p style="margin-top: 0.5rem; font-size: 0.875rem; color: #86868b;">
                    {result["metadata"]["character_count"]} chars, {result["metadata"]["word_count"]} words
                </p>
            </div>
"""

    html += """
        </div>

        <div class="comparison-grid">
"""

    # Add OCR results
    for result in results["ocr_results"]:
        status_badge = '<span class="badge success">Success</span>' if result["status"] == "success" else '<span class="badge error">Error</span>'

        html += f"""
            <div class="ocr-card">
                <h2>{result["engine"]}</h2>
                {status_badge}
"""

        if result["status"] == "success":
            html += f"""
                <div class="ocr-stats">
                    <div class="ocr-stat">
                        <div class="label">Time</div>
                        <div class="value">{result["time"]}s</div>
                    </div>
                    <div class="ocr-stat">
                        <div class="label">Chars</div>
                        <div class="value">{result["metadata"]["character_count"]}</div>
                    </div>
                    <div class="ocr-stat">
                        <div class="label">Words</div>
                        <div class="value">{result["metadata"]["word_count"]}</div>
                    </div>
                </div>
                <div class="ocr-text">{result["text"]}</div>
"""
        else:
            html += f"""
                <p style="color: #c41e3a; margin-top: 1rem;">Error: {result.get("error", "Unknown error")}</p>
"""

        html += """
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)


def main():
    if len(sys.argv) < 2:
        print("\nUSAGE:")
        print("  python3 ocr_comparison.py <pdf_or_image_path>")
        print("\nEXAMPLE:")
        print("  python3 ocr_comparison.py /path/to/document.pdf")
        print("\nNOTE:")
        print("  - Compares Tesseract and EasyOCR")
        print("  - Generates HTML visualization for side-by-side comparison")
        print("  - Install OCR engines: pip3 install pytesseract easyocr")
        return

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return

    if not PDF_SUPPORT:
        print("❌ PDF support not installed. Run: pip3 install pdf2image Pillow")
        return

    # Run comparison
    results = run_ocr_comparison(file_path)

    # Save JSON results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_output = f"ocr_comparison_{timestamp}.json"
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 JSON results saved to: {json_output}")

    # Generate HTML
    html_output = f"ocr_comparison_{timestamp}.html"
    generate_html_comparison(results, html_output)

    print(f"🌐 HTML comparison generated: {html_output}")
    print(f"\n📊 Open in browser:")
    print(f"   open {html_output}")
    print("=" * 80)


if __name__ == "__main__":
    main()
