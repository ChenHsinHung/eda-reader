"""
Course navigation module
Handles course listing, navigation, and progress tracking
"""

import time
import logging
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from config import *
from utils import *
from conditions import ConditionExtractor
from video import VideoPlayer
from quiz import QuizSolver


class CourseNavigator:
    """Handles course navigation and completion"""

    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger('elearning_bot')
        self.condition_extractor = ConditionExtractor(driver)
        self.video_player = VideoPlayer(driver)
        self.quiz_solver = QuizSolver(driver)

    def get_course_list(self):
        """Get list of available courses from learning record page"""
        try:
            self.logger.info("Fetching course list from learning record page")

            # Navigate to learning record page
            # Try common learning record URLs
            record_urls = [
                "https://elearning.taipei/mpage/learning_record",
                "https://elearning.taipei/mpage/my_learning",
                "https://elearning.taipei/mpage/progress",
                "https://elearning.taipei/mpage/my_courses"
            ]

            courses = []
            for url in record_urls:
                try:
                    self.driver.get(url)
                    time.sleep(2)  # Wait for page to load

                    # Check if we're on the right page by looking for course elements
                    course_elements = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        ".course-item, .course-card, .learning-item, [class*='course'], [class*='learning']"
                    )

                    if course_elements:
                        self.logger.info(f"Found courses on page: {url}")
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to load {url}: {e}")
                    continue
            else:
                # If no record page found, fall back to course list page
                self.logger.warning("No learning record page found, using course list page")
                self.driver.get("https://elearning.taipei/mpage/view_type_list")
                time.sleep(2)

            # Wait for courses to load
            wait_for_element(self.driver, By.CSS_SELECTOR, ".course-item, .course-card, .learning-item", timeout=10)

            # Find course elements (try multiple selectors)
            course_selectors = [
                ".course-item",
                ".course-card",
                ".learning-item",
                "[class*='course']",
                "[class*='learning']",
                "tr[class*='course']",  # Table rows
                ".list-item"
            ]

            course_elements = []
            for selector in course_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    course_elements = elements
                    self.logger.debug(f"Found {len(elements)} courses using selector: {selector}")
                    break

            for element in course_elements:
                course_data = self._parse_course_element(element)
                if course_data:
                    courses.append(course_data)

            self.logger.info(f"Found {len(courses)} courses from learning record")
            return courses

        except Exception as e:
            self.logger.error(f"Failed to get course list: {e}")
            return []

    def _parse_course_element(self, element):
        """Parse course information from element (supports both course list and learning record pages)"""
        try:
            # Get course title and link
            title_selectors = ["h3 a", ".title a", "a[href*='course']", "a[href*='learning']", "a"]
            title_element = None
            title = ""
            url = ""

            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    title = safe_get_text(title_element)
                    url = safe_get_attribute(title_element, "href")
                    if title and url:
                        break
                except NoSuchElementException:
                    continue

            if not title or not url:
                return None

            # Get course metadata
            metadata = {}

            # Try to get hours
            hours_selectors = ["[class*='hour']", "[class*='time']", "[class*='duration']", "td:nth-child(3)"]
            for selector in hours_selectors:
                try:
                    hours_element = element.find_element(By.CSS_SELECTOR, selector)
                    hours_text = safe_get_text(hours_element)
                    # Extract number from text like "認證時數: 2小時" or "2小時"
                    import re
                    match = re.search(r'(\d+)', hours_text)
                    if match:
                        metadata['hours'] = int(match.group(1))
                        break
                except NoSuchElementException:
                    continue

            # Check completion status (for learning record pages)
            status_selectors = ["[class*='status']", "[class*='progress']", ".badge", "td:nth-child(4)"]
            for selector in status_selectors:
                try:
                    status_element = element.find_element(By.CSS_SELECTOR, selector)
                    status_text = safe_get_text(status_element).lower()
                    if '完成' in status_text or 'completed' in status_text or 'finished' in status_text:
                        metadata['completed'] = True
                    elif '進行中' in status_text or 'in progress' in status_text or 'ongoing' in status_text:
                        metadata['completed'] = False
                        metadata['in_progress'] = True
                    else:
                        metadata['completed'] = False
                    break
                except NoSuchElementException:
                    continue

            # Check if has quiz
            quiz_selectors = ["[class*='quiz']", "[class*='test']", "[class*='exam']"]
            metadata['has_quiz'] = False
            for selector in quiz_selectors:
                try:
                    element.find_element(By.CSS_SELECTOR, selector)
                    metadata['has_quiz'] = True
                    break
                except NoSuchElementException:
                    continue

            # Get progress percentage if available
            progress_selectors = ["[class*='progress-bar']", ".progress", "[class*='percentage']"]
            for selector in progress_selectors:
                try:
                    progress_element = element.find_element(By.CSS_SELECTOR, selector)
                    progress_text = safe_get_text(progress_element)
                    match = re.search(r'(\d+)%', progress_text)
                    if match:
                        metadata['progress'] = int(match.group(1)) / 100.0
                        break
                except NoSuchElementException:
                    continue

            return {
                'title': title,
                'url': url,
                'metadata': metadata
            }

        except Exception as e:
            self.logger.debug(f"Failed to parse course element: {e}")
            return None

    def process_course(self, course_data):
        """Process a single course from start to finish"""
        try:
            course_title = course_data['title']
            course_url = course_data['url']

            self.logger.info(f"Starting course: {course_title}")

            # Step 1: Extract completion conditions
            conditions = self.condition_extractor.extract_conditions(course_url)
            self.logger.info(f"Course conditions: {conditions}")

            # Step 2: Get course structure (chapters)
            chapters = self._get_course_chapters()
            self.logger.info(f"Found {len(chapters)} chapters")

            # Step 3: Process each chapter
            chapter_progress = []
            for i, chapter in enumerate(chapters):
                self.logger.info(f"Processing chapter {i+1}/{len(chapters)}: {chapter.get('title', f'Chapter {i+1}')}")

                try:
                    chapter_result = self._process_chapter(chapter, conditions)
                    chapter_progress.append(chapter_result)

                    # Check if we should continue
                    if not chapter_result.get('success', False):
                        self.logger.warning(f"Chapter {i+1} failed, but continuing with next chapter")

                except Exception as e:
                    self.logger.error(f"Chapter {i+1} processing failed: {e}")
                    chapter_progress.append({
                        'chapter_index': i,
                        'success': False,
                        'error': str(e)
                    })

            # Step 4: Handle quiz if present
            quiz_result = self._handle_course_quiz(conditions)

            # Step 5: Check final completion
            final_status = self._check_course_completion(conditions, chapter_progress, quiz_result)

            # Step 6: Submit completion
            submission_result = self._submit_course_completion()

            result = {
                'course_title': course_title,
                'conditions': conditions,
                'chapters_processed': len(chapter_progress),
                'chapters_successful': sum(1 for c in chapter_progress if c.get('success', False)),
                'quiz_result': quiz_result,
                'final_status': final_status,
                'submission_result': submission_result,
                'completed_at': time.time()
            }

            self.logger.info(f"Course completed: {course_title}")
            return result

        except Exception as e:
            self.logger.error(f"Course processing failed: {e}")
            return {
                'course_title': course_data.get('title', 'Unknown'),
                'success': False,
                'error': str(e)
            }

    def _get_course_chapters(self):
        """Get list of course chapters"""
        chapters = []

        try:
            # Find chapter elements
            chapter_selectors = [
                ".chapter",
                ".section",
                "[class*='chapter']",
                "[class*='section']",
                ".lesson",
                "[class*='lesson']"
            ]

            for selector in chapter_selectors:
                chapter_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if chapter_elements:
                    for i, element in enumerate(chapter_elements):
                        chapter_data = {
                            'index': i,
                            'title': safe_get_text(element),
                            'element': element
                        }
                        chapters.append(chapter_data)
                    break

            # If no structured chapters, assume single chapter
            if not chapters:
                chapters = [{
                    'index': 0,
                    'title': 'Main Content',
                    'element': None
                }]

        except Exception as e:
            self.logger.warning(f"Failed to get chapters: {e}")
            chapters = [{
                'index': 0,
                'title': 'Main Content',
                'element': None
            }]

        return chapters

    def _process_chapter(self, chapter, conditions):
        """Process a single chapter"""
        try:
            # Click chapter if needed
            if chapter['element']:
                try:
                    chapter['element'].click()
                    time.sleep(2)  # Wait for content to load
                except Exception as e:
                    self.logger.debug(f"Could not click chapter element: {e}")

            # Find and play video
            if self.video_player.find_video_element():
                # Start playback
                if self.video_player.start_playback():
                    # Wait for completion
                    video_completed = self.video_player.wait_for_completion()
                    if video_completed:
                        self.logger.info(f"Chapter video completed: {chapter['title']}")
                        return {
                            'chapter_index': chapter['index'],
                            'success': True,
                            'video_completed': True
                        }
                    else:
                        self.logger.warning(f"Chapter video did not complete: {chapter['title']}")
                        return {
                            'chapter_index': chapter['index'],
                            'success': False,
                            'video_completed': False,
                            'error': 'Video completion timeout'
                        }
                else:
                    self.logger.error(f"Failed to start video for chapter: {chapter['title']}")
                    return {
                        'chapter_index': chapter['index'],
                        'success': False,
                        'error': 'Video playback failed'
                    }
            else:
                # No video found, consider chapter complete
                self.logger.info(f"No video in chapter: {chapter['title']}")
                return {
                    'chapter_index': chapter['index'],
                    'success': True,
                    'video_completed': False,
                    'note': 'No video content'
                }

        except Exception as e:
            self.logger.error(f"Chapter processing error: {e}")
            return {
                'chapter_index': chapter['index'],
                'success': False,
                'error': str(e)
            }

    def _handle_course_quiz(self, conditions):
        """Handle course quiz if present"""
        try:
            if not AUTO_ANSWER_QUIZ:
                self.logger.info("Quiz auto-answering disabled")
                return {'skipped': True, 'reason': 'Disabled in config'}

            if self.quiz_solver.detect_quiz():
                self.logger.info("Quiz detected, starting auto-answering")

                # Parse questions
                questions = self.quiz_solver.parse_questions()

                if not questions:
                    self.logger.warning("No questions found in quiz")
                    return {'success': False, 'error': 'No questions found'}

                # Answer questions
                answers = self.quiz_solver.answer_questions(questions, QUIZ_METHOD)

                # Submit quiz
                submitted = self.quiz_solver.submit_quiz()

                if submitted:
                    # Get score
                    score = self.quiz_solver.get_quiz_score()
                    passed = self.quiz_solver.is_quiz_passed(score, conditions.get('quiz_min_score', MIN_QUIZ_SCORE))

                    self.logger.info(f"Quiz completed - Score: {score}, Passed: {passed}")
                    return {
                        'success': True,
                        'score': score,
                        'passed': passed,
                        'questions_answered': len(answers)
                    }
                else:
                    self.logger.error("Failed to submit quiz")
                    return {'success': False, 'error': 'Submission failed'}
            else:
                self.logger.info("No quiz found for this course")
                return {'skipped': True, 'reason': 'No quiz detected'}

        except Exception as e:
            self.logger.error(f"Quiz handling failed: {e}")
            return {'success': False, 'error': str(e)}

    def _check_course_completion(self, conditions, chapter_progress, quiz_result):
        """Check if course is fully completed"""
        try:
            # Check video completion
            video_required = conditions.get('video_completion', 0.9)
            video_progress = sum(1 for c in chapter_progress if c.get('video_completed', False)) / len(chapter_progress)
            video_ok = video_progress >= video_required

            # Check quiz
            quiz_required = conditions.get('quiz_min_score', 0) > 0
            if quiz_required:
                quiz_ok = quiz_result.get('passed', False)
            else:
                quiz_ok = True

            # Check other requirements
            discussion_ok = not conditions.get('discussion_required', False) or True  # Placeholder
            assignment_ok = not conditions.get('assignment_required', False) or True  # Placeholder

            all_met = video_ok and quiz_ok and discussion_ok and assignment_ok

            self.logger.info(f"Completion check - Video: {video_ok}, Quiz: {quiz_ok}, Overall: {all_met}")

            return {
                'completed': all_met,
                'video_ok': video_ok,
                'quiz_ok': quiz_ok,
                'discussion_ok': discussion_ok,
                'assignment_ok': assignment_ok
            }

        except Exception as e:
            self.logger.error(f"Completion check failed: {e}")
            return {'completed': False, 'error': str(e)}

    def _submit_course_completion(self):
        """Submit course completion"""
        try:
            # Look for completion/submit button
            completion_selectors = [
                "button:contains('完成')",
                "button:contains('結算')",
                "button:contains('離開')",
                ".completion-btn",
                "[class*='complete']",
                "a[href*='complete']"
            ]

            for selector in completion_selectors:
                try:
                    button = wait_for_element_clickable(self.driver, By.CSS_SELECTOR, selector, timeout=10)
                    button.click()
                    time.sleep(2)

                    self.logger.info("Course completion submitted")
                    return {'success': True}

                except (NoSuchElementException, TimeoutException):
                    continue

            self.logger.warning("Completion button not found")
            return {'success': False, 'error': 'Button not found'}

        except Exception as e:
            self.logger.error(f"Completion submission failed: {e}")
            return {'success': False, 'error': str(e)}