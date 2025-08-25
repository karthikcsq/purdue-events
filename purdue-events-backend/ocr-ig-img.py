import io
import requests
from typing import List, Dict

import easyocr
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import os

reader = easyocr.Reader(['en'])


def ocr_from_url(src_url: str) -> List[Dict]:
    """Download image from src_url and run OCR, return list of text blocks with confidence.

    Returns list of dicts: {'text': str, 'confidence': float, 'bbox': [x1,y1,x2,y2]}.
    """
    resp = requests.get(src_url, stream=True, timeout=15)
    resp.raise_for_status()

    img_bytes = resp.content
    image = Image.open(io.BytesIO(img_bytes)).convert('RGB')

    # convert PIL Image to numpy array (EasyOCR accepts numpy arrays or bytes)
    np_image = np.array(image)

    # EasyOCR returns list of [bbox, text, confidence]
    results = reader.readtext(np_image)

    formatted = []
    for bbox, text, conf in results:
        formatted.append({
            'text': text,
            'confidence': float(conf),
            'bbox': [float(b) for point in bbox for b in point],
        })

    return formatted


def annotate_image(pil_image: Image.Image, results: List[Dict], min_confidence: float = 0.0) -> Image.Image:
    """Draw bounding boxes and confidence/text on a PIL image for OCR results.

    - pil_image: source PIL.Image (RGB)
    - results: list of dicts with 'text','confidence','bbox' (flat 8 values)
    - min_confidence: only draw results with confidence >= this
    Returns a new PIL.Image with annotations.
    """
    image = pil_image.copy()
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for r in results:
        conf = r.get('confidence', 0.0)
        if conf < min_confidence:
            continue
        bbox = r.get('bbox', [])
        if not bbox or len(bbox) < 4:
            continue
        # bbox is [x1,y1,x2,y2,x3,y3,x4,y4]
        xs = bbox[0::2]
        ys = bbox[1::2]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        # draw rectangle
        draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=2)
        text = r.get('text', '')
        label = f"{conf:.2f} {text}"
        text_pos = (x0, max(0, y0 - 12))
        # draw background for readability - compute text size with fallbacks
        if font:
            bbox_txt = draw.textbbox((0, 0), label, font=font)
        else:
            bbox_txt = draw.textbbox((0, 0), label)
        text_size = (bbox_txt[2] - bbox_txt[0], bbox_txt[3] - bbox_txt[1])

        rect_bg = [text_pos[0], text_pos[1], text_pos[0] + text_size[0] + 4, text_pos[1] + text_size[1] + 2]
        draw.rectangle(rect_bg, fill=(255, 255, 255))
        draw.text((text_pos[0] + 2, text_pos[1] + 1), label, fill=(0, 0, 0), font=font)

    return image


def display_ocr_results_from_url(src_url: str, min_confidence: float = 0.0, out_path: str = None) -> str:
    """Download image, run OCR, annotate and either show or save the annotated image.

    Returns path to saved annotated image.
    """
    resp = requests.get(src_url, stream=True, timeout=15)
    resp.raise_for_status()
    img_bytes = resp.content
    pil_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')

    results = ocr_from_url(src_url)
    annotated = annotate_image(pil_image, results, min_confidence=min_confidence)

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        out_path = tmp.name
        tmp.close()

    annotated.save(out_path)
    # attempt to open with default viewer
    try:
        annotated.show()
    except Exception:
        pass

    return out_path


if __name__ == '__main__':
    # quick manual test; replace with a real URL
    TEST_URL = 'https://instagram.find2-1.fna.fbcdn.net/v/t51.2885-15/536822350_18284345179282522_6279552119284829720_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=instagram.find2-1.fna.fbcdn.net&_nc_cat=110&_nc_oc=Q6cZ2QHyDjqClQMWHVo8k8p03DBCvzaXP9T2nLnJV0zXN3a54yU5zhQlqITTFVJvFvPkbnI&_nc_ohc=4nTfKkBVlcsQ7kNvwEIix5P&_nc_gid=hm-snKPtBhxueNLJ8_Uhpw&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfVfY8_4ywQHu7ynPeqtcTpKnQi49WXalG9hvH8tRypfsw&oe=68B2AAA1&_nc_sid=8b3546'
    if TEST_URL:
        print(ocr_from_url(TEST_URL))
        path = display_ocr_results_from_url(TEST_URL, min_confidence=0.3)
        print('Annotated image saved to', path)
