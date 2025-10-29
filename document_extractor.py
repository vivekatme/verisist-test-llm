"""
Document Extractor for Clinical and Financial Documents

Handles extraction for document-based templates (prescriptions, bills, certificates, etc.)
Uses LLM to extract structured sections with lists and nested objects.
"""

import json
import re
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import requests


class DocumentExtractor:
    """
    Extractor for document-based templates (clinical, financial, diagnostic documents).
    Uses single-stage LLM extraction with structured output.
    """

    def __init__(self, template_manager):
        self.template_manager = template_manager
        self.ollama_base_url = "http://localhost:11434"

    def extract_with_llm(
        self,
        model_name: str,
        ocr_text: str,
        template: Dict
    ) -> Dict:
        """
        Extract document data using LLM with document-based template.

        Args:
            model_name: Ollama model name (e.g., "qwen2.5:7b")
            ocr_text: OCR extracted text
            template: Document template (with extractionType: DOCUMENT_BASED)

        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()

        try:
            # Generate prompt for document extraction
            prompt = self._get_document_extraction_prompt(ocr_text, template)

            # Call LLM
            raw_output, llm_time, error = self._call_llm(model_name, prompt)

            if error:
                return {
                    "success": False,
                    "error": error,
                    "timings": {"extraction": time.time() - start_time}
                }

            # Parse LLM output
            parsed_data = self._parse_llm_output(raw_output, template)

            if not parsed_data:
                return {
                    "success": False,
                    "error": "Failed to parse LLM output",
                    "raw_output": raw_output,
                    "timings": {"extraction": time.time() - start_time}
                }

            # Build structured document
            structured_doc = self._build_structured_document(parsed_data, template)

            # Calculate completeness
            completeness = self._calculate_completeness(structured_doc, template)

            extraction_time = time.time() - start_time

            return {
                "success": True,
                "data": structured_doc,
                "completeness": completeness,
                "raw_output": raw_output,
                "timings": {
                    "llm": llm_time,
                    "extraction": extraction_time
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timings": {"extraction": time.time() - start_time}
            }

    def _get_document_extraction_prompt(self, ocr_text: str, template: Dict) -> str:
        """Generate extraction prompt for document-based template"""
        doc_name = template.get("displayName", "Medical Document")
        doc_type = template.get("documentType", "UNKNOWN")
        sections = template.get("sections", [])

        # Build section descriptions
        section_descriptions = []
        for section in sections:
            section_id = section.get("sectionId")
            section_name = section.get("sectionName")
            is_list = section.get("isList", False)

            if is_list:
                # List section (medications, charges, etc.)
                item_schema = section.get("itemSchema", {})
                fields = item_schema.get("fields", [])
                field_names = [f.get("fieldId") for f in fields]
                section_descriptions.append(
                    f'"{section_id}": List of items, each with fields: {", ".join(field_names)}'
                )
            else:
                # Regular section
                fields = section.get("fields", [])
                field_names = [f.get("fieldId") for f in fields]
                section_descriptions.append(
                    f'"{section_id}": {", ".join(field_names)}'
                )

        sections_str = "\n".join(f"  - {desc}" for desc in section_descriptions)

        # Build example output structure
        example_output = self._build_example_output(template)

        prompt = f"""Extract information from this {doc_name} document.

**DOCUMENT TYPE:** {doc_type}

**SECTIONS TO EXTRACT:**
{sections_str}

**EXTRACTION RULES:**
1. Extract ALL available information from each section
2. For list sections (medications, charges, etc.), extract ALL items as an array
3. Use exact field IDs as specified in the sections above
4. If a field is not found, omit it (don't use null/None)
5. For dates, use YYYY-MM-DD format
6. For currency, extract numeric values only (no currency symbols)
7. Preserve all details including instructions, remarks, and notes

**OUTPUT FORMAT (JSON only, no markdown):**
{json.dumps(example_output, indent=2)}

**IMPORTANT:**
- Return ONLY valid JSON, no markdown code blocks
- Extract complete information for all sections
- For list sections, include ALL items found in the document
- Use exact field IDs as shown in the example

**OCR TEXT:**
{ocr_text}

**YOUR RESPONSE (JSON only):**
"""
        return prompt

    def _build_example_output(self, template: Dict) -> Dict:
        """Build example output structure for prompt"""
        example = {}
        sections = template.get("sections", [])

        for section in sections:
            section_id = section.get("sectionId")
            is_list = section.get("isList", False)

            if is_list:
                # List section - show array with one example item
                item_schema = section.get("itemSchema", {})
                fields = item_schema.get("fields", [])
                example_item = {}
                for field in fields[:3]:  # Show first 3 fields as example
                    field_id = field.get("fieldId")
                    data_type = field.get("dataType", "text")
                    if data_type == "numeric":
                        example_item[field_id] = 0
                    elif data_type == "currency":
                        example_item[field_id] = 0.00
                    elif data_type == "date":
                        example_item[field_id] = "2025-01-01"
                    else:
                        example_item[field_id] = "string"
                example[section_id] = [example_item]
            else:
                # Regular section - show object with fields
                fields = section.get("fields", [])
                section_data = {}
                for field in fields[:3]:  # Show first 3 fields as example
                    field_id = field.get("fieldId")
                    data_type = field.get("dataType", "text")
                    if data_type == "numeric":
                        section_data[field_id] = 0
                    elif data_type == "date":
                        section_data[field_id] = "2025-01-01"
                    elif data_type == "list":
                        section_data[field_id] = ["item1", "item2"]
                    else:
                        section_data[field_id] = "string"
                example[section_id] = section_data

        return example

    def _call_llm(self, model_name: str, prompt: str) -> Tuple[str, float, Optional[str]]:
        """Call Ollama LLM"""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=300
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("response", "")
                llm_time = time.time() - start_time
                return output, llm_time, None
            else:
                return "", 0, f"LLM API error: {response.status_code}"

        except requests.exceptions.Timeout:
            return "", 0, "LLM request timeout"
        except Exception as e:
            return "", 0, f"LLM error: {str(e)}"

    def _parse_llm_output(self, raw_output: str, template: Dict) -> Optional[Dict]:
        """Parse LLM output to extract JSON"""
        try:
            # Clean markdown code blocks
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Parse JSON
            parsed = json.loads(cleaned)
            return parsed

        except json.JSONDecodeError as e:
            # Try to extract JSON from text
            json_match = re.search(r'\{[\s\S]*\}', raw_output)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            return None

    def _build_structured_document(self, parsed_data: Dict, template: Dict) -> Dict:
        """Build structured document from parsed data"""
        doc_type = template.get("documentType", "UNKNOWN")
        doc_id = template.get("templateId")

        structured = {
            "documentType": doc_type,
            "templateId": doc_id,
            "extractedData": {}
        }

        # Map parsed data to template sections
        sections = template.get("sections", [])
        for section in sections:
            section_id = section.get("sectionId")

            if section_id in parsed_data:
                structured["extractedData"][section_id] = parsed_data[section_id]

        return structured

    def _calculate_completeness(self, structured_doc: Dict, template: Dict) -> Dict:
        """Calculate extraction completeness"""
        extracted_data = structured_doc.get("extractedData", {})
        sections = template.get("sections", [])

        total_required_fields = 0
        extracted_fields = 0

        for section in sections:
            section_id = section.get("sectionId")
            is_required = section.get("required", False)
            is_list = section.get("isList", False)

            if is_list:
                # Count list items
                items = extracted_data.get(section_id, [])
                if items and len(items) > 0:
                    extracted_fields += 1
                if is_required:
                    total_required_fields += 1
            else:
                # Count fields in section
                fields = section.get("fields", [])
                section_data = extracted_data.get(section_id, {})

                for field in fields:
                    field_id = field.get("fieldId")
                    is_field_required = field.get("required", False)

                    if is_field_required:
                        total_required_fields += 1
                        if field_id in section_data and section_data[field_id]:
                            extracted_fields += 1

        completeness_score = (extracted_fields / total_required_fields * 100) if total_required_fields > 0 else 0

        return {
            "completenessScore": round(completeness_score, 1),
            "extractedFields": extracted_fields,
            "totalRequiredFields": total_required_fields
        }


if __name__ == "__main__":
    print("Document Extractor - For clinical and financial document extraction")
    print("Handles prescriptions, bills, certificates, and diagnostic reports")
