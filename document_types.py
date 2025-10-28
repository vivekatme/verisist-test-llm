"""
Medical Document Type Classifications

This module defines all supported medical document types for the extraction system.
Used for document classification, filtering, and routing to appropriate extractors.
"""

from enum import Enum
from typing import Dict, List


class DocumentCategory(str, Enum):
    """High-level document categories"""
    LAB_REPORT = "LAB_REPORT"
    CLINICAL = "CLINICAL"
    FINANCIAL = "FINANCIAL"
    DIAGNOSTIC = "DIAGNOSTIC"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    MONITORING = "MONITORING"
    UNKNOWN = "UNKNOWN"


class DocumentType(str, Enum):
    """Comprehensive document type classification"""

    # ==================== LAB REPORTS ====================
    # Hematology
    COMPLETE_BLOOD_COUNT = "COMPLETE_BLOOD_COUNT"
    ESR_TEST = "ESR_TEST"
    COAGULATION_PANEL = "COAGULATION_PANEL"

    # Biochemistry
    LIPID_PROFILE = "LIPID_PROFILE"
    LIVER_FUNCTION_TEST = "LIVER_FUNCTION_TEST"
    KIDNEY_FUNCTION_TEST = "KIDNEY_FUNCTION_TEST"
    GLUCOSE_PANEL = "GLUCOSE_PANEL"
    CARDIAC_ENZYMES = "CARDIAC_ENZYMES"
    VITAMIN_D_TEST = "VITAMIN_D_TEST"
    VITAMIN_B12_TEST = "VITAMIN_B12_TEST"
    IRON_STUDIES = "IRON_STUDIES"
    ELECTROLYTES_PANEL = "ELECTROLYTES_PANEL"

    # Endocrinology
    THYROID_FUNCTION_TEST = "THYROID_FUNCTION_TEST"

    # Serology/Infectious Disease
    DENGUE_PROFILE = "DENGUE_PROFILE"
    COVID19_TEST = "COVID19_TEST"
    MALARIA_TEST = "MALARIA_TEST"
    TYPHOID_TEST = "TYPHOID_TEST"
    HEPATITIS_PANEL = "HEPATITIS_PANEL"
    CRP_TEST = "CRP_TEST"

    # Urine
    URINE_ROUTINE = "URINE_ROUTINE"

    # ==================== CLINICAL DOCUMENTS ====================
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    MEDICAL_CERTIFICATE = "MEDICAL_CERTIFICATE"
    CONSULTATION_NOTES = "CONSULTATION_NOTES"
    REFERRAL_LETTER = "REFERRAL_LETTER"
    IMMUNIZATION_RECORD = "IMMUNIZATION_RECORD"

    # ==================== FINANCIAL DOCUMENTS ====================
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    INSURANCE_CLAIM = "INSURANCE_CLAIM"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"
    ESTIMATE_QUOTATION = "ESTIMATE_QUOTATION"

    # ==================== DIAGNOSTIC REPORTS ====================
    XRAY_REPORT = "XRAY_REPORT"
    CT_SCAN_REPORT = "CT_SCAN_REPORT"
    MRI_REPORT = "MRI_REPORT"
    ULTRASOUND_REPORT = "ULTRASOUND_REPORT"
    MAMMOGRAPHY_REPORT = "MAMMOGRAPHY_REPORT"
    ECG_REPORT = "ECG_REPORT"
    ECHO_REPORT = "ECHO_REPORT"
    PET_SCAN_REPORT = "PET_SCAN_REPORT"

    # ==================== ADMINISTRATIVE DOCUMENTS ====================
    VACCINATION_CERTIFICATE = "VACCINATION_CERTIFICATE"
    FITNESS_CERTIFICATE = "FITNESS_CERTIFICATE"
    PATIENT_REGISTRATION = "PATIENT_REGISTRATION"
    CONSENT_FORM = "CONSENT_FORM"

    # ==================== MONITORING LOGS ====================
    GLUCOSE_LOG = "GLUCOSE_LOG"
    BLOOD_PRESSURE_LOG = "BLOOD_PRESSURE_LOG"
    WEIGHT_LOG = "WEIGHT_LOG"
    MEDICATION_LOG = "MEDICATION_LOG"

    # ==================== UNKNOWN/OTHER ====================
    UNKNOWN = "UNKNOWN"
    OTHER = "OTHER"


class ExtractionComplexity(str, Enum):
    """Complexity level for document extraction"""
    SIMPLE = "SIMPLE"          # Single value or few fields (e.g., Medical Certificate)
    MODERATE = "MODERATE"      # Structured sections (e.g., Prescription)
    COMPLEX = "COMPLEX"        # Multiple sections, calculations (e.g., Hospital Bill)
    ADVANCED = "ADVANCED"      # Unstructured text, interpretation needed (e.g., Radiology)


# Document type metadata
DOCUMENT_TYPE_METADATA: Dict[DocumentType, Dict] = {
    # Lab Reports
    DocumentType.COMPLETE_BLOOD_COUNT: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Complete Blood Count (CBC)",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["CBC", "COMPLETE BLOOD COUNT", "HEMOGRAM", "HEMOGLOBIN", "WBC", "RBC", "PLATELET"],
        "icon": "🩸",
        "implemented": True
    },
    DocumentType.LIPID_PROFILE: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Lipid Profile",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["LIPID", "CHOLESTEROL", "HDL", "LDL", "TRIGLYCERIDE"],
        "icon": "💊",
        "implemented": True
    },
    DocumentType.LIVER_FUNCTION_TEST: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Liver Function Test (LFT)",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["LFT", "LIVER FUNCTION", "SGOT", "SGPT", "ALT", "AST", "BILIRUBIN"],
        "icon": "🫀",
        "implemented": True
    },
    DocumentType.KIDNEY_FUNCTION_TEST: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Kidney Function Test (KFT)",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["KFT", "RFT", "KIDNEY FUNCTION", "RENAL", "CREATININE", "UREA", "BUN"],
        "icon": "🫘",
        "implemented": True
    },
    DocumentType.THYROID_FUNCTION_TEST: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Thyroid Function Test (TFT)",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["TFT", "THYROID", "TSH", "T3", "T4", "FT3", "FT4"],
        "icon": "🦋",
        "implemented": True
    },
    DocumentType.GLUCOSE_PANEL: {
        "category": DocumentCategory.LAB_REPORT,
        "displayName": "Blood Glucose Panel",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["GLUCOSE", "SUGAR", "HBA1C", "FASTING", "POSTPRANDIAL", "DIABETES"],
        "icon": "🍬",
        "implemented": True
    },

    # Clinical Documents
    DocumentType.PRESCRIPTION: {
        "category": DocumentCategory.CLINICAL,
        "displayName": "Doctor Prescription",
        "complexity": ExtractionComplexity.COMPLEX,
        "keywords": ["PRESCRIPTION", "RX", "MEDICATION", "DOSAGE", "DRUG", "TABLET", "CAPSULE"],
        "icon": "📝",
        "implemented": True  # Will implement next
    },
    DocumentType.DISCHARGE_SUMMARY: {
        "category": DocumentCategory.CLINICAL,
        "displayName": "Discharge Summary",
        "complexity": ExtractionComplexity.COMPLEX,
        "keywords": ["DISCHARGE", "ADMISSION", "HOSPITALIZATION", "INPATIENT", "DISCHARGE SUMMARY"],
        "icon": "🏥",
        "implemented": True
    },
    DocumentType.MEDICAL_CERTIFICATE: {
        "category": DocumentCategory.CLINICAL,
        "displayName": "Medical Certificate",
        "complexity": ExtractionComplexity.SIMPLE,
        "keywords": ["MEDICAL CERTIFICATE", "SICK LEAVE", "FITNESS CERTIFICATE", "UNFIT"],
        "icon": "📄",
        "implemented": True
    },

    # Financial Documents
    DocumentType.HOSPITAL_BILL: {
        "category": DocumentCategory.FINANCIAL,
        "displayName": "Hospital Bill",
        "complexity": ExtractionComplexity.COMPLEX,
        "keywords": ["BILL", "INVOICE", "CHARGES", "CONSULTATION", "AMOUNT", "TOTAL", "TAX"],
        "icon": "💰",
        "implemented": True
    },
    DocumentType.PHARMACY_BILL: {
        "category": DocumentCategory.FINANCIAL,
        "displayName": "Pharmacy Bill",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["PHARMACY", "CHEMIST", "MEDICINE", "MRP", "QUANTITY", "DRUG STORE"],
        "icon": "💊",
        "implemented": True
    },

    # Diagnostic Reports
    DocumentType.ECG_REPORT: {
        "category": DocumentCategory.DIAGNOSTIC,
        "displayName": "ECG Report",
        "complexity": ExtractionComplexity.MODERATE,
        "keywords": ["ECG", "EKG", "ELECTROCARDIOGRAM", "HEART RATE", "RHYTHM", "QRS"],
        "icon": "❤️",
        "implemented": True
    },
    DocumentType.XRAY_REPORT: {
        "category": DocumentCategory.DIAGNOSTIC,
        "displayName": "X-Ray Report",
        "complexity": ExtractionComplexity.ADVANCED,
        "keywords": ["X-RAY", "XRAY", "RADIOGRAPH", "CHEST PA", "FINDINGS", "IMPRESSION"],
        "icon": "🦴",
        "implemented": True
    },
    DocumentType.ULTRASOUND_REPORT: {
        "category": DocumentCategory.DIAGNOSTIC,
        "displayName": "Ultrasound Report",
        "complexity": ExtractionComplexity.ADVANCED,
        "keywords": ["ULTRASOUND", "USG", "SONOGRAPHY", "DOPPLER"],
        "icon": "🔊",
        "implemented": True
    },

    # Administrative
    DocumentType.VACCINATION_CERTIFICATE: {
        "category": DocumentCategory.ADMINISTRATIVE,
        "displayName": "Vaccination Certificate",
        "complexity": ExtractionComplexity.SIMPLE,
        "keywords": ["VACCINATION", "VACCINE", "IMMUNIZATION", "DOSE", "COVAXIN", "COVISHIELD"],
        "icon": "💉",
        "implemented": True
    },

    # Unknown
    DocumentType.UNKNOWN: {
        "category": DocumentCategory.UNKNOWN,
        "displayName": "Unknown Document Type",
        "complexity": ExtractionComplexity.ADVANCED,
        "keywords": [],
        "icon": "❓",
        "implemented": False
    }
}


def get_document_category(doc_type: DocumentType) -> DocumentCategory:
    """Get category for a document type"""
    metadata = DOCUMENT_TYPE_METADATA.get(doc_type, {})
    return metadata.get("category", DocumentCategory.UNKNOWN)


def get_display_name(doc_type: DocumentType) -> str:
    """Get human-readable display name"""
    metadata = DOCUMENT_TYPE_METADATA.get(doc_type, {})
    return metadata.get("displayName", doc_type.value)


def get_keywords(doc_type: DocumentType) -> List[str]:
    """Get identification keywords for document type"""
    metadata = DOCUMENT_TYPE_METADATA.get(doc_type, {})
    return metadata.get("keywords", [])


def is_implemented(doc_type: DocumentType) -> bool:
    """Check if extraction is implemented for this document type"""
    metadata = DOCUMENT_TYPE_METADATA.get(doc_type, {})
    return metadata.get("implemented", False)


def get_all_lab_report_types() -> List[DocumentType]:
    """Get all lab report document types"""
    return [
        dt for dt in DocumentType
        if get_document_category(dt) == DocumentCategory.LAB_REPORT
    ]


def get_all_clinical_types() -> List[DocumentType]:
    """Get all clinical document types"""
    return [
        dt for dt in DocumentType
        if get_document_category(dt) == DocumentCategory.CLINICAL
    ]


def get_all_financial_types() -> List[DocumentType]:
    """Get all financial document types"""
    return [
        dt for dt in DocumentType
        if get_document_category(dt) == DocumentCategory.FINANCIAL
    ]


def get_implemented_types() -> List[DocumentType]:
    """Get all implemented document types"""
    return [dt for dt in DocumentType if is_implemented(dt)]
