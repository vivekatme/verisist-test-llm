#!/usr/bin/env python3
"""
Template Extractor V2 - Two-Stage Approach

Stage 1: Free-form extraction (get everything)
Stage 2: Map to template structure + fill gaps

This approach is more reliable than single-shot template-guided extraction.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from template_manager import TemplateManager, get_template_manager


OLLAMA_HOST = "http://localhost:11434"


class TemplateExtractorV2:
    """Two-stage template extraction"""

    def __init__(self, template_manager: Optional[TemplateManager] = None):
        self.template_manager = template_manager or get_template_manager()

    def extract_with_llm(self, model_name: str, ocr_text: str, template: Dict) -> Dict:
        """
        Two-stage extraction:
        1. Free-form extraction (get all values)
        2. Map to template structure
        """
        # Stage 1: Free-form extraction
        print("   Stage 1: Free-form extraction...")
        freeform_prompt = self._get_freeform_prompt(ocr_text, template)
        freeform_response, time1, error1 = self._call_llm(model_name, freeform_prompt)

        if error1:
            return {"success": False, "error": f"Stage 1 failed: {error1}", "stage": 1}

        # Parse free-form extraction
        freeform_data = self._parse_json_response(freeform_response)
        if not freeform_data:
            return {"success": False, "error": "Stage 1 JSON parsing failed", "stage": 1}

        print(f"   ✅ Stage 1: Extracted {len(freeform_data.get('parameters', []))} parameters")

        # Stage 2: Map to template
        print("   Stage 2: Mapping to template...")
        mapped_data = self._map_to_template(freeform_data, template)

        print(f"   ✅ Stage 2: Mapped to template structure")

        return {
            "success": True,
            "data": mapped_data,
            "timings": {"stage1": time1},
            "raw_stage1": freeform_response
        }

    def _get_freeform_prompt(self, ocr_text: str, template: Dict) -> str:
        """Generate free-form extraction prompt (no template constraints)"""
        test_name = template.get("displayName", "Medical Test")

        return f"""Extract ALL test parameters from this {test_name} report.

**INSTRUCTIONS:**
1. Find EVERY test parameter with its value
2. For each parameter extract:
   - Parameter name (as it appears in document)
   - Value (numeric or text)
   - Unit (if present)
   - Reference range min and max (if present)
3. Also extract patient metadata

**OUTPUT FORMAT (JSON only, no markdown):**
{{
  "metadata": {{
    "patientName": "string",
    "age": "string",
    "gender": "M/F",
    "uhid": "string",
    "labName": "string",
    "collectionDate": "YYYY-MM-DD",
    "reportedDate": "YYYY-MM-DD"
  }},
  "parameters": [
    {{
      "name": "HAEMOGLOBIN",
      "value": 13.5,
      "unit": "g/dL",
      "refMin": 13.0,
      "refMax": 17.0
    }},
    {{
      "name": "WBC COUNT",
      "value": 3680,
      "unit": "cells/cu.mm",
      "refMin": 4000,
      "refMax": 10000
    }}
  ]
}}

**IMPORTANT:**
- Extract EVERY parameter you find
- Include the reference range from the document if present
- Return ONLY JSON, no markdown blocks

**OCR TEXT:**
{ocr_text}

**YOUR RESPONSE (JSON only):**
"""

    def _call_llm(self, model_name: str, prompt: str) -> Tuple[str, float, Optional[str]]:
        """Call Ollama LLM"""
        import time

        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": "You are a medical document extraction AI. Extract data accurately and return only JSON.",
            "stream": False,
            "options": {"temperature": 0.1}
        }

        start = time.time()
        try:
            response = requests.post(url, json=payload, timeout=300)
            elapsed = time.time() - start

            if response.status_code == 200:
                return response.json().get("response", ""), elapsed, None
            else:
                return "", elapsed, f"HTTP {response.status_code}"
        except Exception as e:
            return "", time.time() - start, str(e)

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        import re

        # Clean response
        cleaned = response.strip()

        # Remove markdown
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        # Fix common issues
        try:
            cleaned = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)
        except:
            pass

        try:
            return json.loads(cleaned)
        except:
            return None

    def _map_to_template(self, freeform_data: Dict, template: Dict) -> Dict:
        """Map free-form extraction to template structure"""
        mapped = {
            "documentMetadata": freeform_data.get("metadata", {}),
            "testResults": {
                "templateId": template.get("templateId"),
                "sections": []
            }
        }

        # Get all template parameters organized by section
        template_sections = {}
        for section in template.get("sections", []):
            section_id = section.get("sectionId")
            template_sections[section_id] = {
                "sectionName": section.get("sectionName"),
                "parameters": section.get("parameters", [])
            }

        # Extract parameters from freeform data
        extracted_params = freeform_data.get("parameters", [])

        # Match each extracted param to template
        matched_by_section = {}

        for ext_param in extracted_params:
            ext_name = ext_param.get("name", "").upper().strip()

            # Try to find matching template parameter
            best_match = None
            best_section_id = None

            for section_id, section_data in template_sections.items():
                for template_param in section_data["parameters"]:
                    # Check if name matches parameter or aliases
                    param_id = template_param.get("parameterId", "")
                    display_name = template_param.get("displayName", "").upper()
                    aliases = [a.upper() for a in template_param.get("aliases", [])]

                    if (ext_name == param_id.upper() or
                        ext_name == display_name or
                        ext_name in aliases or
                        any(alias in ext_name or ext_name in alias for alias in aliases)):

                        best_match = template_param
                        best_section_id = section_id
                        break

                if best_match:
                    break

            # If matched, add to appropriate section
            if best_match and best_section_id:
                if best_section_id not in matched_by_section:
                    matched_by_section[best_section_id] = []

                # Create parameter object
                ref_range = {}
                if ext_param.get("refMin") is not None and ext_param.get("refMax") is not None:
                    ref_range = {
                        "min": ext_param.get("refMin"),
                        "max": ext_param.get("refMax")
                    }
                    ref_source = "document"
                else:
                    # Use template default
                    ref_range = self.template_manager.get_reference_range(best_match)
                    ref_source = "template"

                param_obj = {
                    "parameterId": best_match.get("parameterId"),
                    "value": ext_param.get("value"),
                    "unit": ext_param.get("unit") or best_match.get("unit"),
                    "referenceRange": ref_range,
                    "referenceSource": ref_source
                }

                # Calculate status
                if param_obj["value"] is not None and ref_range:
                    try:
                        value_num = float(param_obj["value"])
                        status = self.template_manager.calculate_status(value_num, ref_range)
                        param_obj["status"] = status

                        # Check critical values
                        critical = best_match.get("criticalValues", {})
                        flags = []
                        if status == "HIGH":
                            flags.append("HIGH")
                        elif status == "LOW":
                            flags.append("LOW")

                        if critical:
                            if critical.get("low") and value_num < critical["low"]:
                                flags.append("CRITICAL_LOW")
                            if critical.get("high") and value_num > critical["high"]:
                                flags.append("CRITICAL_HIGH")

                        param_obj["flags"] = flags
                    except:
                        param_obj["status"] = "UNKNOWN"
                        param_obj["flags"] = []
                else:
                    param_obj["status"] = "UNKNOWN"
                    param_obj["flags"] = []

                matched_by_section[best_section_id].append(param_obj)

        # Build sections
        for section_id, params in matched_by_section.items():
            mapped["testResults"]["sections"].append({
                "sectionId": section_id,
                "parameters": params
            })

        return mapped


if __name__ == "__main__":
    print("Template Extractor V2 - Two-Stage Approach")
    print("This module uses a 2-stage process for better extraction accuracy")
