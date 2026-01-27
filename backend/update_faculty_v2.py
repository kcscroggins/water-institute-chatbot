#!/usr/bin/env python3
"""
Update faculty_txt files with Google Scholar and Website info from Version 2 Excel.
"""

import pandas as pd
import os
import re
from pathlib import Path

# Paths
EXCEL_FILE = "../Database Affilaite Faculty Information Version 2.xlsx"
FACULTY_DIR = "../data/faculty_txt"

def clean_name_for_filename(last_name, first_name):
    """Convert name to filename format: LastName_FirstName.txt"""
    # Remove special characters and spaces
    last = re.sub(r'[^a-zA-Z]', '', last_name)
    first = re.sub(r'[^a-zA-Z]', '', first_name)
    return f"{last}_{first}.txt"

def find_faculty_file(email, last_name, first_name):
    """Find the faculty file by trying different naming patterns."""
    # Try exact match first
    filename = clean_name_for_filename(last_name, first_name)
    filepath = os.path.join(FACULTY_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    # Try searching by email in file content
    for f in os.listdir(FACULTY_DIR):
        if f.endswith('.txt'):
            fpath = os.path.join(FACULTY_DIR, f)
            with open(fpath, 'r') as file:
                content = file.read()
                if email.lower() in content.lower():
                    return fpath

    return None

def update_faculty_file(filepath, google_scholar, website):
    """Update a faculty file with Google Scholar and/or Website if not present."""
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    lines = content.split('\n')
    updated = False

    # Find where to insert (after Email line)
    email_idx = None
    for i, line in enumerate(lines):
        if line.startswith('Email:'):
            email_idx = i
            break

    if email_idx is None:
        print(f"  Warning: No Email line found in {filepath}")
        return False

    # Check if Google Scholar already exists
    has_google_scholar = any('Google Scholar:' in line for line in lines)
    has_website = any('Website:' in line for line in lines)

    insertions = []

    # Add Google Scholar if not present and we have data
    if google_scholar and not has_google_scholar:
        insertions.append(f"Google Scholar: {google_scholar}")
        updated = True

    # Add Website if not present and we have data
    if website and not has_website:
        insertions.append(f"Website: {website}")
        updated = True

    if insertions:
        # Insert after email line
        for i, insertion in enumerate(insertions):
            lines.insert(email_idx + 1 + i, insertion)

        new_content = '\n'.join(lines)
        with open(filepath, 'w') as f:
            f.write(new_content)

        return True

    return False

def main():
    # Read Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Rename columns for easier access
    df.columns = ['Last Name', 'First Name', 'Email', 'Department', 'Google Scholar', 'Website']

    # Remove duplicates (keep first)
    df = df.drop_duplicates(subset=['Email'], keep='first')

    print(f"Processing {len(df)} unique faculty members...")
    print()

    updated_count = 0
    not_found_count = 0
    already_complete_count = 0

    for idx, row in df.iterrows():
        last_name = str(row['Last Name']).strip() if pd.notna(row['Last Name']) else ''
        first_name = str(row['First Name']).strip() if pd.notna(row['First Name']) else ''
        email = str(row['Email']).strip() if pd.notna(row['Email']) else ''
        google_scholar = str(row['Google Scholar']).strip() if pd.notna(row['Google Scholar']) else None
        website = str(row['Website']).strip() if pd.notna(row['Website']) else None

        # Skip if no new data to add
        if not google_scholar and not website:
            already_complete_count += 1
            continue

        # Find the faculty file
        filepath = find_faculty_file(email, last_name, first_name)

        if filepath:
            if update_faculty_file(filepath, google_scholar, website):
                print(f"✓ Updated: {first_name} {last_name}")
                if google_scholar:
                    print(f"  + Google Scholar: {google_scholar[:50]}...")
                if website:
                    print(f"  + Website: {website[:50]}...")
                updated_count += 1
            else:
                already_complete_count += 1
        else:
            print(f"✗ Not found: {first_name} {last_name} ({email})")
            not_found_count += 1

    print()
    print("=" * 50)
    print(f"Summary:")
    print(f"  - Updated: {updated_count} files")
    print(f"  - Already complete/no new data: {already_complete_count} files")
    print(f"  - Not found: {not_found_count} files")

if __name__ == "__main__":
    main()
