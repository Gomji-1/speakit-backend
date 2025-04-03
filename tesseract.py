import os
import io
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import logging
import hashlib
from tempfile import NamedTemporaryFile

# Critical memory optimization
os.environ['OMP_THREAD_LIMIT'] = '1'  # Single thread for Tesseract
os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/4.00/tessdata/'

# Enhanced performance presets with language-specific optimizations
LANGUAGE_PRESETS = {
    'english': {
        'config': '--psm 6 --oem 1 -c preserve_interword_spaces=1',
        'resize_factor': 1.1,
        'contrast': 1.2,
        'sharpness': 1.1
    },
    'general': {
        'config': '--psm 6 --oem 1',
        'resize_factor': 1.0,
        'contrast': 1.1,
        'sharpness': 1.0
    },
    'document': {
        'config': '--psm 3 --oem 1',
        'resize_factor': 1.0,
        'contrast': 1.3,
        'sharpness': 1.2
    }
}

def get_cache_key(image_bytes: bytes, lang: str, preset: str) -> str:
    """Generate consistent cache key for processed images"""
    return hashlib.md5(image_bytes + lang.encode() + preset.encode()).hexdigest()

def optimize_image(image_bytes: bytes, preset: str = 'general') -> bytes:
    """
    Enhanced image optimization pipeline with:
    - Memory-efficient processing
    - Adaptive quality adjustments
    - Smart fallback mechanisms
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            preset_data = LANGUAGE_PRESETS.get(preset, LANGUAGE_PRESETS['general'])
            
            # Convert to grayscale first (uses less memory)
            img = img.convert('L')
            
            # Adaptive resizing only for large images
            if max(img.size) > 1600:
                new_size = (
                    int(img.width * min(preset_data['resize_factor'], 1.2)),
                    int(img.height * min(preset_data['resize_factor'], 1.2))
                )
                img = img.resize(new_size, Image.BILINEAR)
            
            # Enhanced preprocessing pipeline
            img = ImageOps.autocontrast(img, cutoff=1.0)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(preset_data['contrast'])
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(preset_data['sharpness'])
            
            # Optimized JPEG output with quality scaling
            output = io.BytesIO()
            quality = 80 if max(img.size) > 1200 else 85
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
            
    except Exception as e:
        logging.warning(f"Image optimization failed, using original: {str(e)}")
        return image_bytes

def extract_text(image_bytes: bytes, lang: str = 'eng', preset: str = 'general') -> str:
    """
    Robust text extraction with:
    - Memory safety guards
    - Adaptive fallbacks
    - Comprehensive error handling
    """
    # Cache processed images in temp files to reduce memory pressure
    cache_key = get_cache_key(image_bytes, lang, preset)
    temp_file = NamedTemporaryFile(delete=False, suffix='.jpg')
    
    try:
        # Optimize and cache the image
        optimized_img = optimize_image(image_bytes, preset)
        with open(temp_file.name, 'wb') as f:
            f.write(optimized_img)
        
        # Get appropriate config
        preset_config = LANGUAGE_PRESETS.get(preset, LANGUAGE_PRESETS['general'])
        
        # Progressive processing with fallbacks
        for attempt in range(2):
            try:
                return pytesseract.image_to_string(
                    Image.open(temp_file.name),
                    lang=lang,
                    config=preset_config['config']
                )
            except RuntimeError as e:
                if attempt == 0 and 'memory' in str(e).lower():
                    logging.warning("Memory limit hit, retrying with simpler config")
                    preset_config['config'] = '--psm 6 --oem 1'  # Fallback config
                    continue
                raise
        
    except Exception as e:
        logging.error(f"OCR extraction failed: {str(e)}")
        raise
    finally:
        try:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        except Exception as e:
            logging.warning(f"Failed to cleanup temp file: {str(e)}")

# Preload Tesseract to reduce first-request latency
try:
    pytesseract.get_tesseract_version()
except Exception as e:
    logging.warning(f"Tesseract initialization check failed: {str(e)}")