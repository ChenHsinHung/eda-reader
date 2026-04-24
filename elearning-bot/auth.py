"""
Authentication module for elearning.taipei
Handles login, captcha recognition, and session management
"""

import os
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging

from config import *
from utils import *
from encryption import get_credential_manager


class AuthManager:
    """Manages authentication with elearning.taipei"""

    def __init__(self):
        self.logger = logging.getLogger('elearning_bot')
        self.driver = None
        self.temp_dir = tempfile.mkdtemp()

    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()

        if ENABLE_HEADLESS:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        # Common options for stability
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Speed up loading
        chrome_options.add_argument("--disable-javascript")  # Will enable selectively
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Set window size for headless mode
        chrome_options.add_argument("--window-size=1920,1080")

        # Setup service
        service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(BROWSER_IMPLICIT_WAIT)

        self.logger.info("WebDriver initialized successfully")

    def _get_captcha_image(self):
        """Download captcha image"""
        try:
            # Find captcha image element
            captcha_img = wait_for_element(
                self.driver,
                By.CSS_SELECTOR,
                "img[src*='captcha']"
            )

            captcha_url = captcha_img.get_attribute("src")
            if not captcha_url:
                raise ValueError("Captcha image URL not found")

            # Download image
            captcha_path = os.path.join(self.temp_dir, "captcha.png")
            if not download_image(captcha_url, captcha_path):
                raise ValueError("Failed to download captcha image")

            return captcha_path

        except Exception as e:
            self.logger.error(f"Failed to get captcha image: {e}")
            raise

    def _recognize_captcha(self, image_path):
        """Recognize captcha with OCR"""
        text, confidence = recognize_captcha(image_path)

        if not text or len(text) < 4:
            raise ValueError("Captcha recognition failed - empty or too short result")

        if confidence < 50:
            self.logger.warning(f"Low OCR confidence: {confidence}%")

        return text

    def _fill_login_form(self, account_id, password, captcha_text):
        """Fill login form with credentials"""
        try:
            # Wait for form to load
            wait_for_element(self.driver, By.ID, "login-form")

            # Fill account ID
            id_field = wait_for_element(self.driver, By.NAME, "id_no")
            id_field.clear()
            id_field.send_keys(account_id)

            # Fill password
            password_field = wait_for_element(self.driver, By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)

            # Fill captcha
            captcha_field = wait_for_element(self.driver, By.NAME, "captcha")
            captcha_field.clear()
            captcha_field.send_keys(captcha_text)

            self.logger.debug("Login form filled successfully")

        except Exception as e:
            self.logger.error(f"Failed to fill login form: {e}")
            raise

    def _submit_login(self):
        """Submit login form and check result"""
        try:
            # Find and click login button
            login_button = wait_for_element_clickable(
                self.driver,
                By.CSS_SELECTOR,
                "button[type='submit'], input[type='submit']"
            )
            login_button.click()

            # Wait for redirect or error message
            time.sleep(3)

            # Check for error messages
            error_selectors = [
                ".error-message",
                ".alert-danger",
                "[class*='error']",
                "[id*='error']"
            ]

            for selector in error_selectors:
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    error_text = safe_get_text(error_element)
                    if error_text and "錯誤" in error_text or "失敗" in error_text:
                        raise ValueError(f"Login failed: {error_text}")
                except NoSuchElementException:
                    continue

            # Check if redirected to main page
            current_url = self.driver.current_url
            if "login" in current_url.lower():
                raise ValueError("Still on login page - login may have failed")

            self.logger.info("Login successful")
            return True

        except Exception as e:
            self.logger.error(f"Login submission failed: {e}")
            raise

    def login(self, max_attempts=3):
        """Main login function with retry logic"""
        if not self.driver:
            self._setup_driver()

        # Load credentials
        try:
            manager = get_credential_manager()
            account_id, password = manager.load_credentials()
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise

        # Login attempts
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Login attempt {attempt + 1}/{max_attempts}")

                # Navigate to login page
                self.driver.get("https://elearning.taipei/mpage/login")

                # Get and recognize captcha
                captcha_path = self._get_captcha_image()
                captcha_text = self._recognize_captcha(captcha_path)

                # Fill and submit form
                self._fill_login_form(account_id, password, captcha_text)
                self._submit_login()

                return True

            except Exception as e:
                self.logger.warning(f"Login attempt {attempt + 1} failed: {e}")

                if attempt < max_attempts - 1:
                    # Wait before retry (exponential backoff)
                    wait_time = 10 * (2 ** attempt)
                    self.logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    self.logger.error("All login attempts failed")
                    raise

        return False

    def is_logged_in(self):
        """Check if user is logged in"""
        try:
            # Check for logout button or user menu
            logout_indicators = [
                "a[href*='logout']",
                "a[href*='signout']",
                ".user-menu",
                ".logout"
            ]

            for selector in logout_indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    return True
                except NoSuchElementException:
                    continue

            return False
        except:
            return False

    def logout(self):
        """Logout from the system"""
        try:
            # Find and click logout link
            logout_selectors = [
                "a[href*='logout']",
                "a[href*='signout']",
                ".logout"
            ]

            for selector in logout_selectors:
                try:
                    logout_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logout_link.click()
                    time.sleep(2)
                    self.logger.info("Logged out successfully")
                    return True
                except NoSuchElementException:
                    continue

            self.logger.warning("Logout link not found")
            return False

        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return False

    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver cleaned up")
            except:
                pass

        # Clean up temp files
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass