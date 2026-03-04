"""
Generate structured faculty.json from faculty text files.

This script parses all faculty .txt files and creates a comprehensive JSON file
with structured data for improved search and filtering capabilities.

Usage:
    python generate_faculty_json.py                    # Generate faculty.json
    python generate_faculty_json.py --dry-run          # Preview without saving
    python generate_faculty_json.py --validate         # Validate existing JSON
"""

import json
import re
import os
from pathlib import Path
from typing import Optional
import argparse


def extract_field(content: str, field_name: str, multiline: bool = False) -> Optional[str]:
    """Extract a field value from the content."""
    # Try exact match first
    pattern = rf'^{re.escape(field_name)}:\s*(.+?)$'
    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # For multiline fields, get until next section
    if multiline:
        pattern = rf'^{re.escape(field_name)}:\s*\n(.*?)(?=\n[A-Z][^:\n]*:|---|\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def extract_list_field(content: str, field_name: str) -> list[str]:
    """Extract a list field (items starting with -)."""
    pattern = rf'^{re.escape(field_name)}:\s*\n((?:\s*-\s*.+\n?)+)'
    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        items = re.findall(r'^\s*-\s*(.+)$', match.group(1), re.MULTILINE)
        return [item.strip() for item in items if item.strip()]
    return []


def extract_url(content: str, field_name: str) -> Optional[str]:
    """Extract a URL field, handling various formats."""
    # Try standard format: "Website: https://..."
    pattern = rf'^{re.escape(field_name)}:\s*(https?://[^\s\[\]]+)'
    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        url = match.group(1).strip()
        # Clean up any trailing artifacts
        url = re.sub(r'\s*\[oai_citation.*$', '', url)
        url = re.sub(r'\s+.*$', '', url)
        return url
    return None


def parse_metrics(content: str) -> dict:
    """Extract Dimensions research metrics from enriched data section."""
    metrics = {}

    # Find the enriched data section
    enriched_match = re.search(r'--- Enriched Data.*?---(.+?)(?=---|\Z)', content, re.DOTALL)
    if not enriched_match:
        return metrics

    enriched_section = enriched_match.group(1)

    # Extract metrics
    patterns = {
        'total_publications': r'Total Publications:\s*(\d+)',
        'total_citations': r'Total Citations:\s*([\d,]+)',
        'h_index': r'H-Index:\s*(\d+)',
        'avg_citations_per_paper': r'Average Citations per Paper:\s*([\d.]+)',
        'open_access_percentage': r'Open Access Publications:\s*([\d.]+)%',
        'field_citation_ratio': r'Field Citation Ratio:\s*([\d.]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, enriched_section)
        if match:
            value = match.group(1).replace(',', '')
            metrics[key] = float(value) if '.' in value else int(value)

    return metrics


def parse_rankings(content: str) -> dict:
    """Extract research impact rankings."""
    rankings = {}

    # Find the rankings section
    rankings_match = re.search(r'--- Research Impact Rankings.*?---(.+?)(?=---|\Z)', content, re.DOTALL)
    if not rankings_match:
        return rankings

    rankings_section = rankings_match.group(1)

    # Extract impact score
    score_match = re.search(r'Research Impact Score:\s*([\d.]+)/10', rankings_section)
    if score_match:
        rankings['impact_score'] = float(score_match.group(1))

    # Extract percentile
    percentile_match = re.search(r'Percentile:\s*Top\s*(\d+)%', rankings_section)
    if percentile_match:
        rankings['percentile'] = int(percentile_match.group(1))

    # Extract category rankings
    category_rankings = {}
    category_pattern = r'-\s*([^:]+):\s*#(\d+)\s*of\s*(\d+)'
    for match in re.finditer(category_pattern, rankings_section):
        category = match.group(1).strip()
        category_rankings[category] = {
            'rank': int(match.group(2)),
            'total': int(match.group(3))
        }

    if category_rankings:
        rankings['by_category'] = category_rankings

    return rankings


def parse_research_categories(content: str) -> list[str]:
    """Extract research categories from Dimensions data."""
    match = re.search(r'Research Categories \(from Dimensions\.ai\):\s*\n(.+?)(?=\n\n|\nKey Research|\n---|\Z)', content, re.DOTALL)
    if match:
        categories_text = match.group(1).strip()
        # Split by semicolons or numbered prefixes
        categories = re.split(r';\s*|\d+\s+', categories_text)
        return [c.strip() for c in categories if c.strip() and len(c.strip()) > 2]
    return []


def parse_keywords(content: str) -> list[str]:
    """Extract keywords from the Keywords field."""
    keywords_text = extract_field(content, "Keywords")
    if keywords_text:
        # Split by semicolons
        keywords = [k.strip() for k in keywords_text.split(';')]
        return [k for k in keywords if k]
    return []


def parse_subject_areas(content: str) -> list[str]:
    """Extract subject areas."""
    # Try various field names
    for field_name in ["Subject Areas", "Subject Areas (from CSV)"]:
        areas_text = extract_field(content, field_name)
        if areas_text:
            # Split by commas or semicolons
            areas = re.split(r'[,;]\s*', areas_text)
            return [a.strip() for a in areas if a.strip()]
    return []


def parse_publications(content: str) -> list[dict]:
    """Extract recent publications from Dimensions data."""
    publications = []

    # Find the recent publications section
    pub_match = re.search(r'Recent Publications \(from Dimensions\.ai\):\s*\n(.+?)(?=\nResearch Grants|\nResearch Categories|\n---|\Z)', content, re.DOTALL)
    if not pub_match:
        return publications

    pub_section = pub_match.group(1)

    # Parse each publication
    pub_pattern = r'-\s*(.+?)\s*\*([^*]+)\*\s*\((\d{4})\)\s*-?\s*(\d+)?\s*citations?\s*\n\s*DOI:\s*(https?://[^\s]+)'
    for match in re.finditer(pub_pattern, pub_section, re.IGNORECASE):
        pub = {
            'title': match.group(1).strip(),
            'journal': match.group(2).strip(),
            'year': int(match.group(3)),
            'doi': match.group(5).strip()
        }
        if match.group(4):
            pub['citations'] = int(match.group(4))
        publications.append(pub)

    return publications


def parse_grants(content: str) -> list[dict]:
    """Extract research grants from Dimensions data."""
    grants = []

    # Find the research grants section
    grants_match = re.search(r'Research Grants \(from Dimensions\.ai\):\s*\n(.+?)(?=\nResearch Categories|\nKey Research|\n---|\Z)', content, re.DOTALL)
    if not grants_match:
        return grants

    grants_section = grants_match.group(1)

    # Parse each grant - handle various formats
    grant_pattern = r'-\s*(.+?)\s*\((\d{4})-(\d{4}|present)\)\s*(?:-\s*\$?([\d,]+))?\s*\n\s*Funder:\s*(.+?)(?=\n-|\Z)'
    for match in re.finditer(grant_pattern, grants_section, re.IGNORECASE | re.DOTALL):
        grant = {
            'title': match.group(1).strip(),
            'start_year': int(match.group(2)),
            'end_year': match.group(3) if match.group(3) == 'present' else int(match.group(3)),
            'funder': match.group(5).strip()
        }
        if match.group(4):
            grant['funding_usd'] = int(match.group(4).replace(',', ''))
        grants.append(grant)

    return grants


def parse_faculty_file(file_path: Path) -> dict:
    """Parse a single faculty file and return structured data."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate ID from filename
    faculty_id = file_path.stem.lower()

    # Extract basic fields
    name = extract_field(content, "Name")
    if not name:
        # Try to get name from filename
        name = file_path.stem.replace('_', ' ')

    faculty = {
        'id': faculty_id,
        'name': name,
        'role': extract_field(content, "Role"),
        'academic_unit': extract_field(content, "Academic Unit"),
        'email': extract_field(content, "Email"),
        'phone': extract_field(content, "Phone"),
        'office': extract_field(content, "Office"),
        'title': extract_field(content, "Title"),
    }

    # Extract URLs
    website = extract_url(content, "Website")
    google_scholar = extract_url(content, "Google Scholar")
    if website:
        faculty['website'] = website
    if google_scholar:
        faculty['google_scholar'] = google_scholar

    # Extract expertise fields
    subject_areas = parse_subject_areas(content)
    keywords = parse_keywords(content)
    research_categories = parse_research_categories(content)

    if subject_areas or keywords or research_categories:
        faculty['expertise'] = {}
        if subject_areas:
            faculty['expertise']['subject_areas'] = subject_areas
        if keywords:
            faculty['expertise']['keywords'] = keywords
        if research_categories:
            faculty['expertise']['research_categories'] = research_categories

    # Extract education
    education = extract_list_field(content, "Education")
    if education:
        faculty['education'] = education

    # Extract research focus (paragraph)
    research_focus = extract_field(content, "Research Focus", multiline=True)
    if research_focus:
        # Clean up and truncate for JSON
        research_focus = ' '.join(research_focus.split())  # Normalize whitespace
        faculty['research_focus'] = research_focus[:2000]  # Limit length

    # Extract metrics from Dimensions data
    metrics = parse_metrics(content)
    if metrics:
        faculty['metrics'] = metrics

    # Extract rankings
    rankings = parse_rankings(content)
    if rankings:
        faculty['rankings'] = rankings

    # Extract publications
    publications = parse_publications(content)
    if publications:
        faculty['recent_publications'] = publications[:5]  # Top 5 only

    # Extract grants
    grants = parse_grants(content)
    if grants:
        faculty['grants'] = grants[:3]  # Top 3 only

    # Remove None values
    faculty = {k: v for k, v in faculty.items() if v is not None}

    return faculty


def generate_faculty_json(faculty_dir: Path, output_path: Path, dry_run: bool = False) -> dict:
    """Generate faculty.json from all faculty text files."""
    faculty_files = list(faculty_dir.glob("*.txt"))
    print(f"Found {len(faculty_files)} faculty files")

    faculty_data = {
        'metadata': {
            'generated': None,  # Will be set below
            'total_faculty': len(faculty_files),
            'version': '1.0'
        },
        'faculty': {}
    }

    # Track statistics
    stats = {
        'with_metrics': 0,
        'with_rankings': 0,
        'with_website': 0,
        'with_google_scholar': 0,
        'with_publications': 0,
        'parse_errors': 0
    }

    for file_path in sorted(faculty_files):
        try:
            faculty = parse_faculty_file(file_path)
            faculty_id = faculty['id']
            faculty_data['faculty'][faculty_id] = faculty

            # Update stats
            if 'metrics' in faculty:
                stats['with_metrics'] += 1
            if 'rankings' in faculty:
                stats['with_rankings'] += 1
            if 'website' in faculty:
                stats['with_website'] += 1
            if 'google_scholar' in faculty:
                stats['with_google_scholar'] += 1
            if 'recent_publications' in faculty:
                stats['with_publications'] += 1

        except Exception as e:
            print(f"  Error parsing {file_path.name}: {e}")
            stats['parse_errors'] += 1

    # Set generation timestamp
    from datetime import datetime
    faculty_data['metadata']['generated'] = datetime.now().isoformat()
    faculty_data['metadata']['stats'] = stats

    # Print summary
    print(f"\n{'='*50}")
    print("Generation Summary:")
    print(f"  Total faculty parsed: {len(faculty_data['faculty'])}")
    print(f"  With Dimensions metrics: {stats['with_metrics']}")
    print(f"  With rankings: {stats['with_rankings']}")
    print(f"  With website URL: {stats['with_website']}")
    print(f"  With Google Scholar: {stats['with_google_scholar']}")
    print(f"  With publications: {stats['with_publications']}")
    print(f"  Parse errors: {stats['parse_errors']}")
    print(f"{'='*50}")

    if dry_run:
        print("\n[DRY RUN] Would save to:", output_path)
        # Print sample entry
        sample_id = list(faculty_data['faculty'].keys())[0]
        print(f"\nSample entry ({sample_id}):")
        print(json.dumps(faculty_data['faculty'][sample_id], indent=2)[:1500])
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(faculty_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

    return faculty_data


def validate_faculty_json(json_path: Path) -> bool:
    """Validate the generated faculty.json."""
    print(f"Validating: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issues = []

    # Check structure
    if 'metadata' not in data:
        issues.append("Missing 'metadata' field")
    if 'faculty' not in data:
        issues.append("Missing 'faculty' field")

    # Check each faculty entry
    required_fields = ['id', 'name']
    for faculty_id, faculty in data.get('faculty', {}).items():
        for field in required_fields:
            if field not in faculty:
                issues.append(f"{faculty_id}: Missing required field '{field}'")

        # Validate URLs
        for url_field in ['website', 'google_scholar']:
            if url_field in faculty:
                url = faculty[url_field]
                if not url.startswith('http'):
                    issues.append(f"{faculty_id}: Invalid {url_field} URL: {url[:50]}")

        # Validate metrics
        if 'metrics' in faculty:
            metrics = faculty['metrics']
            if 'h_index' in metrics and (metrics['h_index'] < 0 or metrics['h_index'] > 200):
                issues.append(f"{faculty_id}: Suspicious h_index: {metrics['h_index']}")

    if issues:
        print(f"\nFound {len(issues)} issues:")
        for issue in issues[:20]:  # Show first 20
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
        return False
    else:
        print("Validation passed!")
        print(f"  Total faculty: {len(data['faculty'])}")
        return True


def main():
    parser = argparse.ArgumentParser(description='Generate structured faculty.json from text files')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--validate', action='store_true', help='Validate existing JSON')
    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    faculty_dir = script_dir / ".." / "data" / "faculty_txt"
    output_path = script_dir / ".." / "data" / "faculty.json"

    if args.validate:
        if output_path.exists():
            validate_faculty_json(output_path)
        else:
            print(f"Error: {output_path} does not exist")
    else:
        generate_faculty_json(faculty_dir, output_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
