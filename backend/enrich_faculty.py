"""
Faculty Data Enrichment Script using Dimensions API

This script enriches faculty profiles with:
- Recent publications (last 5 years)
- Citation metrics (h-index proxy, total citations)
- Active grants
- Top cited publications

Usage:
    python enrich_faculty.py                    # Enrich all faculty
    python enrich_faculty.py --name "Mike Allen"  # Enrich specific faculty
    python enrich_faculty.py --dry-run          # Preview without saving

Requires DIMENSIONS_API_KEY in .env file
"""

import os
import re
import json
import time
import requests
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../.env")

# Configuration
DIMENSIONS_API_KEY = os.getenv("DIMENSIONS_API_KEY")
DIMENSIONS_AUTH_URL = "https://app.dimensions.ai/api/auth"
DIMENSIONS_API_URL = "https://app.dimensions.ai/api/dsl/v2"
FACULTY_DIR = Path("../data/faculty_txt")
ENRICHED_DIR = Path("../data/enriched")

# Rate limiting: 30 requests per minute
REQUEST_DELAY = 2.5  # seconds between requests


class DimensionsClient:
    """Client for interacting with Dimensions API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.token = None
        self.token_timestamp = None

    def authenticate(self):
        """Get authentication token from Dimensions API"""
        if not self.api_key:
            raise ValueError("DIMENSIONS_API_KEY not found in environment variables")

        resp = requests.post(
            DIMENSIONS_AUTH_URL,
            json={"key": self.api_key}
        )

        if resp.status_code != 200:
            raise Exception(f"Authentication failed: {resp.status_code} - {resp.text}")

        self.token = resp.json().get("token")
        self.token_timestamp = datetime.now()
        print("✅ Authenticated with Dimensions API")
        return self.token

    def _ensure_token(self):
        """Ensure we have a valid token (tokens expire after ~2 hours)"""
        if not self.token or not self.token_timestamp:
            self.authenticate()
        elif (datetime.now() - self.token_timestamp).seconds > 6000:  # Refresh after 100 min
            self.authenticate()

    def query(self, dsl_query: str) -> dict:
        """Execute a DSL query against Dimensions API"""
        self._ensure_token()

        headers = {"Authorization": f"JWT {self.token}"}
        resp = requests.post(
            DIMENSIONS_API_URL,
            data=dsl_query.encode("utf-8"),
            headers=headers
        )

        if resp.status_code != 200:
            raise Exception(f"Query failed: {resp.status_code} - {resp.text}")

        return resp.json()

    def search_researcher_publications(self, name: str, org: str = "University of Florida",
                                        years: int = 5, limit: int = 20) -> dict:
        """Search for publications by researcher name and organization"""
        current_year = datetime.now().year
        start_year = current_year - years

        # Clean name for query
        clean_name = name.replace('"', '\\"')

        query = f'''
        search publications
            in authors for "\\"{clean_name}\\""
            where research_orgs.name = "{org}"
            and year >= {start_year}
        return publications[id+doi+title+year+times_cited+journal+authors+abstract+type]
            sort by times_cited desc
            limit {limit}
        '''

        return self.query(query)

    def search_researcher_grants(self, name: str, org: str = "University of Florida",
                                  limit: int = 10) -> dict:
        """Search for grants by researcher name and organization"""
        # Clean name for query
        clean_name = name.replace('"', '\\"')

        query = f'''
        search grants
            in investigators for "\\"{clean_name}\\""
            where research_orgs.name = "{org}"
        return grants[id+title+start_year+end_year+funding_usd+funder_orgs+abstract]
            sort by start_year desc
            limit {limit}
        '''

        return self.query(query)

    def get_citation_metrics(self, name: str, org: str = "University of Florida") -> dict:
        """Get aggregated citation metrics for a researcher"""
        clean_name = name.replace('"', '\\"')

        query = f'''
        search publications
            in authors for "\\"{clean_name}\\""
            where research_orgs.name = "{org}"
        return publications[times_cited]
            limit 500
        '''

        result = self.query(query)
        publications = result.get("publications", [])

        # Calculate metrics
        total_pubs = len(publications)
        citations = [p.get("times_cited", 0) for p in publications]
        total_citations = sum(citations)

        # Calculate h-index approximation
        sorted_citations = sorted(citations, reverse=True)
        h_index = 0
        for i, c in enumerate(sorted_citations):
            if c >= i + 1:
                h_index = i + 1
            else:
                break

        return {
            "total_publications": total_pubs,
            "total_citations": total_citations,
            "h_index": h_index,
            "avg_citations": round(total_citations / total_pubs, 1) if total_pubs > 0 else 0
        }


def extract_faculty_name(file_path: Path) -> str:
    """Extract faculty name from a .txt file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for "Name: XXX" pattern
    match = re.search(r"^Name:\s*(.+?)(?:\s*$|\s{2,})", content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fallback: use filename
    return file_path.stem.replace("_", " ")


def format_publication(pub: dict) -> str:
    """Format a publication for display"""
    title = pub.get("title", "Untitled")
    year = pub.get("year", "N/A")
    citations = pub.get("times_cited", 0)
    journal = pub.get("journal", {})
    journal_title = journal.get("title", "") if isinstance(journal, dict) else ""
    doi = pub.get("doi", "")

    formatted = f"- {title}"
    if journal_title:
        formatted += f" *{journal_title}*"
    formatted += f" ({year})"
    if citations > 0:
        formatted += f" - {citations} citations"
    if doi:
        formatted += f"\n  DOI: https://doi.org/{doi}"

    return formatted


def format_grant(grant: dict) -> str:
    """Format a grant for display"""
    title = grant.get("title", "Untitled")
    start = grant.get("start_year", "")
    end = grant.get("end_year", "")
    funding = grant.get("funding_usd")
    funders = grant.get("funder_orgs", [])

    funder_names = []
    for f in funders:
        if isinstance(f, dict):
            funder_names.append(f.get("name", ""))

    formatted = f"- {title}"
    if start and end:
        formatted += f" ({start}-{end})"
    elif start:
        formatted += f" ({start}-present)"
    if funding:
        formatted += f" - ${funding:,.0f}"
    if funder_names:
        formatted += f"\n  Funder: {', '.join(funder_names)}"

    return formatted


def create_enrichment_section(name: str, publications: list, grants: list,
                               metrics: dict) -> str:
    """Create the enrichment text section to append to faculty file"""

    sections = []

    # Citation Metrics Section
    if metrics.get("total_publications", 0) > 0:
        sections.append(f"""
Dimensions Research Metrics (via Dimensions.ai):
- Total Publications: {metrics['total_publications']}
- Total Citations: {metrics['total_citations']}
- H-Index: {metrics['h_index']}
- Average Citations per Paper: {metrics['avg_citations']}
""")

    # Recent Publications Section
    if publications:
        pub_lines = [format_publication(p) for p in publications[:10]]
        sections.append(f"""
Recent Publications (from Dimensions.ai):
{chr(10).join(pub_lines)}
""")

    # Grants Section
    if grants:
        grant_lines = [format_grant(g) for g in grants[:5]]
        sections.append(f"""
Research Grants (from Dimensions.ai):
{chr(10).join(grant_lines)}
""")

    if not sections:
        return ""

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    header = f"\n\n--- Enriched Data (Updated: {timestamp}) ---"

    return header + "".join(sections)


def enrich_faculty_file(file_path: Path, client: DimensionsClient,
                        dry_run: bool = False) -> dict:
    """Enrich a single faculty file with Dimensions data"""

    name = extract_faculty_name(file_path)
    print(f"\n📚 Processing: {name}")

    result = {
        "name": name,
        "file": str(file_path),
        "publications_found": 0,
        "grants_found": 0,
        "success": False,
        "error": None
    }

    try:
        # Fetch data from Dimensions
        print(f"   Searching publications...")
        time.sleep(REQUEST_DELAY)
        pub_result = client.search_researcher_publications(name)
        publications = pub_result.get("publications", [])
        result["publications_found"] = len(publications)
        print(f"   Found {len(publications)} publications")

        print(f"   Searching grants...")
        time.sleep(REQUEST_DELAY)
        grant_result = client.search_researcher_grants(name)
        grants = grant_result.get("grants", [])
        result["grants_found"] = len(grants)
        print(f"   Found {len(grants)} grants")

        print(f"   Calculating metrics...")
        time.sleep(REQUEST_DELAY)
        metrics = client.get_citation_metrics(name)
        print(f"   H-index: {metrics['h_index']}, Total citations: {metrics['total_citations']}")

        # Create enrichment section
        enrichment = create_enrichment_section(name, publications, grants, metrics)

        if not enrichment:
            print(f"   ⚠️ No data found for {name}")
            result["error"] = "No data found"
            return result

        if dry_run:
            print(f"   [DRY RUN] Would append {len(enrichment)} characters")
            print(f"   Preview:\n{enrichment[:500]}...")
        else:
            # Read existing content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove old enrichment section if exists
            content = re.sub(
                r"\n\n--- Enriched Data \(Updated:.*?$",
                "",
                content,
                flags=re.DOTALL
            )

            # Append new enrichment
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content.rstrip() + enrichment)

            print(f"   ✅ Updated {file_path.name}")

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        print(f"   ❌ Error: {e}")

    return result


def save_enrichment_json(file_path: Path, name: str, publications: list,
                          grants: list, metrics: dict):
    """Save enrichment data as JSON for potential API use"""
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "name": name,
        "updated": datetime.now().isoformat(),
        "metrics": metrics,
        "publications": publications[:10],
        "grants": grants[:5]
    }

    json_path = ENRICHED_DIR / f"{file_path.stem}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Enrich faculty data with Dimensions API")
    parser.add_argument("--name", type=str, help="Enrich specific faculty by name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--file", type=str, help="Enrich specific file")
    args = parser.parse_args()

    if not DIMENSIONS_API_KEY:
        print("❌ Error: DIMENSIONS_API_KEY not found in .env file")
        print("   Add this to your .env file: DIMENSIONS_API_KEY=your_key_here")
        return

    # Initialize client
    client = DimensionsClient(DIMENSIONS_API_KEY)

    try:
        client.authenticate()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Get faculty files to process
    if args.file:
        files = [Path(args.file)]
    elif args.name:
        # Find file matching name
        files = []
        for f in FACULTY_DIR.glob("*.txt"):
            if args.name.lower() in extract_faculty_name(f).lower():
                files.append(f)
        if not files:
            print(f"❌ No faculty file found matching '{args.name}'")
            return
    else:
        files = list(FACULTY_DIR.glob("*.txt"))

    print(f"\n🔬 Enriching {len(files)} faculty files...")
    if args.dry_run:
        print("   (DRY RUN - no changes will be saved)\n")

    results = []
    for file_path in files:
        result = enrich_faculty_file(file_path, client, dry_run=args.dry_run)
        results.append(result)

    # Summary
    successful = sum(1 for r in results if r["success"])
    total_pubs = sum(r["publications_found"] for r in results)
    total_grants = sum(r["grants_found"] for r in results)

    print(f"\n" + "="*50)
    print(f"📊 Enrichment Complete!")
    print(f"   Faculty processed: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Total publications found: {total_pubs}")
    print(f"   Total grants found: {total_grants}")

    if not args.dry_run and successful > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Review the updated files in {FACULTY_DIR}")
        print(f"   2. Run: python ingest_faculty.py")
        print(f"   3. Redeploy to update the live chatbot")


if __name__ == "__main__":
    main()
