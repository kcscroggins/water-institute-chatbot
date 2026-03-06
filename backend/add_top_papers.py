"""
Add Top Cited Papers to Faculty Profiles

Adds an all-time "Top Cited Papers" section to faculty .txt files using
Dimensions API data. This complements the existing "Recent Publications"
(last 5 years) with the most-cited papers across all time.

Usage:
    python add_top_papers.py                      # All faculty in rankings.json
    python add_top_papers.py --name "Matt Cohen"  # Single faculty member
    python add_top_papers.py --dry-run             # Preview without saving
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Reuse DimensionsClient from enrich_faculty
from enrich_faculty import (
    DimensionsClient,
    extract_faculty_name,
    DIMENSIONS_API_KEY,
    FACULTY_DIR,
    REQUEST_DELAY,
)

# Load environment variables
load_dotenv(dotenv_path="../.env")

RANKINGS_PATH = Path("../data/rankings.json")


def get_ranked_faculty_names() -> list[str]:
    """Get unique faculty names from rankings.json"""
    with open(RANKINGS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    names = set()
    # Overall rankings
    for entry in data.get("overall", []):
        names.add(entry["name"])
    # Category rankings
    for cat_entries in data.get("categories", {}).values():
        for entry in cat_entries:
            names.add(entry["name"])

    return sorted(names)


def find_faculty_file(name: str) -> Path | None:
    """Find the .txt file for a faculty member by name.

    Matches if all words in the search name appear in the faculty name,
    so 'Matt Cohen' matches 'Matthew J. Cohen'.
    """
    search_parts = name.lower().split()
    for f in FACULTY_DIR.glob("*.txt"):
        faculty_name = extract_faculty_name(f).lower()
        if all(part in faculty_name for part in search_parts):
            return f
    return None


def query_top_papers(client: DimensionsClient, name: str, limit: int = 5) -> list:
    """Query Dimensions for top cited papers all time"""
    clean_name = name.replace('"', '\\"')

    query = f'''
    search publications
        in authors for "\\"{clean_name}\\""
        where research_orgs.name = "University of Florida"
    return publications[id+doi+title+year+times_cited+journal]
        sort by times_cited desc
        limit {limit}
    '''

    result = client.query(query)
    return result.get("publications", [])


def format_top_paper(pub: dict) -> str:
    """Format a single top-cited paper"""
    title = pub.get("title", "Untitled")
    year = pub.get("year", "N/A")
    citations = pub.get("times_cited", 0)
    journal = pub.get("journal", {})
    journal_title = journal.get("title", "") if isinstance(journal, dict) else ""
    doi = pub.get("doi", "")

    line = f"- {title}"
    if journal_title:
        line += f" *{journal_title}*"
    line += f" ({year}) - {citations} citations"
    if doi:
        line += f"\n  DOI: https://doi.org/{doi}"

    return line


def build_top_papers_section(publications: list) -> str:
    """Build the top cited papers text section"""
    if not publications:
        return ""

    lines = [format_top_paper(p) for p in publications]
    return "Top Cited Papers (All Time, from Dimensions.ai):\n" + "\n".join(lines)


def insert_top_papers(content: str, section_text: str) -> str:
    """Insert top papers section before 'Recent Publications' in the enriched data block"""

    # Remove any existing top papers section
    content = re.sub(
        r"\nTop Cited Papers \(All Time, from Dimensions\.ai\):.*?(?=\n\n|\nRecent Publications)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Insert before "Recent Publications"
    marker = "\nRecent Publications (from Dimensions.ai):"
    if marker in content:
        content = content.replace(
            marker,
            "\n" + section_text + "\n" + marker,
        )
    else:
        # If no Recent Publications section, insert before Research Grants or at end of enriched block
        for fallback in [
            "\nResearch Grants (from Dimensions.ai):",
            "\nResearch Categories (from Dimensions.ai):",
            "\n--- Research Impact Rankings",
        ]:
            if fallback in content:
                content = content.replace(
                    fallback,
                    "\n" + section_text + "\n" + fallback,
                )
                break

    return content


def process_faculty(name: str, client: DimensionsClient, dry_run: bool = False) -> dict:
    """Process a single faculty member"""
    result = {"name": name, "success": False, "papers_found": 0, "error": None}

    file_path = find_faculty_file(name)
    if not file_path:
        result["error"] = f"No .txt file found for {name}"
        print(f"  ⚠️  {result['error']}")
        return result

    try:
        print(f"  Querying top papers...")
        time.sleep(REQUEST_DELAY)
        papers = query_top_papers(client, name)
        result["papers_found"] = len(papers)

        if not papers:
            print(f"  No papers found")
            result["error"] = "No papers found"
            return result

        print(f"  Found {len(papers)} papers (top: {papers[0].get('times_cited', 0)} citations)")

        section_text = build_top_papers_section(papers)

        if dry_run:
            print(f"  [DRY RUN] Would insert into {file_path.name}:")
            print(f"  ---")
            for line in section_text.split("\n"):
                print(f"  {line}")
            print(f"  ---")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated = insert_top_papers(content, section_text)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated)

            print(f"  ✅ Updated {file_path.name}")

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        print(f"  ❌ Error: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Add top cited papers to faculty profiles")
    parser.add_argument("--name", type=str, help="Process specific faculty by name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    if not DIMENSIONS_API_KEY:
        print("❌ DIMENSIONS_API_KEY not found in .env")
        return

    client = DimensionsClient(DIMENSIONS_API_KEY)
    try:
        client.authenticate()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Determine which faculty to process
    if args.name:
        names = [args.name]
    else:
        names = get_ranked_faculty_names()

    print(f"\n📖 Adding top cited papers for {len(names)} faculty...")
    if args.dry_run:
        print("  (DRY RUN - no changes will be saved)\n")

    results = []
    for i, name in enumerate(names, 1):
        print(f"\n[{i}/{len(names)}] {name}")
        result = process_faculty(name, client, dry_run=args.dry_run)
        results.append(result)

    # Summary
    successful = sum(1 for r in results if r["success"])
    total_papers = sum(r["papers_found"] for r in results)
    errors = [r for r in results if r["error"]]

    print(f"\n{'='*50}")
    print(f"📊 Done!")
    print(f"  Processed: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Total papers added: {total_papers}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for r in errors:
            print(f"    - {r['name']}: {r['error']}")

    if not args.dry_run and successful > 0:
        print(f"\n💡 Next steps:")
        print(f"  1. Run: python ingest_faculty.py")
        print(f"  2. Run: python test_chatbot.py --local")


if __name__ == "__main__":
    main()
