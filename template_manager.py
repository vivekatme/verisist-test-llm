#!/usr/bin/env python3
"""
Template Manager - Load and manage test templates for medical document extraction.

This module provides functionality to:
- Load test templates from JSON files
- Identify test types from OCR text
- Match parameters with aliases
- Manage template metadata
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


class TemplateManager:
    """Manages test templates for medical document extraction."""

    def __init__(self, templates_dir: str = "templates"):
        """Initialize template manager with templates directory."""
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, Dict] = {}
        self.template_index: Dict[str, str] = {}  # Maps test type to template ID
        self._load_all_templates()

    def _load_all_templates(self):
        """Load all template JSON files from templates directory."""
        if not self.templates_dir.exists():
            print(f"⚠️  Templates directory not found: {self.templates_dir}")
            return

        template_files = list(self.templates_dir.glob("*.json"))

        for template_file in template_files:
            try:
                with open(template_file, 'r') as f:
                    template = json.load(f)

                template_id = template.get("templateId")
                test_type = template.get("testType")

                if template_id and test_type:
                    self.templates[template_id] = template
                    self.template_index[test_type] = template_id

                    print(f"✅ Loaded template: {template.get('displayName')} ({template_id})")
                else:
                    print(f"⚠️  Invalid template format: {template_file.name}")

            except Exception as e:
                print(f"❌ Error loading template {template_file.name}: {e}")

    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get template by template ID."""
        return self.templates.get(template_id)

    def get_template_by_test_type(self, test_type: str) -> Optional[Dict]:
        """Get template by test type."""
        template_id = self.template_index.get(test_type)
        if template_id:
            return self.templates.get(template_id)
        return None

    def list_templates(self) -> List[Dict]:
        """List all available templates with basic info."""
        result = []
        for template in self.templates.values():
            result.append({
                "templateId": template.get("templateId"),
                "testType": template.get("testType"),
                "displayName": template.get("displayName"),
                "department": template.get("department"),
                "version": template.get("version")
            })
        return result

    def identify_test_type(self, ocr_text: str) -> Optional[str]:
        """
        Identify test type from OCR text using keywords and aliases.

        Returns the test_type if found, None otherwise.
        """
        ocr_text_upper = ocr_text.upper()

        # Check each template for matches
        best_match = None
        max_score = 0

        for template in self.templates.values():
            score = 0
            test_type = template.get("testType")
            display_name = template.get("displayName", "").upper()
            aliases = template.get("metadata", {}).get("commonAliases", [])
            department = template.get("department", "").upper()

            # Check display name (strong match)
            if display_name in ocr_text_upper:
                score += 10

            # Check aliases (strong match)
            for alias in aliases:
                if alias.upper() in ocr_text_upper:
                    score += 8

            # Check department (weak match)
            if department in ocr_text_upper:
                score += 2

            # Check for specific test type keywords
            if test_type == "COMPLETE_BLOOD_COUNT":
                if re.search(r'\b(CBC|COMPLETE BLOOD COUNT|HEMOGRAM)\b', ocr_text_upper):
                    score += 15
                if re.search(r'\b(HAEMOGLOBIN|HEMOGLOBIN|WBC|RBC|PLATELET)\b', ocr_text_upper):
                    score += 5

            elif test_type == "DENGUE_PROFILE":
                if re.search(r'\b(DENGUE|NS1|IGG|IGM)\b', ocr_text_upper):
                    score += 15

            elif test_type == "LIPID_PROFILE":
                if re.search(r'\b(LIPID|CHOLESTEROL|HDL|LDL|TRIGLYCERIDE)\b', ocr_text_upper):
                    score += 15

            # Update best match
            if score > max_score:
                max_score = score
                best_match = test_type

        # Return best match if score is above threshold
        if max_score >= 10:
            return best_match

        return None

    def match_parameter(self, parameter_name: str, section_params: List[Dict]) -> Optional[Dict]:
        """
        Match a parameter name (from OCR) to a template parameter definition.

        Uses fuzzy matching with parameter names and aliases.
        """
        param_name_upper = parameter_name.upper().strip()

        for param in section_params:
            # Check direct name match
            if param.get("displayName", "").upper() == param_name_upper:
                return param

            # Check parameter ID match
            if param.get("parameterId", "").upper() == param_name_upper:
                return param

            # Check aliases
            aliases = param.get("aliases", [])
            for alias in aliases:
                if alias.upper() == param_name_upper:
                    return param

            # Check partial matches (for OCR errors)
            display_name = param.get("displayName", "").upper()
            if param_name_upper in display_name or display_name in param_name_upper:
                # Calculate similarity
                if len(param_name_upper) > 3 and len(display_name) > 3:
                    similarity = self._calculate_similarity(param_name_upper, display_name)
                    if similarity > 0.7:  # 70% similarity threshold
                        return param

        return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity (Jaccard similarity on words)."""
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def get_all_parameters(self, template: Dict) -> List[Dict]:
        """Get all parameters from all sections of a template."""
        all_params = []
        sections = template.get("sections", [])

        for section in sections:
            params = section.get("parameters", [])
            for param in params:
                # Add section info to param
                param_with_section = param.copy()
                param_with_section["sectionId"] = section.get("sectionId")
                param_with_section["sectionName"] = section.get("sectionName")
                all_params.append(param_with_section)

        return all_params

    def get_reference_range(self, param: Dict, gender: Optional[str] = None,
                           age: Optional[int] = None) -> Dict:
        """
        Get appropriate reference range for a parameter based on gender and age.

        Args:
            param: Parameter definition from template
            gender: Patient gender ("M" or "F")
            age: Patient age in years

        Returns:
            Reference range dict with min/max values
        """
        ref_ranges = param.get("referenceRanges", {})

        # Try gender-specific range
        if gender:
            gender_key = "male" if gender.upper() in ["M", "MALE"] else "female"
            if gender_key in ref_ranges:
                return ref_ranges[gender_key]

        # Try age-specific range
        if age is not None:
            for key, value in ref_ranges.items():
                if "child" in key.lower():
                    # Extract age range from key (e.g., "child_1_5" -> 1-5 years)
                    parts = key.split("_")
                    if len(parts) >= 3:
                        try:
                            min_age = int(parts[1])
                            max_age = int(parts[2])
                            if min_age <= age <= max_age:
                                return value
                        except ValueError:
                            continue

        # Return default range
        return ref_ranges.get("default", {})

    def calculate_status(self, value: float, ref_range: Dict) -> str:
        """
        Calculate parameter status (NORMAL, HIGH, LOW) based on reference range.

        Args:
            value: Measured value
            ref_range: Reference range dict with min/max

        Returns:
            Status string: "NORMAL", "HIGH", "LOW", or "UNKNOWN"
        """
        if not ref_range:
            return "UNKNOWN"

        # Handle simple min/max ranges
        if "min" in ref_range and "max" in ref_range:
            min_val = ref_range.get("min")
            max_val = ref_range.get("max")

            if min_val is not None and value < min_val:
                return "LOW"
            elif max_val is not None and value > max_val:
                return "HIGH"
            else:
                return "NORMAL"

        # Handle complex ranges (e.g., desirable/borderline/high)
        # For these, we'll check if value falls in any category
        for category, range_dict in ref_range.items():
            if isinstance(range_dict, dict):
                min_val = range_dict.get("min", float('-inf'))
                max_val = range_dict.get("max", float('inf'))

                if min_val <= value <= max_val:
                    # Categorize as HIGH/LOW/NORMAL based on category name
                    if "high" in category.lower() or "elevated" in category.lower():
                        return "HIGH"
                    elif "low" in category.lower():
                        return "LOW"
                    else:
                        return "NORMAL"

        return "UNKNOWN"


# Convenience function to create a singleton instance
_template_manager = None

def get_template_manager() -> TemplateManager:
    """Get or create singleton TemplateManager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager


if __name__ == "__main__":
    # Test template manager
    print("\n" + "=" * 80)
    print("  TEMPLATE MANAGER TEST")
    print("=" * 80)

    tm = TemplateManager()

    print(f"\n📋 Available Templates: {len(tm.templates)}")
    for template_info in tm.list_templates():
        print(f"   - {template_info['displayName']} ({template_info['testType']})")

    # Test identification
    print("\n🔍 Test Type Identification:")

    test_samples = [
        "COMPLETE BLOOD COUNT (CBC), WHOLE BLOOD EDTA\nHAEMOGLOBIN\nPCV\nRBC COUNT",
        "DENGUE PROFILE (IGG & IGM ANTIBODY & NS1 ANTIGEN), SERUM\nDENGUE NS1 ANTIGEN",
        "LIPID PROFILE\nTOTAL CHOLESTEROL\nHDL CHOLESTEROL\nLDL CHOLESTEROL"
    ]

    for sample in test_samples:
        test_type = tm.identify_test_type(sample)
        print(f"   Sample: {sample[:50]}...")
        print(f"   Identified: {test_type}\n")

    # Test parameter matching
    print("🎯 Parameter Matching Test:")
    cbc_template = tm.get_template_by_test_type("COMPLETE_BLOOD_COUNT")
    if cbc_template:
        all_params = tm.get_all_parameters(cbc_template)
        test_names = ["HAEMOGLOBIN", "HB", "Hemoglobin", "WBC", "Total Leucocyte Count"]

        for name in test_names:
            matched = tm.match_parameter(name, all_params)
            if matched:
                print(f"   '{name}' -> {matched['displayName']} ({matched['parameterId']})")
            else:
                print(f"   '{name}' -> No match")

    print("\n" + "=" * 80)
