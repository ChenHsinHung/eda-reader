"""
Utility functions for elearning-bot
Includes logging, OCR, image processing, and other helpers
"""

import os
import logging
import logging.handlers
from datetime import datetime
from PIL import Image
import pytesseract
import requests
from config import *


def setup_logging():
    """Setup logging configuration"""
    log_dir = os.path.join(CREDENTIALS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"elearning_{datetime.now().strftime('%Y-%m-%d')}.log"
    log_path = os.path.join(log_dir, log_filename)

    # Create logger
    logger = logging.getLogger('elearning_bot')
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def preprocess_image_for_ocr(image_path):
    """Preprocess image for better OCR results"""
    try:
        # Open image
        img = Image.open(image_path)

        # Convert to grayscale
        img = img.convert('L')

        # Increase contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Resize if too small
        width, height = img.size
        if width < 100 or height < 50:
            img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)

        # Save processed image
        processed_path = image_path.replace('.png', '_processed.png')
        img.save(processed_path)

        return processed_path
    except Exception as e:
        logger = logging.getLogger('elearning_bot')
        logger.error(f"Image preprocessing failed: {e}")
        return image_path


def recognize_captcha(image_path):
    """Recognize captcha using Tesseract OCR"""
    try:
        # Set Tesseract path on all platforms
        # Windows: C:\Program Files\Tesseract-OCR\tesseract.exe
        # macOS: /usr/local/bin/tesseract or /opt/homebrew/bin/tesseract (M1/M2)
        # Linux: /usr/bin/tesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

        # Preprocess image
        processed_image = preprocess_image_for_ocr(image_path)

        # Perform OCR
        text = pytesseract.image_to_string(
            processed_image,
            config='--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        )

        # Clean up
        text = ''.join(c for c in text if c.isalnum()).upper()

        # Get confidence (if available)
        confidence = 0
        try:
            data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            if confidences:
                confidence = sum(confidences) / len(confidences)
        except:
            pass

        # Clean up processed image
        try:
            os.remove(processed_image)
        except:
            pass

        logger = logging.getLogger('elearning_bot')
        logger.debug(f"OCR result: '{text}' (confidence: {confidence}%)")

        return text, confidence

    except Exception as e:
        logger = logging.getLogger('elearning_bot')
        logger.error(f"OCR recognition failed: {e}")
        return "", 0


def download_image(url, save_path, headers=None):
    """Download image from URL"""
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)

        return True
    except Exception as e:
        logger = logging.getLogger('elearning_bot')
        logger.error(f"Image download failed: {e}")
        return False


def retry_with_backoff(func, max_attempts=RETRY_ATTEMPTS, initial_delay=RETRY_DELAY):
    """Retry function with exponential backoff"""
    import time

    logger = logging.getLogger('elearning_bot')

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                logger.error(f"Function failed after {max_attempts} attempts: {e}")
                raise e

            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds: {e}")
            time.sleep(delay)


def safe_get_text(element, default=""):
    """Safely get text from Selenium element"""
    try:
        return element.text.strip()
    except:
        return default


def safe_get_attribute(element, attribute, default=""):
    """Safely get attribute from Selenium element"""
    try:
        return element.get_attribute(attribute) or default
    except:
        return default


def wait_for_element(driver, by, value, timeout=BROWSER_WAIT_TIMEOUT):
    """Wait for element to be present"""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception as e:
        logger = logging.getLogger('elearning_bot')
        logger.error(f"Element not found: {by}={value}, timeout: {timeout}s")
        raise e


def wait_for_element_clickable(driver, by, value, timeout=BROWSER_WAIT_TIMEOUT):
    """Wait for element to be clickable"""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    except Exception as e:
        logger = logging.getLogger('elearning_bot')
        logger.error(f"Element not clickable: {by}={value}, timeout: {timeout}s")
        raise e