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

        # Debug: Show ALL extracted parameter names
        stage1_params = [p.get('name', '') for p in freeform_data.get('parameters', [])]
        print(f"   📝 Stage 1 extracted {len(stage1_params)} parameter names:")
        for i, name in enumerate(stage1_params, 1):
            print(f"      {i:2d}. {name}")

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

        # Get expected parameter IDs from template (simplified - just IDs, no aliases)
        expected_params = []
        for section in template.get("sections", []):
            for param in section.get("parameters", []):
                param_id = param.get("parameterId", "")
                if param_id:
                    expected_params.append(param_id)

        param_count = len(expected_params)
        param_hint = "\n   - ".join(expected_params)

        return f"""Extract test parameters from this {test_name} report.

**YOU MUST EXTRACT EXACTLY THESE {param_count} PARAMETERS (use these exact names):**
   - {param_hint}

**CRITICAL INSTRUCTIONS:**
1. Extract ONLY the {param_count} parameters listed above - use the exact parameter names shown
2. Search ALL pages in the document (parameters may be on different pages)
3. For each parameter extract:
   - Parameter name: Use the EXACT name from the list above
   - Value (numeric or text)
   - Unit (if present)
   - Reference range min and max (if present)
4. Also extract patient metadata
5. DO NOT extract parameters not in the list above (e.g., if you see "BASOPHILS_ABSOLUTE" but it's not listed, skip it)

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
      "name": "HEMOGLOBIN",
      "value": 13.5,
      "unit": "g/dL",
      "refMin": 13.0,
      "refMax": 17.0
    }},
    {{
      "name": "WBC_COUNT",
      "value": 3680,
      "unit": "cells/cu.mm",
      "refMin": 4000,
      "refMax": 10000
    }}
  ]
}}

**IMPORTANT:**
- You MUST extract all {param_count} parameters from the list above
- Use EXACT parameter names from the list (not document names)
- Search ALL pages - parameters may be split across multiple pages
- Include reference ranges from document if present
- Return ONLY JSON, no markdown blocks
- If a parameter is not found in the document, you may omit it (but try to find all {param_count})

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

    def _calculate_match_score(self, extracted_name: str, param_id: str, display_name: str, aliases: List[str]) -> int:
        """
        Calculate match score between extracted name and template parameter.
        Higher score = better match.

        Scoring:
        - 1000: Exact match (parameterId, displayName, or alias)
        - 500+: Word-based match (score = 500 + number of matching words)
        - 0: No match
        """
        ext_upper = extracted_name.upper().strip()

        # Exact matches (highest priority)
        if ext_upper == param_id.upper():
            return 1000
        if ext_upper == display_name.upper():
            return 1000
        if ext_upper in [a.upper() for a in aliases]:
            return 1000

        # Word-based fuzzy matching
        # Tokenize: split on spaces, underscores, hyphens, parentheses
        import re
        ext_words = set(re.split(r'[\s_\-()]+', ext_upper))
        ext_words = {w for w in ext_words if w}  # Remove empty strings

        # Check against parameterId words
        param_words = set(re.split(r'[\s_\-()]+', param_id.upper()))
        param_words = {w for w in param_words if w}

        # Check against display name words
        display_words = set(re.split(r'[\s_\-()]+', display_name.upper()))
        display_words = {w for w in display_words if w}

        # Check against all aliases
        max_word_match = 0
        for alias in aliases:
            alias_words = set(re.split(r'[\s_\-()]+', alias.upper()))
            alias_words = {w for w in alias_words if w}

            # Count matching words
            common_words = ext_words & alias_words
            if common_words:
                # Score based on percentage of words matched
                match_ratio = len(common_words) / max(len(ext_words), len(alias_words))
                score = int(500 + match_ratio * 100 + len(common_words) * 10)
                max_word_match = max(max_word_match, score)

        # Also check parameterId and displayName word matching
        common_param = ext_words & param_words
        if common_param:
            match_ratio = len(common_param) / max(len(ext_words), len(param_words))
            score = int(500 + match_ratio * 100 + len(common_param) * 10)
            max_word_match = max(max_word_match, score)

        common_display = ext_words & display_words
        if common_display:
            match_ratio = len(common_display) / max(len(ext_words), len(display_words))
            score = int(500 + match_ratio * 100 + len(common_display) * 10)
            max_word_match = max(max_word_match, score)

        return max_word_match

    def _calculate_missing_formulas(self, mapped: Dict, template: Dict, matched_by_section: Dict):
        """Calculate missing parameters using formulas"""
        # Build a lookup of all extracted parameter IDs -> values
        param_values = {}
        for section in mapped["testResults"]["sections"]:
            for param in section.get("parameters", []):
                param_id = param.get("parameterId")
                value = param.get("value")
                if param_id and value is not None:
                    param_values[param_id] = value

        # For each template parameter with a formula
        for section in template.get("sections", []):
            section_id = section.get("sectionId")

            for template_param in section.get("parameters", []):
                param_id = template_param.get("parameterId")
                formula = template_param.get("formula")

                # Skip if no formula or already extracted
                if not formula or param_id in param_values:
                    continue

                # Try to evaluate formula
                try:
                    # Replace parameter IDs in formula with their values
                    eval_formula = formula
                    for pid, pvalue in param_values.items():
                        eval_formula = eval_formula.replace(pid, str(pvalue))

                    # Evaluate the formula
                    calculated_value = eval(eval_formula)

                    # Get reference range from template
                    ref_range = self.template_manager.get_reference_range(template_param)

                    # Create parameter object
                    param_obj = {
                        "parameterId": param_id,
                        "value": round(calculated_value, template_param.get("decimalPlaces", 2)),
                        "unit": template_param.get("unit", ""),
                        "referenceRange": ref_range,
                        "referenceSource": "template"
                    }

                    # Calculate status
                    if ref_range:
                        try:
                            status = self.template_manager.calculate_status(calculated_value, ref_range)
                            param_obj["status"] = status

                            flags = []
                            if status == "HIGH":
                                flags.append("HIGH")
                            elif status == "LOW":
                                flags.append("LOW")

                            # Check critical values
                            critical = template_param.get("criticalValues", {})
                            if critical:
                                if critical.get("low") and calculated_value < critical["low"]:
                                    flags.append("CRITICAL_LOW")
                                if critical.get("high") and calculated_value > critical["high"]:
                                    flags.append("CRITICAL_HIGH")

                            param_obj["flags"] = flags
                        except:
                            param_obj["status"] = "UNKNOWN"
                            param_obj["flags"] = []
                    else:
                        param_obj["status"] = "UNKNOWN"
                        param_obj["flags"] = []

                    # Add to appropriate section
                    for result_section in mapped["testResults"]["sections"]:
                        if result_section["sectionId"] == section_id:
                            result_section["parameters"].append(param_obj)
                            break
                    else:
                        # Section doesn't exist, create it
                        mapped["testResults"]["sections"].append({
                            "sectionId": section_id,
                            "parameters": [param_obj]
                        })

                    print(f"   ✅ Calculated {param_id} = {param_obj['value']} using formula: {formula}")

                except Exception as e:
                    # Formula evaluation failed (missing dependencies or invalid formula)
                    pass

        # Reverse formula calculation (e.g., if VLDL = TRIG/5, then TRIG = VLDL*5)
        # Common patterns: A = B / C  =>  B = A * C
        for section in template.get("sections", []):
            section_id = section.get("sectionId")

            for template_param in section.get("parameters", []):
                param_id = template_param.get("parameterId")

                # Skip if already extracted or calculated
                if param_id in param_values:
                    continue

                # Check if any other parameter has a formula that uses this param
                for other_section in template.get("sections", []):
                    for other_param in other_section.get("parameters", []):
                        other_id = other_param.get("parameterId")
                        formula = other_param.get("formula")

                        # If this parameter is used in another's formula
                        if formula and param_id in formula and other_id in param_values:
                            # Try to reverse calculate for simple division formulas
                            # Pattern: other = param / divisor  =>  param = other * divisor
                            if " / " in formula:
                                parts = formula.split(" / ")
                                if len(parts) == 2 and parts[0].strip() == param_id:
                                    try:
                                        divisor = float(parts[1].strip())
                                        calculated_value = param_values[other_id] * divisor

                                        # Get reference range from template
                                        ref_range = self.template_manager.get_reference_range(template_param)

                                        # Create parameter object
                                        param_obj = {
                                            "parameterId": param_id,
                                            "value": round(calculated_value, template_param.get("decimalPlaces", 0)),
                                            "unit": template_param.get("unit", ""),
                                            "referenceRange": ref_range,
                                            "referenceSource": "template"
                                        }

                                        # Calculate status
                                        if ref_range:
                                            try:
                                                status = self.template_manager.calculate_status(calculated_value, ref_range)
                                                param_obj["status"] = status

                                                flags = []
                                                if status == "HIGH":
                                                    flags.append("HIGH")
                                                elif status == "LOW":
                                                    flags.append("LOW")

                                                critical = template_param.get("criticalValues", {})
                                                if critical:
                                                    if critical.get("low") and calculated_value < critical["low"]:
                                                        flags.append("CRITICAL_LOW")
                                                    if critical.get("high") and calculated_value > critical["high"]:
                                                        flags.append("CRITICAL_HIGH")

                                                param_obj["flags"] = flags
                                            except:
                                                param_obj["status"] = "UNKNOWN"
                                                param_obj["flags"] = []
                                        else:
                                            param_obj["status"] = "UNKNOWN"
                                            param_obj["flags"] = []

                                        # Add to appropriate section
                                        for result_section in mapped["testResults"]["sections"]:
                                            if result_section["sectionId"] == section_id:
                                                result_section["parameters"].append(param_obj)
                                                param_values[param_id] = calculated_value
                                                break
                                        else:
                                            # Section doesn't exist, create it
                                            mapped["testResults"]["sections"].append({
                                                "sectionId": section_id,
                                                "parameters": [param_obj]
                                            })
                                            param_values[param_id] = calculated_value

                                        print(f"   ✅ Reverse-calculated {param_id} = {param_obj['value']} from {other_id} (formula: {formula})")

                                    except Exception as e:
                                        pass

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
            ext_name = ext_param.get("name", "").strip()

            # Find best matching template parameter using scoring
            best_match = None
            best_section_id = None
            best_score = 0

            for section_id, section_data in template_sections.items():
                for template_param in section_data["parameters"]:
                    # Calculate match score
                    param_id = template_param.get("parameterId", "")
                    display_name = template_param.get("displayName", "")
                    aliases = template_param.get("aliases", [])

                    score = self._calculate_match_score(ext_name, param_id, display_name, aliases)

                    # Keep track of best match
                    if score > best_score:
                        best_score = score
                        best_match = template_param
                        best_section_id = section_id

            # Only use matches with score >= 500 (at least some word overlap)
            if best_score < 500:
                best_match = None
                best_section_id = None

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

        # Build sections - deduplicate parameters by parameterId
        for section_id, params in matched_by_section.items():
            # Deduplicate: keep first occurrence with non-None value for each parameterId
            seen_params = {}
            dedup_params = []

            for param in params:
                param_id = param.get("parameterId")
                param_value = param.get("value")

                # Skip parameters with None value
                if param_value is None:
                    continue

                # If we haven't seen this param_id, or we have but previous was None
                if param_id not in seen_params:
                    seen_params[param_id] = param
                    dedup_params.append(param)
                # If we've seen it but current value is better (not None), replace
                elif seen_params[param_id].get("value") is None and param_value is not None:
                    # Replace in list
                    idx = dedup_params.index(seen_params[param_id])
                    dedup_params[idx] = param
                    seen_params[param_id] = param

            mapped["testResults"]["sections"].append({
                "sectionId": section_id,
                "parameters": dedup_params
            })

        # Formula-based calculation for missing parameters
        self._calculate_missing_formulas(mapped, template, matched_by_section)

        return mapped


if __name__ == "__main__":
    print("Template Extractor V2 - Two-Stage Approach")
    print("This module uses a 2-stage process for better extraction accuracy")
