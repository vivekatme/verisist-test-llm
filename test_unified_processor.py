"""
Test Unified Document Processor
Tests both lab reports and clinical/financial documents
"""

import sys
import json
from pathlib import Path
from unified_document_processor import UnifiedDocumentProcessor
from paddleocr import PaddleOCR


def perform_ocr(pdf_path: str) -> str:
    """Extract text from PDF using PaddleOCR"""
    print(f"\n📄 Performing OCR on: {Path(pdf_path).name}")

    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    result = ocr.ocr(pdf_path, cls=True)

    # Extract text preserving structure
    extracted_lines = []
    for page_idx, page_result in enumerate(result):
        if page_result:
            for line in page_result:
                text = line[1][0]
                extracted_lines.append(text)

    ocr_text = "\n".join(extracted_lines)
    print(f"   ✅ OCR Complete: {len(ocr_text)} characters extracted")
    return ocr_text


def test_document(processor, file_path: str, model_name: str = "qwen2.5:7b"):
    """Test a single document"""
    print(f"\n{'='*100}")
    print(f"Testing: {Path(file_path).name}")
    print(f"{'='*100}")

    # Perform OCR
    ocr_text = perform_ocr(file_path)

    # Process with unified processor
    print(f"\n🔍 Processing document...")
    result = processor.process_document(ocr_text, model_name)

    # Display results
    print(f"\n{'='*100}")
    print("RESULTS")
    print(f"{'='*100}\n")

    if not result.get("success"):
        print(f"❌ Processing failed: {result.get('error')}")
        return

    # Show identified document types
    identified = result.get("identifiedTypes", [])
    print(f"✅ Identified {len(identified)} document type(s):\n")
    for doc_info in identified:
        print(f"   • {doc_info['displayName']}")
        print(f"     Type: {doc_info['type']}")
        print(f"     Confidence: {doc_info['score']}")
        print()

    # Show extraction results
    extraction_results = result.get("extractionResults", [])
    print(f"\n{'='*100}")
    print("EXTRACTION RESULTS")
    print(f"{'='*100}\n")

    for idx, extract_result in enumerate(extraction_results, 1):
        doc_name = extract_result.get("displayName", "Unknown")
        doc_type = extract_result.get("documentType", "Unknown")
        extraction_type = extract_result.get("extractionType", "Unknown")

        print(f"{idx}. {doc_name}")
        print(f"   Document Type: {doc_type}")
        print(f"   Extraction Type: {extraction_type}")

        if extract_result.get("success"):
            completeness = extract_result.get("completeness", {})
            if isinstance(completeness, dict):
                score = completeness.get("completenessScore", 0)
                extracted = completeness.get("extractedFields") or completeness.get("extractedParameters", 0)
                total = completeness.get("totalRequiredFields") or completeness.get("totalParameters", 0)
                print(f"   ✅ Completeness: {score:.1f}% ({extracted}/{total})")
            else:
                print(f"   ✅ Completeness: {completeness:.1f}%")

            # Show extracted data summary
            data = extract_result.get("data", {})
            if extraction_type == "PARAMETER_BASED":
                # Lab report - show parameters
                sections = data.get("sections", {})
                total_params = sum(len(params) for params in sections.values())
                print(f"   📊 Extracted {total_params} parameters across {len(sections)} sections")
            else:
                # Clinical/Financial - show sections
                extracted_data = data.get("extractedData", {})
                print(f"   📄 Extracted {len(extracted_data)} sections")
                for section_id, section_data in extracted_data.items():
                    if isinstance(section_data, list):
                        print(f"      • {section_id}: {len(section_data)} items")
                    elif isinstance(section_data, dict):
                        print(f"      • {section_id}: {len(section_data)} fields")
        else:
            error = extract_result.get("error", "Unknown error")
            print(f"   ❌ Extraction failed: {error}")

        print()

    # Show timings
    timings = result.get("timings", {})
    print(f"⏱️  Total Processing Time: {timings.get('total', 0):.2f}s\n")

    # Save full result to JSON
    output_dir = Path("/Users/VivekGupta/projects/verisist/verisist-test-llm/test-results")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"{Path(file_path).stem}_unified_result.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"💾 Full results saved to: {output_file}")


def test_all_documents(directory: str, model_name: str = "qwen2.5:7b"):
    """Test all documents in directory"""
    processor = UnifiedDocumentProcessor()

    print("\n" + "="*100)
    print("UNIFIED DOCUMENT PROCESSOR - BATCH TEST")
    print("="*100)
    print(f"\nSupported Document Types: {len(processor.get_supported_document_types())}")
    print(f"Model: {model_name}")
    print()

    # Find all PDF files
    pdf_files = list(Path(directory).glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in {directory}")
        return

    print(f"Found {len(pdf_files)} document(s) to process\n")

    # Process each document
    for pdf_file in pdf_files:
        try:
            test_document(processor, str(pdf_file), model_name)
        except Exception as e:
            print(f"\n❌ Error processing {pdf_file.name}: {str(e)}")
            continue

    print("\n" + "="*100)
    print("BATCH TEST COMPLETE")
    print("="*100)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_unified_processor.py <pdf_file_or_directory> [model_name]")
        print("\nExamples:")
        print("  python test_unified_processor.py test-docs/")
        print("  python test_unified_processor.py prescription.pdf")
        print("  python test_unified_processor.py hospital_bill.pdf mistral:7b")
        sys.exit(1)

    path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5:7b"

    if Path(path).is_dir():
        test_all_documents(path, model_name)
    elif Path(path).is_file():
        processor = UnifiedDocumentProcessor()
        test_document(processor, path, model_name)
    else:
        print(f"❌ Path not found: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
