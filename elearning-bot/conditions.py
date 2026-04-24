"""
Condition extraction module
Dynamically extracts completion conditions from course pages
"""

import re
import logging
from typing import Dict, List, Any
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from utils import *


class ConditionExtractor:
    """Extracts completion conditions from course pages"""

    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger('elearning_bot')

    def extract_conditions(self, course_url: str) -> Dict[str, Any]:
        """Extract completion conditions from course page"""
        try:
            self.logger.info(f"Extracting conditions from: {course_url}")

            # Navigate to course page
            self.driver.get(course_url)
            wait_for_element(self.driver, By.CLASS_NAME, "course-content")

            # Get page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Extract conditions using multiple methods
            conditions = {}

            # Method 1: Look for explicit condition text
            conditions.update(self._extract_from_text(page_text))

            # Method 2: Look for structured data (tables, lists)
            conditions.update(self._extract_from_structure())

            # Method 3: Look for progress indicators
            conditions.update(self._extract_from_progress())

            # Validate and normalize conditions
            conditions = self._normalize_conditions(conditions)

            self.logger.info(f"Extracted conditions: {conditions}")
            return conditions

        except Exception as e:
            self.logger.error(f"Failed to extract conditions: {e}")
            # Return default conditions if extraction fails
            return self._get_default_conditions()

    def _extract_from_text(self, page_text: str) -> Dict[str, Any]:
        """Extract conditions from page text using regex patterns"""
        conditions = {}

        # Video completion patterns
        video_patterns = [
            r'視頻.*?(?:觀看|播放).*?(\d+)%',
            r'影片.*?(?:觀看|播放).*?(\d+)%',
            r'視頻完成度.*?(\d+)%',
            r'播放進度.*?(\d+)%'
        ]

        for pattern in video_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                percentage = int(match.group(1))
                conditions['video_completion'] = percentage / 100.0
                break

        # Quiz score patterns
        quiz_patterns = [
            r'測驗.*?(?:分數|成績).*?(\d+)分',
            r'考試.*?(?:分數|成績).*?(\d+)分',
            r'及格分數.*?(\d+)分',
            r'通過標準.*?(\d+)分'
        ]

        for pattern in quiz_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                conditions['quiz_min_score'] = score
                break

        # Discussion requirements
        if re.search(r'討論區|討論|發言|回覆', page_text, re.IGNORECASE):
            conditions['discussion_required'] = True

        # Assignment requirements
        if re.search(r'作業|任務|練習|實作', page_text, re.IGNORECASE):
            conditions['assignment_required'] = True

        return conditions

    def _extract_from_structure(self) -> Dict[str, Any]:
        """Extract conditions from page structure (tables, lists)"""
        conditions = {}

        try:
            # Look for condition tables
            condition_tables = self.driver.find_elements(
                By.CSS_SELECTOR,
                "table[class*='condition'], .completion-requirements, .course-requirements"
            )

            for table in condition_tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        label = safe_get_text(cells[0]).lower()
                        value = safe_get_text(cells[1])

                        # Parse video completion
                        if '視頻' in label or '影片' in label or '播放' in label:
                            match = re.search(r'(\d+)%', value)
                            if match:
                                conditions['video_completion'] = int(match.group(1)) / 100.0

                        # Parse quiz score
                        elif '測驗' in label or '考試' in label or '分數' in label:
                            match = re.search(r'(\d+)分', value)
                            if match:
                                conditions['quiz_min_score'] = int(match.group(1))

        except Exception as e:
            self.logger.debug(f"Structure extraction failed: {e}")

        return conditions

    def _extract_from_progress(self) -> Dict[str, Any]:
        """Extract conditions from progress indicators"""
        conditions = {}

        try:
            # Look for progress bars or completion indicators
            progress_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".progress, .completion-bar, [class*='progress']"
            )

            for element in progress_elements:
                progress_text = safe_get_text(element)
                match = re.search(r'(\d+)%', progress_text)
                if match:
                    percentage = int(match.group(1)) / 100.0
                    if 'video' not in conditions:
                        conditions['video_completion'] = percentage

        except Exception as e:
            self.logger.debug(f"Progress extraction failed: {e}")

        return conditions

    def _normalize_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate extracted conditions"""
        normalized = {}

        # Video completion (default 90%)
        video_completion = conditions.get('video_completion', 0.9)
        normalized['video_completion'] = max(0.1, min(1.0, video_completion))

        # Quiz minimum score (default 60)
        quiz_score = conditions.get('quiz_min_score', 60)
        normalized['quiz_min_score'] = max(0, min(100, quiz_score))

        # Discussion requirement (default False)
        normalized['discussion_required'] = conditions.get('discussion_required', False)

        # Assignment requirement (default False)
        normalized['assignment_required'] = conditions.get('assignment_required', False)

        return normalized

    def _get_default_conditions(self) -> Dict[str, Any]:
        """Get default conditions when extraction fails"""
        return {
            'video_completion': 0.9,  # 90%
            'quiz_min_score': 60,     # 60 points
            'discussion_required': False,
            'assignment_required': False
        }

    def check_condition_progress(self, conditions: Dict[str, Any], current_progress: Dict[str, Any]) -> Dict[str, bool]:
        """Check if current progress meets conditions"""
        results = {}

        # Video completion check
        video_progress = current_progress.get('video_progress', 0)
        required_video = conditions.get('video_completion', 0.9)
        results['video_completed'] = video_progress >= required_video

        # Quiz score check
        quiz_score = current_progress.get('quiz_score', 0)
        required_score = conditions.get('quiz_min_score', 60)
        results['quiz_passed'] = quiz_score >= required_score

        # Discussion check
        discussion_done = current_progress.get('discussion_completed', False)
        discussion_required = conditions.get('discussion_required', False)
        results['discussion_completed'] = not discussion_required or discussion_done

        # Assignment check
        assignment_done = current_progress.get('assignment_completed', False)
        assignment_required = conditions.get('assignment_required', False)
        results['assignment_completed'] = not assignment_required or assignment_done

        return results

    def are_all_conditions_met(self, condition_results: Dict[str, bool]) -> bool:
        """Check if all conditions are met"""
        return all(condition_results.values())