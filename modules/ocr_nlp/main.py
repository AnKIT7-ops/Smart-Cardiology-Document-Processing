import os
import re
import cv2 as cv
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from paddleocr import PaddleOCR


@dataclass
class UploadMeta:
    """Metadata supplied by the user on the Upload page."""
    upload_id: str
    patient_id: str
    file_type: str         
    document_type: str      
    upload_date: str        
    center_id: str
    technician_name: str
    file_path: str


@dataclass
class ExtractedData:
    """All fields shown on the Extracted Data View page."""
    patient_name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    ecg_date: Optional[str] = None

    heart_rate: Optional[str] = None
    pr_interval: Optional[str] = None
    qrs_duration: Optional[str] = None
    qt_interval: Optional[str] = None

    doctor_notes: Optional[str] = None
    diagnosis_text: Optional[str] = None

    confidence_score: float = 0.0

    raw_lines: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class OCRProcessor:
    """
    Wraps PaddleOCR.
    Call process(file_path) → list[tuple[str, float]]
    Each tuple is (text_line, confidence).
    """

    def __init__(self):
        self._ocr = PaddleOCR(
            use_textline_orientation=True,
            lang="en",
            enable_mkldnn=False,
        )

    def process(self, file_path: str) -> list[tuple[str, float]]:
        """
        Accepts an image path (jpg/png) or a PDF path.
        Returns a flat list of (text, confidence) tuples.
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._process_pdf(file_path)
        return self._process_image(file_path)


    def _process_image(self, path: str) -> list[tuple[str, float]]:
        img = cv.imread(path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        return self._run_ocr(img)

    def _process_pdf(self, path: str) -> list[tuple[str, float]]:
        """Convert PDF pages to images then OCR each page."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF (fitz) is required for PDF support. pip install pymupdf")

        doc = fitz.open(path)
        lines: list[tuple[str, float]] = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)           # 2× zoom → better OCR
            pix = page.get_pixmap(matrix=mat)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img_array.reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = cv.cvtColor(img, cv.COLOR_BGRA2BGR)
            lines.extend(self._run_ocr(img))
        return lines

    def _run_ocr(self, img: np.ndarray) -> list[tuple[str, float]]:
        # PaddleOCR v3.5+: .predict() returns list of OCRResult dicts
        # with keys 'rec_texts' (list[str]) and 'rec_scores' (list[float])
        result = self._ocr.predict(img)
        lines: list[tuple[str, float]] = []
        if not result:
            return lines
        for page in result:
            texts = page.get("rec_texts", [])
            scores = page.get("rec_scores", [])
            for text, conf in zip(texts, scores):
                text = text.strip()
                if text:
                    lines.append((text, float(conf)))
        return lines


class NLPExtractor:
    """
    Rule-based NLP extraction for ECG / medical documents.
    Parses a list of (text, confidence) lines → ExtractedData.

    Extend _PATTERNS to support more document layouts.
    """

    _PATTERNS: dict[str, list[re.Pattern]] = {
        "patient_name": [
            re.compile(r"(?:patient\s*name|name)\s*[:\-]?\s*([A-Za-z\s\.]+)", re.I),
            re.compile(r"^name\s*[:\-]\s*(.+)$", re.I | re.M),
        ],
        "age": [
            re.compile(r"(?:age)\s*[:\-]?\s*(\d{1,3})\s*(?:yrs?|years?)?", re.I),
            re.compile(r"(\d{1,3})\s*(?:yrs?|years?\s*old)", re.I),
        ],
        "gender": [
            re.compile(r"(?:gender|sex)\s*[:\-]?\s*(male|female|m|f)\b", re.I),
            re.compile(r"\b(male|female)\b", re.I),
        ],
        "ecg_date": [
            re.compile(r"(?:date|ecg\s*date|recorded)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", re.I),
            re.compile(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"),
        ],
        "heart_rate": [
            re.compile(r"(?:heart\s*rate|hr|ventricular\s*rate)\s*[:\-]?\s*(\d{2,3})\s*(?:bpm)?", re.I),
            re.compile(r"(\d{2,3})\s*bpm", re.I),
        ],
        "pr_interval": [
            re.compile(r"(?:pr\s*interval|pr)\s*[:\-]?\s*(\d{2,3})\s*(?:ms)?", re.I),
        ],
        "qrs_duration": [
            re.compile(r"(?:qrs\s*duration|qrs)\s*[:\-]?\s*(\d{2,3})\s*(?:ms)?", re.I),
        ],
        "qt_interval": [
            re.compile(r"(?:qt[c]?\s*interval|qt[c]?)\s*[:\-]?\s*(\d{2,3})\s*(?:ms)?", re.I),
        ],
    }

    _DIAGNOSIS_KEYWORDS = re.compile(
        r"\b(normal|abnormal|sinus|rhythm|tachycardia|bradycardia|flutter|"
        r"fibrillation|block|ischemia|infarction|hypertrophy|impression|"
        r"interpretation|conclusion|findings?|diagnosis|assessment)\b",
        re.I,
    )
    _NOTES_KEYWORDS = re.compile(
        r"\b(note|comment|remark|suggest|recommend|follow.?up|consult)\b",
        re.I,
    )


    def extract(self, ocr_lines: list[tuple[str, float]]) -> ExtractedData:
        """
        ocr_lines: output of OCRProcessor.process()
        Returns a fully populated ExtractedData.
        """
        full_text = "\n".join(t for t, _ in ocr_lines)
        avg_conf = (sum(c for _, c in ocr_lines) / len(ocr_lines) * 100) if ocr_lines else 0.0

        data = ExtractedData(
            confidence_score=round(avg_conf, 2),
            raw_lines=[{"text": t, "confidence": round(c, 4)} for t, c in ocr_lines],
        )

        for field_name, patterns in self._PATTERNS.items():
            value = self._match_first(full_text, patterns)
            if value:
                setattr(data, field_name, self._clean(value))

   
        diagnosis_lines, notes_lines = [], []
        for text, _ in ocr_lines:
            if self._DIAGNOSIS_KEYWORDS.search(text):
                diagnosis_lines.append(text)
            elif self._NOTES_KEYWORDS.search(text):
                notes_lines.append(text)

        if diagnosis_lines:
            data.diagnosis_text = " | ".join(diagnosis_lines)
        if notes_lines:
            data.doctor_notes = " | ".join(notes_lines)

        return data

 
    @staticmethod
    def _match_first(text: str, patterns: list[re.Pattern]) -> Optional[str]:
        for pat in patterns:
            m = pat.search(text)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _clean(value: str) -> str:
        return value.strip().title() if value else value


def run_pipeline(meta: UploadMeta) -> ExtractedData:
    """
    Full pipeline: OCR → NLP → ExtractedData.
    Called by ui.py and any external orchestrator.
    """
    ocr = OCRProcessor()
    nlp = NLPExtractor()

    print(f"[OCR] Processing: {meta.file_path}")
    lines = ocr.process(meta.file_path)
    print(f"[OCR] Detected {len(lines)} text lines.")

    extracted = nlp.extract(lines)
    print(f"[NLP] Extraction complete. Confidence: {extracted.confidence_score:.1f}%")
    return extracted


if __name__ == "__main__":
    import sys

    img_path = sys.argv[1] if len(sys.argv) > 1 else "ecg sample G.jpg"

    meta = UploadMeta(
        upload_id="TEST-001",
        patient_id="P-001",
        file_type="Image",
        document_type="ECG",
        upload_date="2025-05-08",
        center_id="CTR-01",
        technician_name="Test Tech",
        file_path=img_path,
    )

    result = run_pipeline(meta)

    print("\n--- EXTRACTED DATA ---")
    for k, v in result.to_dict().items():
        if k != "raw_lines":
            print(f"  {k:20s}: {v}")
