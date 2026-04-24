#!/usr/bin/env python3
"""
Main entry point for elearning-bot
Automated learning system for elearning.taipei
"""

import sys
import time
import json
import argparse
from datetime import datetime

from config import *
from utils import setup_logging
from auth import AuthManager
from course import CourseNavigator
from encryption import get_credential_manager


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='elearning.taipei automated learning bot')
    parser.add_argument('--courses', nargs='*', help='Specific courses to complete (leave empty for all)')
    parser.add_argument('--max-courses', type=int, default=0, help='Maximum number of courses to process (0 = all)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode - show what would be done')
    parser.add_argument('--web', action='store_true', help='Start web interface')
    parser.add_argument('--web-host', default=WEB_HOST, help='Web interface host')
    parser.add_argument('--web-port', type=int, default=WEB_PORT, help='Web interface port')
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("elearning-bot started")
    logger.info(f"Arguments: {args}")
    logger.info("=" * 50)

    # Start web interface if requested
    if args.web:
        try:
            from web_ui import run_web_ui
            logger.info("Starting web interface...")
            run_web_ui()
            return
        except ImportError as e:
            logger.error(f"Web interface not available: {e}")
            logger.error("Make sure Flask and flask-socketio are installed")
            sys.exit(1)

    try:
        # Check credentials
        manager = get_credential_manager()
        if not manager.credentials_exist():
            logger.error("No credentials found. Please run: python setup.py")
            sys.exit(1)

        # Initialize browser
        auth_manager = AuthManager()
        driver = None

        try:
            # Login
            logger.info("Attempting login...")
            if not auth_manager.login():
                logger.error("Login failed. Check credentials and network.")
                sys.exit(1)

            driver = auth_manager.get_driver()
            logger.info("Login successful")

            # Initialize course navigator
            navigator = CourseNavigator(driver)

            # Get course list
            logger.info("Fetching course list...")
            courses = navigator.get_course_list()

            if not courses:
                logger.warning("No courses found")
                return

            # Filter courses if specified
            if args.courses:
                courses = [c for c in courses if any(keyword.lower() in c['title'].lower() for keyword in args.courses)]
                logger.info(f"Filtered to {len(courses)} specified courses")

            # Limit courses if specified
            if args.max_courses > 0:
                courses = courses[:args.max_courses]
                logger.info(f"Limited to {len(courses)} courses")

            logger.info(f"Will process {len(courses)} courses")

            if args.dry_run:
                logger.info("DRY RUN MODE - Would process:")
                for i, course in enumerate(courses, 1):
                    logger.info(f"  {i}. {course['title']}")
                return

            # Process courses
            results = []
            successful_courses = 0

            for i, course in enumerate(courses, 1):
                logger.info("=" * 30)
                logger.info(f"Processing course {i}/{len(courses)}: {course['title']}")
                logger.info("=" * 30)

                try:
                    result = navigator.process_course(course)
                    results.append(result)

                    if result.get('final_status', {}).get('completed', False):
                        successful_courses += 1
                        logger.info(f"✅ Course completed successfully")
                    else:
                        logger.warning(f"⚠️  Course not fully completed")

                    # Small delay between courses
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"❌ Course processing failed: {e}")
                    results.append({
                        'course_title': course['title'],
                        'success': False,
                        'error': str(e)
                    })

            # Generate summary report
            generate_report(results, successful_courses, len(courses))

        finally:
            # Cleanup
            if auth_manager:
                auth_manager.cleanup()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


def generate_report(results, successful, total):
    """Generate completion report"""
    logger = logging.getLogger('elearning_bot')

    # Calculate statistics
    total_hours = sum(r.get('metadata', {}).get('hours', 0) for r in results if r.get('success', False))

    report = {
        'timestamp': datetime.now().isoformat(),
        'total_courses': total,
        'successful_courses': successful,
        'success_rate': successful / total if total > 0 else 0,
        'total_hours_completed': total_hours,
        'courses': results
    }

    # Save to file
    report_file = os.path.join(CREDENTIALS_DIR, "logs", f"report_{int(time.time())}.json")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")

    # Print summary
    logger.info("=" * 50)
    logger.info("COMPLETION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total courses processed: {total}")
    logger.info(f"Successfully completed: {successful}")
    logger.info(f"Success rate: {successful/total:.1%}" if total > 0 else "Success rate: N/A")
    logger.info(f"Total hours completed: {total_hours}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()