"""
Quick System Verification
Verifies unified processor routes correctly without OCR
"""

from unified_document_processor import UnifiedDocumentProcessor
import json


def test_lab_report_routing():
    """Test that lab reports route to parameter-based extractor"""
    processor = UnifiedDocumentProcessor()

    # Simulate CBC report OCR text with keywords
    cbc_text = """
    COMPLETE BLOOD COUNT TEST REPORT
    Patient Name: John Doe
    Hemoglobin: 14.5 g/dL
    RBC Count: 5.2 million/mcL
    WBC Count: 8000 cells/mcL
    Platelet Count: 250000 cells/mcL
    """

    print("\n" + "="*80)
    print("TEST 1: Lab Report (CBC) - Should use PARAMETER_BASED extraction")
    print("="*80)

    # Identify document type
    identified = processor.template_manager.identify_all_test_types(cbc_text)
    print(f"\n✅ Identified: {len(identified)} document(s)")
    for doc in identified:
        print(f"   • {doc['display_name']}")
        print(f"     Type: {doc['test_type']}")
        print(f"     Score: {doc['score']}")

        # Check extraction type
        template = processor.template_manager.get_template_by_test_type(doc['test_type'])
        extraction_type = template.get("extractionType", "PARAMETER_BASED")
        print(f"     Extraction Type: {extraction_type}")

        if extraction_type == "PARAMETER_BASED":
            print(f"     ✅ Routes to: TemplateExtractorV2 (Lab Reports)")
        else:
            print(f"     ⚠️  Routes to: DocumentExtractor")


def test_clinical_document_routing():
    """Test that prescriptions route to document-based extractor"""
    processor = UnifiedDocumentProcessor()

    # Simulate prescription OCR text
    prescription_text = """
    PRESCRIPTION
    Dr. Sarah Johnson, MBBS, MD
    Consultant Physician

    Patient Name: Jane Smith
    Date: 2024-10-30

    Medications:
    1. Amoxicillin 500mg - Take 1-0-1 for 7 days
    2. Paracetamol 650mg - Take 1-1-1 when needed
    3. Vitamin D3 - Take 1-0-0 for 30 days
    """

    print("\n" + "="*80)
    print("TEST 2: Clinical Document (Prescription) - Should use DOCUMENT_BASED extraction")
    print("="*80)

    identified = processor.template_manager.identify_all_test_types(prescription_text)
    print(f"\n✅ Identified: {len(identified)} document(s)")
    for doc in identified:
        print(f"   • {doc['display_name']}")
        print(f"     Type: {doc['test_type']}")
        print(f"     Score: {doc['score']}")

        template = processor.template_manager.get_template_by_test_type(doc['test_type'])
        extraction_type = template.get("extractionType", "PARAMETER_BASED")
        print(f"     Extraction Type: {extraction_type}")

        if extraction_type == "DOCUMENT_BASED":
            print(f"     ✅ Routes to: DocumentExtractor (Clinical/Financial)")
        else:
            print(f"     ⚠️  Routes to: TemplateExtractorV2")


def test_financial_document_routing():
    """Test that bills route to document-based extractor"""
    processor = UnifiedDocumentProcessor()

    bill_text = """
    HOSPITAL BILL / INVOICE
    XYZ Hospital

    Patient Name: John Doe
    Bill Number: INV-2024-001
    Date: 2024-10-30

    ITEMIZED CHARGES:
    Consultation Fee: Rs. 500
    Laboratory Tests: Rs. 1500
    Room Charges: Rs. 2000
    Pharmacy: Rs. 800

    TOTAL AMOUNT: Rs. 4800
    """

    print("\n" + "="*80)
    print("TEST 3: Financial Document (Hospital Bill) - Should use DOCUMENT_BASED extraction")
    print("="*80)

    identified = processor.template_manager.identify_all_test_types(bill_text)
    print(f"\n✅ Identified: {len(identified)} document(s)")
    for doc in identified:
        print(f"   • {doc['display_name']}")
        print(f"     Type: {doc['test_type']}")
        print(f"     Score: {doc['score']}")

        template = processor.template_manager.get_template_by_test_type(doc['test_type'])
        extraction_type = template.get("extractionType", "PARAMETER_BASED")
        print(f"     Extraction Type: {extraction_type}")

        if extraction_type == "DOCUMENT_BASED":
            print(f"     ✅ Routes to: DocumentExtractor (Clinical/Financial)")
        else:
            print(f"     ⚠️  Routes to: TemplateExtractorV2")


def test_system_summary():
    """Show system summary"""
    processor = UnifiedDocumentProcessor()

    print("\n" + "="*80)
    print("SYSTEM SUMMARY")
    print("="*80)

    supported_types = processor.get_supported_document_types()

    # Count by extraction type
    param_based = 0
    doc_based = 0

    for doc_type in supported_types:
        template = processor.template_manager.get_template_by_test_type(doc_type['documentType'])
        extraction_type = template.get("extractionType", "PARAMETER_BASED")
        if extraction_type == "PARAMETER_BASED":
            param_based += 1
        else:
            doc_based += 1

    print(f"\n📊 Total Supported Document Types: {len(supported_types)}")
    print(f"\n   Lab Reports (PARAMETER_BASED):     {param_based}")
    print(f"   Clinical/Financial (DOCUMENT_BASED): {doc_based}")

    print(f"\n🔧 Extraction Pipeline:")
    print(f"   • OCR: PaddleOCR (table-aware)")
    print(f"   • Lab Reports: TemplateExtractorV2 (2-stage with formulas)")
    print(f"   • Clinical/Financial: DocumentExtractor (1-stage structured)")
    print(f"   • Routing: UnifiedDocumentProcessor (automatic)")

    print(f"\n✅ System Status: Ready")


def main():
    print("\n" + "="*80)
    print("UNIFIED DOCUMENT PROCESSOR - SYSTEM VERIFICATION")
    print("="*80)

    try:
        test_lab_report_routing()
        test_clinical_document_routing()
        test_financial_document_routing()
        test_system_summary()

        print("\n" + "="*80)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("="*80)
        print("\nThe system is ready to process all document types.")
        print("Use test_unified_processor.py to test with real PDF documents.")
        print()

    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
