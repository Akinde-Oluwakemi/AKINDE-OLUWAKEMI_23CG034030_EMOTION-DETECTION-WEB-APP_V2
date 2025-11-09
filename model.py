# model.py (updated v2) - includes annotate_image_on_disk
import numpy as np
from deepface import DeepFace
from PIL import Image, ImageDraw, ImageFont
import io
import logging
import os

logger = logging.getLogger('emotion_model_v2')
logger.setLevel(logging.INFO)

def _normalize_result(result):
    if isinstance(result, list):
        chosen = None
        max_area = -1
        for r in result:
            reg = r.get('region', {})
            if reg and all(k in reg for k in ('w','h')):
                area = reg.get('w',0) * reg.get('h',0)
                if area > max_area:
                    max_area = area
                    chosen = r
            else:
                if chosen is None:
                    chosen = r
        result = chosen or result[0]

    dominant = result.get('dominant_emotion') or result.get('dominant_emotion', 'unknown')
    emotions = result.get('emotion', {})
    emotions_clean = {k: float(v) for k, v in emotions.items()} if isinstance(emotions, dict) else {}
    return {'dominant_emotion': dominant, 'emotion': emotions_clean}

def analyze_image(image_path):
    try:
        result = DeepFace.analyze(img_path=image_path, actions=['emotion'])
        return _normalize_result(result)
    except Exception as e:
        logger.exception('DeepFace analyze_image failed: %s', e)
        raise

def analyze_image_bytes(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        arr = np.array(img)
        result = DeepFace.analyze(img_path=arr, actions=['emotion'])
        return _normalize_result(result)
    except Exception as e:
        logger.exception('DeepFace analyze_image_bytes failed: %s', e)
        raise

def annotate_image_on_disk(image_path, dominant_emotion):
    """Draws a small label at the top-left of the image with the dominant emotion.
    Returns the new filename (saved in same folder with suffix _annotated.png).
    """
    try:
        img = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(img)
        # load a default truetype font; fallback to PIL default if not available
        try:
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', size=max(18, img.size[0]//20))
        except Exception:
            font = ImageFont.load_default()

        text = f"Emotion: {dominant_emotion}"
        padding = 8
        text_size = draw.textsize(text, font=font)
        rect_w = text_size[0] + padding*2
        rect_h = text_size[1] + padding*2

        # semi-transparent rectangle
        rectangle_color = (0, 0, 0, 180)
        # create overlay if image has alpha else draw directly
        if img.mode != 'RGBA':
            overlay = Image.new('RGBA', img.size, (255,255,255,0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([0, 0, rect_w, rect_h], fill=rectangle_color)
            overlay_draw.text((padding, padding), text, fill=(255,255,255,255), font=font)
            combined = Image.alpha_composite(img.convert('RGBA'), overlay)
            final = combined.convert('RGB')
        else:
            draw.rectangle([0, 0, rect_w, rect_h], fill=rectangle_color)
            draw.text((padding, padding), text, fill=(255,255,255), font=font)
            final = img

        base, ext = os.path.splitext(image_path)
        annotated_path = f"{base}_annotated.png"
        final.save(annotated_path)
        # return just the filename (relative path expected by Flask)
        return os.path.basename(annotated_path)
    except Exception as e:
        logger.exception('Failed to annotate image: %s', e)
        # if annotation fails, just return original filename
        return os.path.basename(image_path)
