"""
Unified Document Processor

Routes documents to the appropriate extractor based on document type:
- Lab Reports → template_extractor_v2.py (Parameter-Based)
- Clinical/Financial Documents → document_extractor.py (Document-Based)
"""

import time
from typing import Dict, List, Optional
from pathlib import Path

from template_manager import TemplateManager
from template_extractor_v2 import TemplateExtractorV2
from document_extractor import DocumentExtractor
from document_types import DocumentType, DocumentCategory, get_document_category


class UnifiedDocumentProcessor:
    """
    Unified processor that identifies document types and routes to appropriate extractor.
    """

    def __init__(self):
        self.template_manager = TemplateManager()
        self.lab_extractor = TemplateExtractorV2(self.template_manager)
        self.doc_extractor = DocumentExtractor(self.template_manager)

    def process_document(
        self,
        ocr_text: str,
        model_name: str = "qwen2.5:7b",
        threshold: int = 10
    ) -> Dict:
        """
        Process a document: identify type(s) and extract data.

        Args:
            ocr_text: OCR extracted text from document
            model_name: Ollama model to use for extraction
            threshold: Minimum score for document type identification

        Returns:
            Dictionary with identified documents and extraction results
        """
        start_time = time.time()

        # Step 1: Identify all document types present
        identified_docs = self.template_manager.identify_all_test_types(ocr_text, threshold)

        if not identified_docs:
            return {
                "success": False,
                "error": "Could not identify document type",
                "identifiedTypes": [],
                "timings": {"total": time.time() - start_time}
            }

        # Step 2: Extract data for each identified document
        results = []

        for doc_info in identified_docs:
            doc_type = doc_info["test_type"]
            template = doc_info["template"]
            display_name = doc_info["display_name"]

            print(f"\n{'='*80}")
            print(f"Processing: {display_name}")
            print(f"Type: {doc_type}")
            print(f"Confidence Score: {doc_info['score']}")
            print(f"{'='*80}\n")

            # Route to appropriate extractor
            extraction_type = template.get("extractionType", "PARAMETER_BASED")

            if extraction_type == "PARAMETER_BASED":
                # Lab reports - use TemplateExtractorV2
                print(f"  → Using TemplateExtractorV2 (Parameter-Based Extraction)")
                extract_result = self.lab_extractor.extract_with_llm(
                    model_name=model_name,
                    ocr_text=ocr_text,
                    template=template
                )
            else:
                # Clinical/Financial documents - use DocumentExtractor
                print(f"  → Using DocumentExtractor (Document-Based Extraction)")
                extract_result = self.doc_extractor.extract_with_llm(
                    model_name=model_name,
                    ocr_text=ocr_text,
                    template=template
                )

            # Add metadata to result
            extract_result["documentType"] = doc_type
            extract_result["displayName"] = display_name
            extract_result["extractionType"] = extraction_type
            extract_result["identificationScore"] = doc_info["score"]

            results.append(extract_result)

            # Print result summary
            if extract_result.get("success"):
                completeness = extract_result.get("completeness", {})
                if isinstance(completeness, dict):
                    score = completeness.get("completenessScore", 0)
                    extracted = completeness.get("extractedFields") or completeness.get("extractedParameters", 0)
                    total = completeness.get("totalRequiredFields") or completeness.get("totalParameters", 0)
                    print(f"  ✅ Extraction successful: {score:.1f}% ({extracted}/{total})")
                else:
                    print(f"  ✅ Extraction successful: {completeness:.1f}%")
            else:
                error = extract_result.get("error", "Unknown error")
                print(f"  ❌ Extraction failed: {error}")

        total_time = time.time() - start_time

        return {
            "success": True,
            "identifiedTypes": [
                {
                    "type": doc["test_type"],
                    "displayName": doc["display_name"],
                    "score": doc["score"]
                }
                for doc in identified_docs
            ],
            "extractionResults": results,
            "timings": {
                "total": total_time
            }
        }

    def get_supported_document_types(self) -> List[Dict]:
        """Get list of all supported document types"""
        templates = self.template_manager.list_templates()

        supported = []
        for template in templates:
            doc_type = template.get("testType")
            display_name = template.get("displayName")
            category = template.get("category", "UNKNOWN")
            extraction_type = template.get("extractionType", "PARAMETER_BASED")

            supported.append({
                "documentType": doc_type,
                "displayName": display_name,
                "category": category,
                "extractionType": extraction_type,
                "implemented": True
            })

        return supported


def main():
    """Example usage"""
    processor = UnifiedDocumentProcessor()

    print("=" * 80)
    print("UNIFIED DOCUMENT PROCESSOR")
    print("=" * 80)
    print("\nSupported Document Types:\n")

    supported = processor.get_supported_document_types()

    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for doc in supported:
        by_category[doc["category"]].append(doc)

    for category in sorted(by_category.keys()):
        docs = by_category[category]
        print(f"{category} ({len(docs)} types):")
        for doc in docs:
            icon = "📊" if doc["extractionType"] == "PARAMETER_BASED" else "📄"
            print(f"  {icon} {doc['displayName']}")
        print()

    print("=" * 80)
    print("📊 = Parameter-Based (Lab Reports)")
    print("📄 = Document-Based (Clinical/Financial)")
    print("=" * 80)


if __name__ == "__main__":
    main()
