"""
modules/ocr_nlp/ocr_engine.py

OCR text extraction from images and PDFs.
Tries PaddleOCR first (high accuracy), falls back to pytesseract.
"""

import os
import sys

def _try_paddle(image_path):
    """Attempt OCR using PaddleOCR."""
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang="en", show_log=False)
        result = ocr.predict(image_path)
        lines = []
        for page in result:
            for text in page.get("rec_texts", []):
                if text.strip():
                    lines.append(text.strip())
        return "\n".join(lines), "PaddleOCR"
    except Exception as e:
        return None, str(e)


def _try_tesseract(image_path):
    """Attempt OCR using pytesseract."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(image_path)
        # Tesseract config for medical documents
        custom_cfg = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_cfg)
        return text.strip(), "pytesseract"
    except Exception as e:
        return None, str(e)


def _try_easyocr(image_path):
    """Attempt OCR using EasyOCR."""
    try:
        import easyocr
        reader = easyocr.Reader(["en"], verbose=False)
        result = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(result), "EasyOCR"
    except Exception as e:
        return None, str(e)


def extract_text_from_image(image_path):
    """
    Extract text from an image file.
    Returns (text, engine_used, error_message).
    Tries PaddleOCR → EasyOCR → pytesseract in order.
    """
    if not os.path.exists(image_path):
        return "", None, f"File not found: {image_path}"

    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(image_path)

    # Try engines in order
    for fn, name in [(_try_paddle, "PaddleOCR"), (_try_easyocr, "EasyOCR"), (_try_tesseract, "pytesseract")]:
        text, info = fn(image_path)
        if text and len(text.strip()) > 20:
            return text, name, None

    return "", None, "No OCR engine available. Install paddleocr, easyocr, or pytesseract."


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF — tries text layer first, then renders pages to images."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        all_text = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                all_text.append(text)
            else:
                # Scanned page — render and OCR
                pix = page.get_pixmap(dpi=300)
                tmp_path = pdf_path + f"_page{page.number}.png"
                pix.save(tmp_path)
                page_text, _, _ = extract_text_from_image(tmp_path)
                all_text.append(page_text)
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        doc.close()
        return "\n\n".join(all_text), "PyMuPDF+OCR", None
    except ImportError:
        pass
    except Exception as e:
        return "", None, f"PDF error: {e}"

    # Fallback: convert first page with pdf2image
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
        if images:
            tmp_path = pdf_path + "_p1.png"
            images[0].save(tmp_path, "PNG")
            text, engine, err = extract_text_from_image(tmp_path)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return text, engine, err
    except Exception as e:
        return "", None, f"PDF fallback error: {e}"

    return "", None, "Cannot process PDF: install PyMuPDF or pdf2image."


def preprocess_image(image_path):
    """
    Optional preprocessing to improve OCR accuracy on medical documents.
    Returns path to preprocessed image (or original if OpenCV not available).
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return image_path

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive threshold for handwritten text
        thresh = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 10
        )

        # Deskew (find rotation angle)
        coords = np.column_stack(np.where(thresh < 127))
        if len(coords) > 10:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:
                (h, w) = thresh.shape
                M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
                thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        out_path = image_path.rsplit(".", 1)[0] + "_preprocessed.png"
        cv2.imwrite(out_path, thresh)
        return out_path

    except Exception:
        return image_path  # Return original if preprocessing fails
