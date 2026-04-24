#!/usr/bin/env python3
"""
Setup script for elearning-bot
Run this script to configure credentials for the first time
Usage: python setup.py [--reset]
"""

import sys
import os
import getpass
import argparse
from encryption import get_credential_manager


def setup_credentials(reset=False):
    """Setup or reset credentials"""
    manager = get_credential_manager()

    if not reset and manager.credentials_exist():
        print("Credentials already exist. Use --reset to overwrite.")
        return

    if reset:
        confirm = input("This will delete existing credentials. Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        manager.reset_credentials()

    print("\n=== elearning-bot Setup ===")
    print("Please enter your elearning.taipei credentials:")
    print("(Note: Credentials will be encrypted and stored locally)")
    print()

    # Get account ID
    while True:
        account_id = input("身分證字號 (ID): ").strip()
        if len(account_id) == 10:  # Taiwanese ID format
            break
        print("Invalid ID format. Please enter a valid Taiwanese ID (10 characters).")

    # Get password (hidden input)
    password = getpass.getpass("密碼 (Password): ").strip()
    if not password:
        print("Password cannot be empty.")
        return

    # Confirm password
    password_confirm = getpass.getpass("確認密碼 (Confirm Password): ").strip()
    if password != password_confirm:
        print("Passwords do not match.")
        return

    try:
        # Save credentials
        manager.save_credentials(account_id, password)
        print("\n✅ Credentials encrypted and saved successfully!")
        print(f"Files stored in: {manager.credentials_dir}")
        print("\nYou can now run: python main.py")

    except Exception as e:
        print(f"\n❌ Failed to save credentials: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Setup elearning-bot credentials')
    parser.add_argument('--reset', action='store_true',
                       help='Reset existing credentials')

    args = parser.parse_args()

    try:
        setup_credentials(reset=args.reset)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()