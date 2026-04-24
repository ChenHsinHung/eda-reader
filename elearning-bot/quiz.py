"""
Quiz auto-answering module
Handles quiz detection, question parsing, and automated answering
"""

import time
import logging
import random
import re
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from config import *
from utils import *


class QuizSolver:
    """Handles automated quiz answering"""

    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger('elearning_bot')

    def detect_quiz(self):
        """Detect if current page contains a quiz"""
        try:
            # Common quiz indicators
            quiz_indicators = [
                ".quiz-form",
                ".question-form",
                "[class*='quiz']",
                "[class*='question']",
                "[class*='test']",
                "form[action*='quiz']",
                "form[action*='test']"
            ]

            for indicator in quiz_indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, indicator)
                    self.logger.info(f"Quiz detected with indicator: {indicator}")
                    return True
                except NoSuchElementException:
                    continue

            # Check for question text
            question_selectors = [
                ".question",
                "[class*='question']",
                "h3, h4, h5"  # Often questions are in headings
            ]

            for selector in question_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = safe_get_text(element)
                    if any(keyword in text.lower() for keyword in ['?', '選擇', '答案', '題目']):
                        self.logger.info("Quiz detected by question text")
                        return True

            return False

        except Exception as e:
            self.logger.debug(f"Quiz detection error: {e}")
            return False

    def parse_questions(self):
        """Parse quiz questions and options"""
        questions = []

        try:
            # Find question containers
            question_containers = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".question, [class*='question'], .quiz-question"
            )

            for container in question_containers:
                question_data = self._parse_single_question(container)
                if question_data:
                    questions.append(question_data)

            self.logger.info(f"Parsed {len(questions)} questions")
            return questions

        except Exception as e:
            self.logger.error(f"Failed to parse questions: {e}")
            return []

    def _parse_single_question(self, container):
        """Parse a single question"""
        try:
            # Get question text
            question_text = ""
            question_selectors = ["h3", "h4", "h5", ".question-text", "[class*='question']"]
            for selector in question_selectors:
                try:
                    element = container.find_element(By.CSS_SELECTOR, selector)
                    question_text = safe_get_text(element)
                    if question_text:
                        break
                except NoSuchElementException:
                    continue

            if not question_text:
                return None

            # Get answer options
            options = []
            option_selectors = [
                "input[type='radio']",
                "input[type='checkbox']",
                ".option",
                "[class*='option']",
                "li"
            ]

            for selector in option_selectors:
                option_elements = container.find_elements(By.CSS_SELECTOR, selector)
                if option_elements:
                    for element in option_elements:
                        option_text = safe_get_text(element)
                        if option_text and len(option_text.strip()) > 1:
                            # Get associated input element
                            input_element = None
                            try:
                                if element.tag_name.lower() == 'input':
                                    input_element = element
                                else:
                                    input_element = element.find_element(By.CSS_SELECTOR, "input")
                            except:
                                pass

                            options.append({
                                'text': option_text.strip(),
                                'element': input_element,
                                'container': element
                            })
                    break

            if not options:
                self.logger.debug(f"No options found for question: {question_text[:50]}...")
                return None

            return {
                'question': question_text,
                'options': options,
                'type': 'multiple_choice' if len(options) > 2 else 'true_false'
            }

        except Exception as e:
            self.logger.debug(f"Failed to parse question: {e}")
            return None

    def answer_questions(self, questions, method="traditional"):
        """Answer all questions using specified method"""
        if method == "ai":
            return self._answer_with_ai(questions)
        else:
            return self._answer_traditional(questions)

    def _answer_traditional(self, questions):
        """Answer questions using traditional trial-and-error method"""
        results = []

        for i, question in enumerate(questions):
            self.logger.info(f"Answering question {i+1}/{len(questions)}")

            try:
                result = self._answer_single_question_traditional(question)
                results.append(result)

                # Small delay between questions
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Failed to answer question {i+1}: {e}")
                results.append({
                    'question_index': i,
                    'success': False,
                    'error': str(e)
                })

        return results

    def _answer_single_question_traditional(self, question):
        """Answer a single question using trial and error"""
        options = question['options']

        # Try each option
        for attempt, option in enumerate(options):
            try:
                self.logger.debug(f"Trying option {attempt+1}: {option['text'][:30]}...")

                # Click the option
                if option['element']:
                    option['element'].click()
                else:
                    option['container'].click()

                # Wait a moment
                time.sleep(0.5)

                # Check for success indicators
                if self._check_answer_correct():
                    self.logger.info(f"Question answered correctly on attempt {attempt+1}")
                    return {
                        'question_index': question.get('index', 0),
                        'success': True,
                        'attempts': attempt + 1,
                        'method': 'trial_and_error'
                    }

                # If not correct, try to uncheck if checkbox
                if option['element'] and option['element'].get_attribute('type') == 'checkbox':
                    try:
                        option['element'].click()  # Uncheck
                    except:
                        pass

            except Exception as e:
                self.logger.debug(f"Failed to try option {attempt+1}: {e}")
                continue

        # If no option worked, try random selection
        self.logger.warning("No correct option found, selecting randomly")
        random_option = random.choice(options)
        try:
            if random_option['element']:
                random_option['element'].click()
            else:
                random_option['container'].click()
        except Exception as e:
            self.logger.error(f"Failed to select random option: {e}")

        return {
            'question_index': question.get('index', 0),
            'success': False,
            'attempts': len(options),
            'method': 'random_fallback'
        }

    def _check_answer_correct(self):
        """Check if the current answer is correct"""
        try:
            # Look for success indicators
            success_selectors = [
                ".correct",
                ".success",
                "[class*='correct']",
                ".alert-success",
                "[class*='success']"
            ]

            for selector in success_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        return True
                except NoSuchElementException:
                    continue

            # Look for "correct" text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if any(word in page_text.lower() for word in ['正確', 'correct', 'right', '對']):
                return True

            return False

        except Exception as e:
            self.logger.debug(f"Error checking answer correctness: {e}")
            return False

    def _answer_with_ai(self, questions):
        """Answer questions using AI (placeholder for future implementation)"""
        # This would integrate with OpenAI/Claude API
        # For now, fall back to traditional method
        self.logger.warning("AI method not implemented, falling back to traditional")
        return self._answer_traditional(questions)

    def submit_quiz(self):
        """Submit the completed quiz"""
        try:
            # Find submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                ".submit-btn",
                "[class*='submit']",
                "button:contains('提交')",
                "button:contains('送出')"
            ]

            for selector in submit_selectors:
                try:
                    submit_button = wait_for_element_clickable(self.driver, By.CSS_SELECTOR, selector)
                    submit_button.click()
                    self.logger.info("Quiz submitted")
                    return True
                except (NoSuchElementException, TimeoutException):
                    continue

            self.logger.warning("Submit button not found")
            return False

        except Exception as e:
            self.logger.error(f"Failed to submit quiz: {e}")
            return False

    def get_quiz_score(self):
        """Get the quiz score after submission"""
        try:
            time.sleep(2)  # Wait for results to load

            # Look for score text
            score_patterns = [
                r'分數.*?(\d+)',
                r'成績.*?(\d+)',
                r'得分.*?(\d+)',
                r'(\d+)/\d+',  # Like "80/100"
                r'(\d+)分'
            ]

            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            for pattern in score_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    self.logger.info(f"Quiz score: {score}")
                    return score

            self.logger.warning("Could not find quiz score")
            return 0

        except Exception as e:
            self.logger.error(f"Failed to get quiz score: {e}")
            return 0

    def is_quiz_passed(self, score, min_score=MIN_QUIZ_SCORE):
        """Check if quiz is passed"""
        return score >= min_score