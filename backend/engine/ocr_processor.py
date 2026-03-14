# utils/ocr_processor.py — Local OCR processing using EasyOCR
import os
import io
import re
import sys
import logging
import numpy as np
from PIL import Image

# Fix for Windows terminal encoding issues (especially with EasyOCR/tqdm progress bars)
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (this will download models on first run)
_reader = None

def get_reader():
    """Lazy initialization of EasyOCR reader."""
    global _reader
    if _reader is None:
        try:
            import easyocr
            # Load English only, disable GPU if not needed or available
            logger.info("Initializing EasyOCR reader (this may take a moment on first run)...")
            _reader = easyocr.Reader(['en'], gpu=False) 
            logger.info("EasyOCR reader initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {e}")
    return _reader

def extract_text_from_image(image_bytes):
    """
    Extract text from image bytes using EasyOCR.
    Returns: list of {text, confidence, box}
    """
    reader = get_reader()
    if not reader:
        return []

    try:
        # Convert bytes to numpy array for EasyOCR
        img = Image.open(io.BytesIO(image_bytes))
        img_np = np.array(img)
        
        # Run OCR
        results = reader.readtext(img_np)
        
        extracted = []
        for (bbox, text, prob) in results:
            extracted.append({
                'text': text,
                'confidence': float(prob),
                'box': [[int(p[0]), int(p[1])] for p in bbox]
            })
            
        return extracted
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return []

def identify_number_plates(ocr_results):
    """
    Filter OCR results for strings that look like Indian vehicle number plates.
    Common formats: SS NN SS NNNN (e.g., TN 37 CB 1234)
    """
    plates = []
    
    # Pattern for Indian plates:
    # 2 chars (state), 2 digits (district), 1-2 chars (series), 4 digits (number)
    # Flexible pattern to catch variations and partial reads
    plate_pattern = re.compile(r'[A-Z]{2}\s*\d{1,2}\s*[A-Z]{0,3}\s*\d{1,4}', re.IGNORECASE)
    
    for item in ocr_results:
        text = item['text'].upper().replace(' ', '').replace('-', '').replace('.', '')
        # Basic heuristic: if it matches the pattern or has high confidence and correct length
        if plate_pattern.search(text) or (len(text) >= 6 and len(text) <= 12 and item['confidence'] > 0.5):
            # Clean up the text for better matching
            plates.append({
                'plate_text': text,
                'confidence': item['confidence'],
                'box': item['box']
            })
            
    return plates

def get_ocr_hint_for_prompt(ocr_results):
    """
    Format OCR results as a string hint for the AI model.
    """
    if not ocr_results:
        return ""
        
    plates = identify_number_plates(ocr_results)
    other_text = [item['text'] for item in ocr_results if item['confidence'] > 0.4]
    
    hint = "\n--- LOCAL OCR HINTS (TRUST THESE TEXTS) ---\n"
    if plates:
        hint += "DETECTED NUMBER PLATES: " + ", ".join([p['plate_text'] for p in plates]) + "\n"
    if other_text:
        hint += "OTHER VISIBLE TEXT: " + ", ".join(other_text[:10]) + "\n"
    hint += "-------------------------------------------\n"
    
    return hint
