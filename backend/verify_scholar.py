#!/usr/bin/env python3
"""
Verify Google Scholar profile links in faculty .txt files.

Fetches each Scholar profile page and compares the profile name against
the faculty name using fuzzy matching. Optionally cross-references
publication titles from the Scholar profile against Dimensions publications
already in the .txt file.

Usage:
    python verify_scholar.py                        # Check all faculty
    python verify_scholar.py --name "Andrew Zimmerman"  # Check single faculty
"""

import argparse
import difflib
import os
import re
import time
import random
import html

import requests

FACULTY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "faculty_txt")

# Common first-name variants for matching
NAME_VARIANTS = {
    "matt": "matthew",
    "mike": "michael",
    "rob": "robert",
    "bob": "robert",
    "bill": "william",
    "will": "william",
    "jim": "james",
    "jimmy": "james",
    "joe": "joseph",
    "dan": "daniel",
    "danny": "daniel",
    "dave": "david",
    "ed": "edward",
    "ted": "edward",
    "alex": "alexander",
    "chris": "christopher",
    "tom": "thomas",
    "tony": "anthony",
    "dick": "richard",
    "rick": "richard",
    "rich": "richard",
    "steve": "steven",
    "stu": "stuart",
    "nick": "nicholas",
    "pat": "patricia",
    "patty": "patricia",
    "liz": "elizabeth",
    "beth": "elizabeth",
    "kate": "katherine",
    "cathy": "catherine",
    "kathy": "katherine",
    "jen": "jennifer",
    "jenny": "jennifer",
    "meg": "margaret",
    "peggy": "margaret",
    "sue": "susan",
    "deb": "deborah",
    "debbie": "deborah",
    "sam": "samuel",
    "ben": "benjamin",
    "jon": "jonathan",
    "andy": "andrew",
    "drew": "andrew",
    "greg": "gregory",
    "jeff": "jeffrey",
    "jerry": "gerald",
    "larry": "lawrence",
    "phil": "philip",
    "ray": "raymond",
    "ron": "ronald",
    "tim": "timothy",
    "walt": "walter",
}

# Reverse mapping so we can canonicalize both directions
_reverse = {}
for short, full in NAME_VARIANTS.items():
    _reverse.setdefault(full, full)
    _reverse.setdefault(short, full)
NAME_CANON = _reverse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_faculty_file(filepath):
    """Extract faculty name, Scholar URL, and publication titles from a .txt file."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Faculty name from filename
    basename = os.path.splitext(os.path.basename(filepath))[0]
    parts = basename.split("_")
    if len(parts) == 2:
        faculty_name = f"{parts[1]} {parts[0]}"  # "Andrew Zimmerman"
    else:
        faculty_name = " ".join(reversed(parts))

    # Google Scholar URL
    scholar_match = re.search(r"Google Scholar:\s*(https?://scholar\.google\.com/\S+)", text)
    scholar_url = scholar_match.group(1) if scholar_match else None

    # Publication titles from Dimensions data (Top Cited + Recent)
    pub_titles = []
    for m in re.finditer(r"^- (.+?)(?:\s*\*)", text, re.MULTILINE):
        title = m.group(1).strip()
        if title and len(title) > 10:  # skip short/junk entries
            pub_titles.append(title)

    return faculty_name, scholar_url, pub_titles


def fetch_scholar_profile(url):
    """Fetch a Google Scholar profile page and extract name + publication titles."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    page = resp.text

    # Check for CAPTCHA / blocking
    if "Please show you" in page or "unusual traffic" in page:
        return None, [], True  # blocked

    # Extract profile name
    name_match = re.search(r'id="gsc_prf_in"[^>]*>(.*?)<', page)
    profile_name = html.unescape(name_match.group(1).strip()) if name_match else None

    # Extract publication titles
    pub_titles = []
    for m in re.finditer(r'class="gsc_a_at"[^>]*>(.*?)<', page):
        title = html.unescape(m.group(1).strip())
        if title:
            pub_titles.append(title)

    return profile_name, pub_titles, False


def normalize_name(name):
    """Normalize a name for comparison: lowercase, strip titles/suffixes/middle initials."""
    name = name.lower().strip()
    # Remove common titles and suffixes
    name = re.sub(
        r"\b(dr|prof|professor|ph\.?d|m\.?d|m\.?s|jr|sr|ii|iii|iv|p\.?e\.?)\b\.?",
        "",
        name,
    )
    # Remove single-letter middle initials (e.g. "James W Jawitz" -> "James Jawitz")
    name = re.sub(r"\b[a-z]\b\.?", "", name)
    # Remove extra whitespace and punctuation
    name = re.sub(r"[.,;:()\-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def canonicalize_first_name(name):
    """Replace common nicknames with canonical form."""
    return NAME_CANON.get(name, name)


def name_match_ratio(faculty_name, profile_name):
    """Compute a fuzzy match ratio between two names, accounting for variants."""
    fn = normalize_name(faculty_name)
    pn = normalize_name(profile_name)

    # Direct ratio
    ratio = difflib.SequenceMatcher(None, fn, pn).ratio()

    # Try with canonicalized first names
    fn_parts = fn.split()
    pn_parts = pn.split()
    if fn_parts and pn_parts:
        fn_canon = [canonicalize_first_name(fn_parts[0])] + fn_parts[1:]
        pn_canon = [canonicalize_first_name(pn_parts[0])] + pn_parts[1:]
        canon_ratio = difflib.SequenceMatcher(
            None, " ".join(fn_canon), " ".join(pn_canon)
        ).ratio()
        ratio = max(ratio, canon_ratio)

        # Also try matching just last names (handles different first-name orderings)
        if fn_parts[-1] == pn_parts[-1]:
            ratio = max(ratio, 0.7)  # same last name is a decent signal

    return ratio


def pub_overlap_count(faculty_pubs, scholar_pubs):
    """Count how many faculty publications appear in the Scholar profile (fuzzy)."""
    if not faculty_pubs or not scholar_pubs:
        return 0, max(len(faculty_pubs), len(scholar_pubs))

    scholar_lower = [t.lower() for t in scholar_pubs]
    matches = 0
    for ft in faculty_pubs:
        ft_lower = ft.lower()
        for st in scholar_lower:
            ratio = difflib.SequenceMatcher(None, ft_lower, st).ratio()
            if ratio > 0.75:
                matches += 1
                break

    return matches, len(faculty_pubs)


def check_faculty(filepath, verbose=False):
    """Check a single faculty file. Returns a result dict."""
    faculty_name, scholar_url, faculty_pubs = parse_faculty_file(filepath)
    filename = os.path.basename(filepath)

    if not scholar_url:
        return {"filename": filename, "status": "no_url"}

    try:
        profile_name, scholar_pubs, blocked = fetch_scholar_profile(scholar_url)
    except Exception as e:
        return {
            "filename": filename,
            "faculty_name": faculty_name,
            "status": "error",
            "error": str(e),
        }

    if blocked:
        return {
            "filename": filename,
            "faculty_name": faculty_name,
            "status": "blocked",
        }

    if not profile_name:
        return {
            "filename": filename,
            "faculty_name": faculty_name,
            "status": "no_profile_name",
        }

    ratio = name_match_ratio(faculty_name, profile_name)
    overlap, total_pubs = pub_overlap_count(faculty_pubs, scholar_pubs)

    if ratio < 0.6:
        status = "mismatch"
    elif ratio < 0.8:
        status = "review"
    else:
        status = "verified"

    result = {
        "filename": filename,
        "faculty_name": faculty_name,
        "profile_name": profile_name,
        "ratio": ratio,
        "pub_overlap": overlap,
        "pub_total": total_pubs,
        "status": status,
        "url": scholar_url,
    }

    if verbose:
        print(f"  {filename} — Faculty: {faculty_name}, Scholar: {profile_name} "
              f"(ratio: {ratio:.2f}, {overlap}/{total_pubs} pub overlap) [{status}]")

    return result


def main():
    parser = argparse.ArgumentParser(description="Verify Google Scholar profile links")
    parser.add_argument("--name", type=str, help='Check single faculty member, e.g. "Andrew Zimmerman"')
    parser.add_argument("--delay", type=float, default=4.0, help="Delay between requests in seconds (default: 4)")
    parser.add_argument("--verbose", action="store_true", help="Print each result as it's checked")
    args = parser.parse_args()

    faculty_dir = os.path.abspath(FACULTY_DIR)
    if not os.path.isdir(faculty_dir):
        print(f"Error: Faculty directory not found: {faculty_dir}")
        return

    # Collect files to check
    if args.name:
        # Find matching file
        name_parts = args.name.strip().split()
        if len(name_parts) >= 2:
            # Try LastName_FirstName.txt pattern
            candidates = [
                f"{name_parts[-1]}_{name_parts[0]}.txt",
                f"{'_'.join(reversed(name_parts))}.txt",
            ]
        else:
            candidates = [f"{args.name}.txt"]

        filepath = None
        for c in candidates:
            p = os.path.join(faculty_dir, c)
            if os.path.exists(p):
                filepath = p
                break

        if not filepath:
            # Fuzzy search
            all_files = [f for f in os.listdir(faculty_dir) if f.endswith(".txt")]
            search = args.name.lower().replace(" ", "_")
            matches = [f for f in all_files if search in f.lower() or f.lower().replace(".txt", "") in search]
            if matches:
                filepath = os.path.join(faculty_dir, matches[0])
            else:
                print(f"Could not find faculty file for: {args.name}")
                return

        print(f"Checking: {os.path.basename(filepath)}")
        result = check_faculty(filepath, verbose=True)
        if result["status"] == "mismatch":
            print(f"\n  MISMATCH: Faculty '{result['faculty_name']}' vs Scholar '{result['profile_name']}'")
            print(f"  Ratio: {result['ratio']:.2f}, Pub overlap: {result['pub_overlap']}/{result['pub_total']}")
            print(f"  URL: {result['url']}")
        elif result["status"] == "review":
            print(f"\n  REVIEW RECOMMENDED: ratio {result['ratio']:.2f}")
        elif result["status"] == "verified":
            print(f"\n  VERIFIED: names match (ratio {result['ratio']:.2f})")
        elif result["status"] == "error":
            print(f"\n  ERROR: {result.get('error', 'unknown')}")
        elif result["status"] == "blocked":
            print("\n  BLOCKED by Google Scholar (CAPTCHA). Try again later.")
        return

    # Check all faculty
    all_files = sorted(
        os.path.join(faculty_dir, f)
        for f in os.listdir(faculty_dir)
        if f.endswith(".txt")
    )

    print(f"Checking {len(all_files)} faculty files for Google Scholar profile mismatches...")
    print(f"Delay between requests: {args.delay}s\n")

    results = {"mismatch": [], "review": [], "verified": [], "no_url": [], "error": [], "blocked": [], "no_profile_name": []}

    for i, filepath in enumerate(all_files):
        # Quick parse to skip files without Scholar URLs
        _, scholar_url, _ = parse_faculty_file(filepath)
        if not scholar_url:
            results["no_url"].append({"filename": os.path.basename(filepath), "status": "no_url"})
            continue

        result = check_faculty(filepath, verbose=args.verbose)
        results[result["status"]].append(result)

        # Rate limit
        if i < len(all_files) - 1:
            delay = args.delay + random.uniform(-1, 1)
            delay = max(2, delay)
            time.sleep(delay)

        # Progress update every 25 files
        checked = sum(len(v) for k, v in results.items() if k != "no_url")
        if checked % 25 == 0 and checked > 0:
            total_with_url = len(all_files) - len(results["no_url"])
            print(f"  Progress: {checked}/{total_with_url} checked...")

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    if results["mismatch"]:
        print(f"\nMISMATCHES FOUND ({len(results['mismatch'])}):")
        for r in results["mismatch"]:
            print(f"  {r['filename']} — Faculty: {r['faculty_name']}, Scholar: {r['profile_name']} "
                  f"(ratio: {r['ratio']:.2f}, {r['pub_overlap']}/{r['pub_total']} pub overlap)")

    if results["review"]:
        print(f"\nREVIEW RECOMMENDED ({len(results['review'])}):")
        for r in results["review"]:
            print(f"  {r['filename']} — Faculty: {r['faculty_name']}, Scholar: {r['profile_name']} "
                  f"(ratio: {r['ratio']:.2f}, {r['pub_overlap']}/{r['pub_total']} pub overlap)")

    if results["error"]:
        print(f"\nERRORS ({len(results['error'])}):")
        for r in results["error"]:
            print(f"  {r['filename']} — {r.get('error', 'unknown')}")

    if results["blocked"]:
        print(f"\nBLOCKED ({len(results['blocked'])}): Google Scholar returned CAPTCHA for these.")
        for r in results["blocked"]:
            print(f"  {r['filename']}")

    total = len(all_files)
    with_url = total - len(results["no_url"])
    verified = len(results["verified"])
    print(f"\nVERIFIED: {verified}/{with_url} (of {total} total faculty files, {len(results['no_url'])} have no Scholar URL)")


if __name__ == "__main__":
    main()
