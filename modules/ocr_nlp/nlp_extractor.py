"""
modules/ocr_nlp/nlp_extractor.py

Extracts structured patient/ECG fields from raw OCR text using
regex patterns and lightweight NLP.
Designed for cardiology documents from Indian health centers.
"""

import re
from datetime import datetime


# ─────────────────────────────────────────
# FIELD PATTERNS
# ─────────────────────────────────────────

PATTERNS = {
    # Patient demographics
    "patient_name": [
        r"PATIENT\s*(?:NAME)?[:\-]?\s*([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        r"Name[:\-]\s*([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        r"Patient[:\-]\s*([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
    ],
    "dob": [
        r"DATE\s*OF\s*BIRTH[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        r"D\.?O\.?B\.?[:\-\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        r"Born[:\-\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        r"Birth\s*Date[:\-\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    ],
    "age": [
        r"Age[:\-\s]+(\d{1,3})\s*(?:yrs?|years?)?",
        r"(\d{2,3})\s*(?:year|yr)s?\s*old",
    ],
    "gender": [
        r"\b(Male|Female|M|F)\b",
        r"Sex[:\-\s]+(Male|Female|M|F)",
        r"Gender[:\-\s]+(Male|Female|M|F)",
    ],
    "hospital_number": [
        r"HOSPITAL\s*(?:NO\.?|NUMBER|NUM)?[:\-\s]*([A-Z]\d{5,})",
        r"MRN[:\-\s]*([A-Z0-9]{4,})",
        r"H\.?No[:\-\s]*([A-Z0-9]{4,})",
        r"Reg(?:istration)?\.?\s*No[:\-\s]*([A-Z0-9]{4,})",
        r"([A-Z]\d{6,})",  # generic: letter + 6+ digits
    ],
    # Hospital / facility
    "hospital": [
        r"HOSPITAL[:\-\s]*([A-Za-z ]+?)(?:\n|WARD|$)",
        r"(?:Hospital|Clinic|Centre|Center|PHC|CHC)[:\-\s]*([A-Za-z ]+?)(?:\n|$)",
    ],
    "ward": [
        r"WARD[:\-\s]*(\w+)",
        r"Ward\s*No\.?\s*[:\-]?\s*(\w+)",
    ],
    "consultant": [
        r"CONSULTANT[:\-\s]*(Dr\.?\s*[A-Za-z ]+?)(?:\n|$)",
        r"Consultant[:\-\s]*(Dr\.?\s*[A-Za-z ]+?)(?:\n|$)",
        r"Seen\s*by[:\-\s]*(Dr\.?\s*[A-Za-z ]+?)(?:\n|$)",
    ],
    # ECG parameters
    "ecg_date": [
        r"ECG\s*(?:performed|done|recorded)\s*on\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        r"ECG[:\-\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    ],
    "ecg_rate": [
        r"Rate[:\-\s]+(\d{2,3})\s*bpm",
        r"Heart\s*Rate[:\-\s]+(\d{2,3})",
        r"(\d{2,3})\s*bpm",
    ],
    "ecg_rhythm": [
        r"Rhythm[:\-\s]+([A-Za-z ]+?)(?:\n|-\s*Axis|$)",
        r"rhythm[:\-\s]+([A-Za-z ]+?)(?:\n|$)",
    ],
    "ecg_axis": [
        r"Axis[:\-\s]+([A-Za-z ]+?)(?:\n|-\s*PR|$)",
    ],
    "ecg_pr": [
        r"PR\s*(?:interval)?[:\-\s]+(\d{2,4})\s*ms",
        r"P-R[:\-\s]+(\d{2,4})\s*ms",
    ],
    "ecg_qrs": [
        r"QRS\s*(?:complex|duration|interval)?[:\-\s]+(\d{2,4})\s*ms",
        r"QRS[:\-\s]+(\d{2,4})",
    ],
    "ecg_qt": [
        r"QT[c]?\s*(?:interval)?[:\-\s]+(\d{2,4})\s*ms",
        r"QT[c]?[:\-\s]+(\d{2,4})",
    ],
    "ecg_st": [
        r"ST\s*(?:segment)?[:\-\s]+(.+?)(?:\n|$)",
        r"ST\s*changes?[:\-\s]+(.+?)(?:\n|$)",
    ],
    "ecg_t_waves": [
        r"T\s*waves?[:\-\s]+(.+?)(?:\n|$)",
        r"T-waves?[:\-\s]+(.+?)(?:\n|$)",
    ],
    # Clinical
    "impression": [
        r"Impression[:\-\s]+(.+?)(?:\n\n|\nPlan|\nAssessment|$)",
        r"IMPRESSION[:\-\s]+(.+?)(?:\n\n|\nPLAN|$)",
        r"Diagnosis[:\-\s]+(.+?)(?:\n|$)",
    ],
    "indication": [
        r"Indication\s*(?:for\s*ECG)?[:\-\s]+(.+?)(?:\n|$)",
        r"Reason\s*for\s*(?:ECG|referral)[:\-\s]+(.+?)(?:\n|$)",
    ],
    "doc_date": [
        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s+\d{2}:\d{2}",
        r"Date[:\-\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    ],
}


# ─────────────────────────────────────────
# PLAN EXTRACTION
# ─────────────────────────────────────────

def extract_plan(text):
    """Extract numbered plan items from clinical text."""
    plan_match = re.search(
        r"Plan[:\-]?\s*\n((?:\d+[\)\.]\s*.+\n?)+)",
        text, re.IGNORECASE
    )
    if plan_match:
        return plan_match.group(1).strip()

    # Try bullet list
    plan_match = re.search(
        r"Plan[:\-]?\s*\n((?:[-•]\s*.+\n?)+)",
        text, re.IGNORECASE
    )
    if plan_match:
        return plan_match.group(1).strip()

    return ""


# ─────────────────────────────────────────
# GENDER INFERENCE FROM TEXT
# ─────────────────────────────────────────

def infer_gender(text):
    lower = text.lower()
    he_count = len(re.findall(r"\b(he|his|him|male)\b", lower))
    she_count = len(re.findall(r"\b(she|her|hers|female)\b", lower))
    if she_count > he_count:
        return "Female"
    if he_count > she_count:
        return "Male"
    return ""


# ─────────────────────────────────────────
# NORMALISE DATE
# ─────────────────────────────────────────

def normalise_date(raw):
    if not raw:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw.strip()


# ─────────────────────────────────────────
# MAIN EXTRACTOR
# ─────────────────────────────────────────

def extract_fields(raw_text):
    """
    Extract all structured fields from raw OCR text.
    Returns a dict of field_name → value.
    """
    fields = {}

    for field, patterns in PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            if match:
                fields[field] = match.group(1).strip()
                break

    # Post-process dates
    for date_field in ("dob", "ecg_date", "doc_date"):
        if date_field in fields:
            fields[date_field] = normalise_date(fields[date_field])

    # Gender fallback
    if "gender" not in fields or not fields["gender"]:
        fields["gender"] = infer_gender(raw_text)

    # Normalise gender abbreviations
    g = fields.get("gender", "")
    if g.upper() == "M":
        fields["gender"] = "Male"
    elif g.upper() == "F":
        fields["gender"] = "Female"

    # Extract plan
    plan = extract_plan(raw_text)
    if plan:
        fields["plan_notes"] = plan

    # Clean ECG rhythm (remove trailing dash/newline artefacts)
    if "ecg_rhythm" in fields:
        fields["ecg_rhythm"] = re.sub(r"[-\s]+$", "", fields["ecg_rhythm"]).strip()

    # Clean impression (may span multiple lines)
    if "impression" in fields:
        fields["impression"] = re.sub(r"\s+", " ", fields["impression"]).strip()

    return fields


# ─────────────────────────────────────────
# SPACY NER (optional enhancement)
# ─────────────────────────────────────────

def enhance_with_spacy(raw_text, fields):
    """Use spaCy NER to pick up names/dates missed by regex (optional)."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(raw_text)
        if not fields.get("patient_name"):
            persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if persons:
                fields["patient_name"] = persons[0]
        if not fields.get("doc_date"):
            dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
            if dates:
                fields["doc_date"] = dates[0]
    except Exception:
        pass  # spaCy not available — regex fields are enough
    return fields
