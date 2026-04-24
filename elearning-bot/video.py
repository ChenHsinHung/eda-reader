"""
Video playback and progress monitoring module
Handles video player detection, playback control, and progress tracking
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, JavascriptException

from config import *
from utils import *


class VideoPlayer:
    """Handles video playback and monitoring"""

    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger('elearning_bot')
        self.video_element = None
        self.start_time = 0

    def find_video_element(self):
        """Find the video element on the page"""
        try:
            # Common video selectors
            video_selectors = [
                "video",
                ".video-player video",
                ".media-player video",
                "#video-player",
                "[class*='video'] video",
                "iframe[src*='video']",
                "iframe[src*='player']"
            ]

            for selector in video_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.tag_name.lower() == 'video' or 'iframe' in selector:
                        self.video_element = element
                        self.logger.info(f"Found video element: {selector}")
                        return True
                except NoSuchElementException:
                    continue

            # Try to find by playing button
            play_buttons = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[class*='play'], .play-button, [title*='播放']"
            )

            if play_buttons:
                self.logger.info("Found play button, assuming video is present")
                return True

            self.logger.warning("No video element found on page")
            return False

        except Exception as e:
            self.logger.error(f"Error finding video element: {e}")
            return False

    def start_playback(self):
        """Start video playback"""
        try:
            if not self.video_element:
                if not self.find_video_element():
                    raise ValueError("No video element available")

            # Try to click play button first
            play_selectors = [
                "button[class*='play']",
                ".play-button",
                "[title*='播放']",
                "[aria-label*='播放']"
            ]

            play_clicked = False
            for selector in play_selectors:
                try:
                    play_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if play_button.is_displayed() and play_button.is_enabled():
                        play_button.click()
                        self.logger.info("Clicked play button")
                        play_clicked = True
                        break
                except NoSuchElementException:
                    continue

            # If no play button found, try JavaScript
            if not play_clicked and self.video_element:
                try:
                    if self.video_element.tag_name.lower() == 'video':
                        self.driver.execute_script("arguments[0].play();", self.video_element)
                        self.logger.info("Started video with JavaScript")
                    else:
                        # For iframe players, might need different approach
                        self.logger.info("Iframe player detected, attempting playback")
                except JavascriptException as e:
                    self.logger.warning(f"JavaScript playback failed: {e}")

            # Set volume to 0 (mute)
            self._set_volume(0)

            self.start_time = time.time()
            self.logger.info("Video playback started")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start video playback: {e}")
            return False

    def _set_volume(self, volume=0):
        """Set video volume"""
        try:
            if self.video_element and self.video_element.tag_name.lower() == 'video':
                self.driver.execute_script(f"arguments[0].volume = {volume};", self.video_element)
                self.logger.debug(f"Video volume set to {volume}")
        except Exception as e:
            self.logger.debug(f"Failed to set volume: {e}")

    def get_progress(self):
        """Get current video progress (0.0 to 1.0)"""
        try:
            if not self.video_element or self.video_element.tag_name.lower() != 'video':
                return 0.0

            # Get current time and duration
            current_time = self.driver.execute_script("return arguments[0].currentTime;", self.video_element)
            duration = self.driver.execute_script("return arguments[0].duration;", self.video_element)

            if duration and duration > 0:
                progress = current_time / duration
                return min(1.0, max(0.0, progress))
            else:
                return 0.0

        except Exception as e:
            self.logger.debug(f"Failed to get video progress: {e}")
            return 0.0

    def is_playing(self):
        """Check if video is currently playing"""
        try:
            if not self.video_element or self.video_element.tag_name.lower() != 'video':
                return False

            # Check if video is paused
            paused = self.driver.execute_script("return arguments[0].paused;", self.video_element)
            return not paused

        except Exception as e:
            self.logger.debug(f"Failed to check if video is playing: {e}")
            return False

    def wait_for_completion(self, timeout=VIDEO_TIMEOUT):
        """Wait for video to complete playing"""
        start_time = time.time()
        last_progress = 0.0
        stagnant_time = 0

        self.logger.info(f"Waiting for video completion (timeout: {timeout}s)")

        while time.time() - start_time < timeout:
            try:
                current_progress = self.get_progress()

                # Check if completed
                if current_progress >= VIDEO_COMPLETION_THRESHOLD:
                    self.logger.info(f"Video completed: {current_progress:.1%}")
                    return True

                # Check for stagnation (video stuck)
                if abs(current_progress - last_progress) < 0.01:
                    stagnant_time += 1
                else:
                    stagnant_time = 0

                if stagnant_time > 30:  # 30 seconds of no progress
                    self.logger.warning("Video appears stuck, attempting to resume")
                    self._resume_playback()
                    stagnant_time = 0

                last_progress = current_progress

                # Log progress every 30 seconds
                if int(time.time() - start_time) % 30 == 0:
                    self.logger.debug(f"Video progress: {current_progress:.1%}")

                time.sleep(2)  # Check every 2 seconds

            except Exception as e:
                self.logger.warning(f"Error during video monitoring: {e}")
                time.sleep(5)

        self.logger.warning(f"Video completion timeout after {timeout} seconds")
        return False

    def _resume_playback(self):
        """Try to resume stuck video"""
        try:
            if self.video_element and self.video_element.tag_name.lower() == 'video':
                # Try to play again
                self.driver.execute_script("arguments[0].play();", self.video_element)
                self.logger.info("Attempted to resume video playback")
        except Exception as e:
            self.logger.debug(f"Failed to resume playback: {e}")

    def get_video_info(self):
        """Get video information"""
        info = {
            'duration': 0,
            'current_time': 0,
            'progress': 0.0,
            'is_playing': False
        }

        try:
            if self.video_element and self.video_element.tag_name.lower() == 'video':
                info['duration'] = self.driver.execute_script("return arguments[0].duration;", self.video_element) or 0
                info['current_time'] = self.driver.execute_script("return arguments[0].currentTime;", self.video_element) or 0
                info['is_playing'] = not (self.driver.execute_script("return arguments[0].paused;", self.video_element) or False)
                info['progress'] = info['current_time'] / info['duration'] if info['duration'] > 0 else 0.0
        except Exception as e:
            self.logger.debug(f"Failed to get video info: {e}")

        return info

    def stop_playback(self):
        """Stop video playback"""
        try:
            if self.video_element and self.video_element.tag_name.lower() == 'video':
                self.driver.execute_script("arguments[0].pause();", self.video_element)
                self.logger.info("Video playback stopped")
        except Exception as e:
            self.logger.debug(f"Failed to stop playback: {e}")

    def seek_to_position(self, position_ratio):
        """Seek to specific position in video (0.0 to 1.0)"""
        try:
            if self.video_element and self.video_element.tag_name.lower() == 'video':
                duration = self.driver.execute_script("return arguments[0].duration;", self.video_element)
                if duration:
                    seek_time = duration * position_ratio
                    self.driver.execute_script(f"arguments[0].currentTime = {seek_time};", self.video_element)
                    self.logger.debug(f"Seeked to {position_ratio:.1%} of video")
        except Exception as e:
            self.logger.debug(f"Failed to seek: {e}")