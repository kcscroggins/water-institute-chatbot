"""
Faculty Ranking Script

This script computes research impact rankings for faculty based on Dimensions data.
It calculates:
- Composite Research Impact Score (0-10 scale)
- Percentile ranking among Water Institute faculty
- Category-based rankings (rank within research categories)

Usage:
    python rank_faculty.py                    # Rank all faculty
    python rank_faculty.py --dry-run          # Preview without saving
    python rank_faculty.py --name "Matt Cohen" # Show ranking for specific faculty

Run this AFTER running enrich_faculty.py to ensure Dimensions data is available.
"""

import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

FACULTY_DIR = Path("../data/faculty_txt")
GENERAL_INFO_DIR = Path("../data/general_info")
DATA_DIR = Path("../data")


def extract_metrics(file_path: Path) -> dict:
    """Extract Dimensions metrics from a faculty file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    metrics = {
        "name": None,
        "h_index": None,
        "total_citations": None,
        "total_publications": None,
        "field_citation_ratio": None,
        "open_access_percentage": None,
        "grant_funding": 0,
        "research_categories": [],
        "has_dimensions_data": False,
        "website": None,
        "google_scholar": None
    }

    # Extract name
    name_match = re.search(r"^Name:\s*(.+?)(?:\s*$|\s{2,})", content, re.MULTILINE)
    if name_match:
        metrics["name"] = name_match.group(1).strip()
    else:
        metrics["name"] = file_path.stem.replace("_", " ")

    # Extract Website URL
    website_match = re.search(r"^Website:\s*(.+?)$", content, re.MULTILINE)
    if website_match:
        url = website_match.group(1).strip()
        # Ensure URL has protocol
        if url and not url.startswith("http"):
            url = "https://" + url
        metrics["website"] = url

    # Extract Google Scholar URL
    gs_match = re.search(r"^Google Scholar:\s*(.+?)$", content, re.MULTILINE)
    if gs_match:
        metrics["google_scholar"] = gs_match.group(1).strip()

    # Check if file has Dimensions data
    if "--- Enriched Data (Updated:" not in content:
        return metrics

    metrics["has_dimensions_data"] = True

    # Extract H-Index
    h_match = re.search(r"H-Index:\s*(\d+)", content)
    if h_match:
        metrics["h_index"] = int(h_match.group(1))

    # Extract Total Citations
    cit_match = re.search(r"Total Citations:\s*([\d,]+)", content)
    if cit_match:
        metrics["total_citations"] = int(cit_match.group(1).replace(",", ""))

    # Extract Total Publications
    pub_match = re.search(r"Total Publications:\s*(\d+)", content)
    if pub_match:
        metrics["total_publications"] = int(pub_match.group(1))

    # Extract Field Citation Ratio
    fcr_match = re.search(r"Field Citation Ratio:\s*([\d.]+)", content)
    if fcr_match:
        metrics["field_citation_ratio"] = float(fcr_match.group(1))

    # Extract Open Access Percentage
    oa_match = re.search(r"Open Access Publications:\s*([\d.]+)%", content)
    if oa_match:
        metrics["open_access_percentage"] = float(oa_match.group(1))

    # Extract Grant Funding (sum all grants)
    grant_matches = re.findall(r"\$(\d{1,3}(?:,\d{3})*)", content)
    for grant in grant_matches:
        metrics["grant_funding"] += int(grant.replace(",", ""))

    # Extract Research Categories
    cat_match = re.search(r"Research Categories \(from Dimensions\.ai\):\s*\n(.+?)(?:\n\n|\n[A-Z])", content, re.DOTALL)
    if cat_match:
        cats = cat_match.group(1).strip()
        # Parse categories - they're semicolon separated
        metrics["research_categories"] = [c.strip() for c in cats.split(";") if c.strip()]

    return metrics


def normalize_values(values: list, inverse: bool = False) -> list:
    """
    Normalize a list of values to 0-1 scale using min-max normalization.
    Handles None values by returning None for those positions.
    """
    # Filter out None values for calculation
    valid_values = [v for v in values if v is not None]

    if not valid_values:
        return [None] * len(values)

    min_val = min(valid_values)
    max_val = max(valid_values)

    if max_val == min_val:
        # All values are the same
        return [0.5 if v is not None else None for v in values]

    normalized = []
    for v in values:
        if v is None:
            normalized.append(None)
        else:
            norm = (v - min_val) / (max_val - min_val)
            if inverse:
                norm = 1 - norm
            normalized.append(norm)

    return normalized


def compute_composite_score(h_norm, fcr_norm, cit_norm, grant_norm) -> float:
    """
    Compute composite research impact score.

    Weights:
    - H-Index (normalized): 40%
    - Field Citation Ratio (normalized): 30%
    - Citations (normalized): 20%
    - Grant Funding (normalized): 10%
    """
    weights = {
        "h_index": 0.4,
        "fcr": 0.3,
        "citations": 0.2,
        "grants": 0.1
    }

    components = [
        (h_norm, weights["h_index"]),
        (fcr_norm, weights["fcr"]),
        (cit_norm, weights["citations"]),
        (grant_norm, weights["grants"])
    ]

    # Calculate weighted sum, only using available components
    total_weight = 0
    weighted_sum = 0

    for value, weight in components:
        if value is not None:
            weighted_sum += value * weight
            total_weight += weight

    if total_weight == 0:
        return None

    # Normalize by actual weights used and scale to 0-10
    score = (weighted_sum / total_weight) * 10
    return round(score, 1)


def compute_percentile(value: float, all_values: list) -> int:
    """Compute percentile rank (0-100) for a value within a list"""
    if value is None:
        return None

    valid_values = [v for v in all_values if v is not None]
    if not valid_values:
        return None

    count_below = sum(1 for v in valid_values if v < value)
    percentile = (count_below / len(valid_values)) * 100
    return int(round(percentile))


def compute_category_rankings(faculty_metrics: list) -> dict:
    """
    Compute rankings within each research category.
    Returns dict: {faculty_name: {category: rank}}
    """
    # Group faculty by category
    category_faculty = defaultdict(list)

    for fm in faculty_metrics:
        if fm["composite_score"] is None:
            continue
        for cat in fm.get("research_categories", []):
            # Use top-level category (first part before any subdivision)
            top_cat = cat.split()[0] if cat else None
            if top_cat and top_cat.isdigit():
                # It's a FOR code like "37 Earth Sciences" - extract the name
                parts = cat.split(" ", 1)
                if len(parts) > 1:
                    top_cat = parts[1].split(";")[0].strip()
            if top_cat:
                category_faculty[top_cat].append({
                    "name": fm["name"],
                    "score": fm["composite_score"]
                })

    # Compute rankings within each category
    rankings = defaultdict(dict)

    for category, faculty_list in category_faculty.items():
        # Sort by score descending
        sorted_faculty = sorted(faculty_list, key=lambda x: x["score"], reverse=True)
        for rank, f in enumerate(sorted_faculty, 1):
            rankings[f["name"]][category] = {
                "rank": rank,
                "total": len(sorted_faculty)
            }

    return rankings


def create_ranking_section(metrics: dict, composite_score: float, percentile: int,
                           category_rankings: dict) -> str:
    """Create the ranking text section to append/update in faculty file"""

    if composite_score is None:
        return ""

    sections = []

    # Main score
    sections.append(f"""
Research Impact Score: {composite_score}/10
Percentile: Top {100 - percentile}% of Water Institute faculty""")

    # Category rankings (top 3 categories)
    if category_rankings:
        cat_lines = []
        sorted_cats = sorted(category_rankings.items(),
                           key=lambda x: x[1]["rank"])[:3]
        for cat, ranking in sorted_cats:
            cat_lines.append(f"- {cat}: #{ranking['rank']} of {ranking['total']}")

        if cat_lines:
            sections.append(f"""
Rankings by Research Category:
{chr(10).join(cat_lines)}""")

    timestamp = datetime.now().strftime("%Y-%m-%d")
    header = f"\n\n--- Research Impact Rankings (Updated: {timestamp}) ---"

    return header + "".join(sections) + "\n"


def generate_top_researchers_summary(faculty_metrics: list, category_rankings_raw: dict) -> str:
    """
    Generate a summary file with top 5 researchers per category.
    This file is used by the chatbot for quick "top researcher" queries.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"Top Researchers by Research Category (Updated: {timestamp})",
        "=" * 60,
        "",
        "This document lists the top researchers at the UF Water Institute",
        "by research category, ranked by Research Impact Score.",
        "",
        "For a complete list of researchers in any category, ask:",
        "\"Show me all researchers in [category]\" or \"Show more [category] researchers\"",
        "",
        "-" * 60,
        ""
    ]

    # Group faculty by category with full metrics
    category_faculty = defaultdict(list)
    for fm in faculty_metrics:
        if fm.get("composite_score") is None:
            continue
        for cat in fm.get("research_categories", []):
            # Clean category name
            parts = cat.split(" ", 1)
            if len(parts) > 1 and parts[0].isdigit():
                cat_name = parts[1].split(";")[0].strip()
            else:
                cat_name = cat.strip()
            if cat_name:
                category_faculty[cat_name].append({
                    "name": fm["name"],
                    "score": fm["composite_score"],
                    "h_index": fm.get("h_index"),
                    "fcr": fm.get("field_citation_ratio"),
                    "website": fm.get("website"),
                    "google_scholar": fm.get("google_scholar")
                })

    # Sort categories by number of faculty (most populated first)
    sorted_categories = sorted(category_faculty.items(),
                               key=lambda x: len(x[1]), reverse=True)

    for category, faculty_list in sorted_categories:
        if len(faculty_list) < 2:  # Skip categories with only 1 person
            continue

        # Sort by score
        sorted_faculty = sorted(faculty_list, key=lambda x: x["score"], reverse=True)

        lines.append(f"## {category}")
        lines.append(f"({len(sorted_faculty)} researchers)")
        lines.append("")

        # Top 5
        for i, f in enumerate(sorted_faculty[:5], 1):
            fcr_str = f" | FCR: {f['fcr']:.1f}x" if f.get('fcr') else ""
            h_str = f" | H-index: {f['h_index']}" if f.get('h_index') else ""
            lines.append(f"{i}. {f['name']} (Score: {f['score']}/10{h_str}{fcr_str})")

            # Add Website and Google Scholar links
            links = []
            if f.get("website"):
                links.append(f"Website: {f['website']}")
            if f.get("google_scholar"):
                links.append(f"Google Scholar: {f['google_scholar']}")
            if links:
                lines.append(f"   {' | '.join(links)}")

        if len(sorted_faculty) > 5:
            lines.append(f"   ... and {len(sorted_faculty) - 5} more researchers")

        lines.append("")

    return "\n".join(lines)


def generate_extended_rankings(faculty_metrics: list) -> str:
    """
    Generate extended rankings file with top 20 per category.
    This is used when users ask for "more" or "full list".
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"Extended Researcher Rankings by Category (Updated: {timestamp})",
        "=" * 60,
        "",
        "Complete rankings of UF Water Institute researchers by research category.",
        "Researchers are ranked by Research Impact Score (0-10 scale).",
        "",
        "-" * 60,
        ""
    ]

    # Group faculty by category
    category_faculty = defaultdict(list)
    for fm in faculty_metrics:
        if fm.get("composite_score") is None:
            continue
        for cat in fm.get("research_categories", []):
            parts = cat.split(" ", 1)
            if len(parts) > 1 and parts[0].isdigit():
                cat_name = parts[1].split(";")[0].strip()
            else:
                cat_name = cat.strip()
            if cat_name:
                category_faculty[cat_name].append({
                    "name": fm["name"],
                    "score": fm["composite_score"],
                    "h_index": fm.get("h_index"),
                    "fcr": fm.get("field_citation_ratio"),
                    "total_citations": fm.get("total_citations"),
                    "total_publications": fm.get("total_publications"),
                    "website": fm.get("website"),
                    "google_scholar": fm.get("google_scholar")
                })

    sorted_categories = sorted(category_faculty.items(),
                               key=lambda x: len(x[1]), reverse=True)

    for category, faculty_list in sorted_categories:
        if len(faculty_list) < 2:
            continue

        sorted_faculty = sorted(faculty_list, key=lambda x: x["score"], reverse=True)

        lines.append(f"## {category}")
        lines.append(f"Total researchers: {len(sorted_faculty)}")
        lines.append("")

        # Top 20 (or all if less)
        for i, f in enumerate(sorted_faculty[:20], 1):
            details = []
            if f.get('h_index'):
                details.append(f"H-index: {f['h_index']}")
            if f.get('fcr'):
                details.append(f"FCR: {f['fcr']:.1f}x")
            if f.get('total_citations'):
                details.append(f"Citations: {f['total_citations']:,}")

            detail_str = " | ".join(details) if details else ""
            lines.append(f"{i}. {f['name']}")
            lines.append(f"   Score: {f['score']}/10 | {detail_str}")

            # Add Website and Google Scholar links
            links = []
            if f.get("website"):
                links.append(f"Website: {f['website']}")
            if f.get("google_scholar"):
                links.append(f"Google Scholar: {f['google_scholar']}")
            if links:
                lines.append(f"   {' | '.join(links)}")

        if len(sorted_faculty) > 20:
            lines.append(f"\n   [{len(sorted_faculty) - 20} additional researchers not shown]")

        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    return "\n".join(lines)


def generate_rankings_json(faculty_metrics: list) -> dict:
    """
    Generate JSON data for the rankings API and frontend page.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Sort all faculty by score for overall rankings
    ranked = sorted(
        [f for f in faculty_metrics if f.get("composite_score") is not None],
        key=lambda x: x["composite_score"],
        reverse=True
    )

    # Overall top 50
    overall = []
    for f in ranked[:50]:
        overall.append({
            "name": f["name"],
            "score": f["composite_score"],
            "h_index": f.get("h_index"),
            "fcr": f.get("field_citation_ratio"),
            "citations": f.get("total_citations"),
            "publications": f.get("total_publications"),
            "website": f.get("website"),
            "google_scholar": f.get("google_scholar")
        })

    # Group by category
    category_faculty = defaultdict(list)
    for fm in faculty_metrics:
        if fm.get("composite_score") is None:
            continue
        for cat in fm.get("research_categories", []):
            parts = cat.split(" ", 1)
            if len(parts) > 1 and parts[0].isdigit():
                cat_name = parts[1].split(";")[0].strip()
            else:
                cat_name = cat.strip()
            if cat_name:
                category_faculty[cat_name].append({
                    "name": fm["name"],
                    "score": fm["composite_score"],
                    "h_index": fm.get("h_index"),
                    "fcr": fm.get("field_citation_ratio"),
                    "citations": fm.get("total_citations"),
                    "website": fm.get("website"),
                    "google_scholar": fm.get("google_scholar")
                })

    # Sort each category and keep top 20
    categories = {}
    for cat_name, faculty_list in category_faculty.items():
        if len(faculty_list) >= 3:  # Only include categories with 3+ people
            sorted_list = sorted(faculty_list, key=lambda x: x["score"], reverse=True)
            categories[cat_name] = sorted_list[:20]

    return {
        "updated": timestamp,
        "overall": overall,
        "categories": categories
    }


def generate_overall_rankings(faculty_metrics: list) -> str:
    """
    Generate overall rankings file (not by category).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Sort all faculty by score
    ranked = sorted(
        [f for f in faculty_metrics if f.get("composite_score") is not None],
        key=lambda x: x["composite_score"],
        reverse=True
    )

    lines = [
        f"Overall Research Impact Rankings (Updated: {timestamp})",
        "=" * 60,
        "",
        "All UF Water Institute researchers ranked by Research Impact Score.",
        "",
        "Score Components:",
        "- H-Index (40%): Career publication impact",
        "- Field Citation Ratio (30%): Impact relative to field average",
        "- Total Citations (20%): Raw citation count",
        "- Grant Funding (10%): Research funding success",
        "",
        "-" * 60,
        ""
    ]

    # Top 50
    lines.append("## Top 50 Researchers")
    lines.append("")

    for i, f in enumerate(ranked[:50], 1):
        cats = ", ".join(f.get("research_categories", [])[:2]) or "N/A"
        lines.append(f"{i}. {f['name']} - Score: {f['composite_score']}/10")
        lines.append(f"   H-index: {f.get('h_index', 'N/A')} | FCR: {f.get('field_citation_ratio', 'N/A')} | Categories: {cats[:50]}")

        # Add Website and Google Scholar links
        links = []
        if f.get("website"):
            links.append(f"Website: {f['website']}")
        if f.get("google_scholar"):
            links.append(f"Google Scholar: {f['google_scholar']}")
        if links:
            lines.append(f"   {' | '.join(links)}")
        lines.append("")

    return "\n".join(lines)


def update_faculty_file(file_path: Path, ranking_section: str, dry_run: bool = False) -> bool:
    """Update faculty file with ranking information"""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove old ranking section if exists
    content = re.sub(
        r"\n\n--- Research Impact Rankings \(Updated:.*?(?=\n\n---|\Z)",
        "",
        content,
        flags=re.DOTALL
    )

    if dry_run:
        print(f"   [DRY RUN] Would add ranking section")
        return True

    # Append new ranking section at the end
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + ranking_section)

    return True


def main():
    parser = argparse.ArgumentParser(description="Compute faculty research impact rankings")
    parser.add_argument("--name", type=str, help="Show ranking for specific faculty")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--stats", action="store_true", help="Show ranking statistics only")
    args = parser.parse_args()

    print("📊 Computing Faculty Research Impact Rankings\n")

    # Load all faculty metrics
    faculty_files = list(FACULTY_DIR.glob("*.txt"))
    print(f"Found {len(faculty_files)} faculty files")

    all_metrics = []
    for f in faculty_files:
        metrics = extract_metrics(f)
        metrics["file_path"] = f
        all_metrics.append(metrics)

    # Filter to those with Dimensions data
    with_data = [m for m in all_metrics if m["has_dimensions_data"]]
    print(f"Faculty with Dimensions data: {len(with_data)}")

    if not with_data:
        print("❌ No faculty have Dimensions data yet. Run enrich_faculty.py first.")
        return

    # Extract metric lists for normalization
    h_indices = [m["h_index"] for m in with_data]
    fcr_values = [m["field_citation_ratio"] for m in with_data]
    citations = [m["total_citations"] for m in with_data]
    grants = [m["grant_funding"] for m in with_data]

    # Normalize metrics
    h_norm = normalize_values(h_indices)
    fcr_norm = normalize_values(fcr_values)
    cit_norm = normalize_values(citations)
    grant_norm = normalize_values(grants)

    # Compute composite scores
    for i, m in enumerate(with_data):
        m["composite_score"] = compute_composite_score(
            h_norm[i], fcr_norm[i], cit_norm[i], grant_norm[i]
        )

    # Compute category rankings
    category_rankings = compute_category_rankings(with_data)

    # Compute percentiles
    all_scores = [m["composite_score"] for m in with_data]
    for m in with_data:
        m["percentile"] = compute_percentile(m["composite_score"], all_scores)

    # Show statistics
    valid_scores = [s for s in all_scores if s is not None]
    if valid_scores:
        print(f"\n📈 Score Statistics:")
        print(f"   Mean Score: {sum(valid_scores)/len(valid_scores):.1f}/10")
        print(f"   Max Score: {max(valid_scores):.1f}/10")
        print(f"   Min Score: {min(valid_scores):.1f}/10")

    if args.stats:
        # Show top 10
        sorted_faculty = sorted(with_data, key=lambda x: x["composite_score"] or 0, reverse=True)
        print(f"\n🏆 Top 10 Faculty by Research Impact:")
        for i, f in enumerate(sorted_faculty[:10], 1):
            print(f"   {i}. {f['name']}: {f['composite_score']}/10 (H-index: {f['h_index']}, FCR: {f['field_citation_ratio']})")
        return

    # Filter for specific faculty if requested
    if args.name:
        with_data = [m for m in with_data if args.name.lower() in m["name"].lower()]
        if not with_data:
            print(f"❌ No faculty found matching '{args.name}'")
            return

    # Update faculty files
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Updating {len(with_data)} faculty files...")

    updated = 0
    for m in with_data:
        if m["composite_score"] is None:
            continue

        cat_ranks = category_rankings.get(m["name"], {})
        ranking_section = create_ranking_section(
            m, m["composite_score"], m["percentile"], cat_ranks
        )

        if ranking_section:
            print(f"\n📝 {m['name']}: Score {m['composite_score']}/10 (Top {100 - m['percentile']}%)")
            update_faculty_file(m["file_path"], ranking_section, dry_run=args.dry_run)
            updated += 1

    print(f"\n✅ {'Would update' if args.dry_run else 'Updated'} {updated} faculty files")

    # Generate ranking summary files (use all faculty with data, not filtered)
    all_with_scores = [m for m in all_metrics if m.get("has_dimensions_data") and m.get("composite_score") is not None]

    if not args.name and all_with_scores:  # Only generate files when processing all faculty
        print(f"\n📄 Generating ranking summary files...")

        # Top researchers summary (for quick chatbot answers)
        summary = generate_top_researchers_summary(all_with_scores, category_rankings)
        summary_path = GENERAL_INFO_DIR / "top_researchers.txt"

        # Extended rankings (for "show more" requests)
        extended = generate_extended_rankings(all_with_scores)
        extended_path = GENERAL_INFO_DIR / "researcher_rankings_extended.txt"

        # Overall rankings
        overall = generate_overall_rankings(all_with_scores)
        overall_path = GENERAL_INFO_DIR / "researcher_rankings_overall.txt"

        # JSON for API/frontend
        rankings_json = generate_rankings_json(all_with_scores)
        json_path = DATA_DIR / "rankings.json"

        if args.dry_run:
            print(f"   [DRY RUN] Would create: {summary_path.name}")
            print(f"   [DRY RUN] Would create: {extended_path.name}")
            print(f"   [DRY RUN] Would create: {overall_path.name}")
            print(f"   [DRY RUN] Would create: {json_path.name}")
        else:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"   ✅ Created: {summary_path.name}")

            with open(extended_path, "w", encoding="utf-8") as f:
                f.write(extended)
            print(f"   ✅ Created: {extended_path.name}")

            with open(overall_path, "w", encoding="utf-8") as f:
                f.write(overall)
            print(f"   ✅ Created: {overall_path.name}")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rankings_json, f, indent=2)
            print(f"   ✅ Created: {json_path.name} (for rankings page)")

    if not args.dry_run and updated > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Run: python ingest_faculty.py")
        print(f"   2. Redeploy to update the live chatbot")


if __name__ == "__main__":
    main()
