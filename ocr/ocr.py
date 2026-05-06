import os
import sys

os.environ['FLAGS_use_onednn'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

import cv2 as cv
from paddleocr import PaddleOCR

def main():
    img_path = "ecg sample G.jpg"
    
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return
    
    ocr = PaddleOCR(use_textline_orientation=True, lang='en', enable_mkldnn=False)
    
    img = cv.imread(img_path)
    
    result = ocr.ocr(img, cls=True)

    if result and result[0]:
        print("\n--- OCR RESULTS ---")
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            print(f"Text: {text} | Confidence: {confidence:.2f}")
    else:
        print("No text detected.")

if __name__ == "__main__":
    main()
