"""
Test Suite for New Features

Tests the recent changes:
1. Topic-specific expert ranking files (PFAS, hydrology, etc.)
2. Follow-up "show more" query handling
3. New staff/student profiles

Usage:
    python test_new_features.py                # Test against production API
    python test_new_features.py --local        # Test against localhost:8000
"""

import requests
import json
import argparse
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# API endpoints
PROD_API = "https://water-institute-chatbot.onrender.com"
LOCAL_API = "http://localhost:8000"


@dataclass
class TestResult:
    name: str
    passed: bool
    response: str
    details: str
    response_time: float


def send_chat(api_url: str, message: str, conversation_history: List[Dict] = None) -> dict:
    """Send a chat request to the API"""
    payload = {
        "message": message,
        "conversation_history": conversation_history or []
    }

    start = time.time()
    resp = requests.post(f"{api_url}/chat", json=payload, timeout=60)
    elapsed = time.time() - start

    if resp.status_code != 200:
        return {"response": f"ERROR: {resp.status_code}", "sources": [], "time": elapsed}

    data = resp.json()
    data["time"] = elapsed
    return data


def test_pfas_experts(api_url: str) -> TestResult:
    """Test that PFAS query returns correct curated experts"""
    result = send_chat(api_url, "Who are the top PFAS researchers?")
    response = result.get("response", "").lower()

    # Expected experts from our curated file (in order of importance)
    expected_experts = ["bowden", "deliz", "katherine"]  # Top experts
    good_experts = ["tracie baker", "bridget baker", "denslow"]  # Also acceptable

    found_expected = [exp for exp in expected_experts if exp in response]
    found_good = [exp for exp in good_experts if exp in response]

    # Check if at least 2 of the top 3 expected experts are mentioned
    passed = len(found_expected) >= 2 or (len(found_expected) >= 1 and len(found_good) >= 1)

    details = f"Found expected: {found_expected}, Found good: {found_good}"
    if not passed:
        details += f"\nResponse may be using old rankings instead of curated PFAS file"

    return TestResult(
        name="PFAS Experts Query",
        passed=passed,
        response=result.get("response", "")[:500],
        details=details,
        response_time=result.get("time", 0)
    )


def test_hydrology_experts(api_url: str) -> TestResult:
    """Test that hydrology query returns correct curated experts"""
    result = send_chat(api_url, "Who are the top hydrology researchers?")
    response = result.get("response", "").lower()

    # Expected experts from our curated hydrology file
    expected_experts = ["cohen", "kaplan", "jawitz", "graham", "munoz-carpena"]

    found = [exp for exp in expected_experts if exp in response]
    passed = len(found) >= 2

    return TestResult(
        name="Hydrology Experts Query",
        passed=passed,
        response=result.get("response", "")[:500],
        details=f"Found expected experts: {found}",
        response_time=result.get("time", 0)
    )


def test_habs_experts(api_url: str) -> TestResult:
    """Test that HABs query returns correct curated experts"""
    result = send_chat(api_url, "Who studies harmful algal blooms?")
    response = result.get("response", "").lower()

    # Expected experts from our curated HABs file
    expected_experts = ["phlips", "laughinghouse", "kaplan"]

    found = [exp for exp in expected_experts if exp in response]
    passed = len(found) >= 1

    return TestResult(
        name="HABs Experts Query",
        passed=passed,
        response=result.get("response", "")[:500],
        details=f"Found expected experts: {found}",
        response_time=result.get("time", 0)
    )


def test_followup_show_more(api_url: str) -> TestResult:
    """Test that follow-up 'yes' query retrieves more researchers"""
    # First query
    result1 = send_chat(api_url, "Who are the top PFAS researchers?")

    # Build conversation history
    history = [
        {"role": "user", "content": "Who are the top PFAS researchers?"},
        {"role": "assistant", "content": result1.get("response", "")}
    ]

    # Follow-up query
    result2 = send_chat(api_url, "yes", history)
    response = result2.get("response", "").lower()

    # Should NOT be rejected as off-topic
    off_topic_indicators = ["i'm designed to help", "off-topic", "unrelated"]
    is_off_topic = any(ind in response for ind in off_topic_indicators)

    # Should contain more researcher names or details
    has_content = len(response) > 100 and ("researcher" in response or "expert" in response or any(name in response for name in ["annable", "zimmerman", "osborne", "martyniuk"]))

    passed = not is_off_topic and has_content

    details = "Follow-up rejected as off-topic" if is_off_topic else "Follow-up accepted"
    if has_content:
        details += ", contains additional researcher info"

    return TestResult(
        name="Follow-up 'Show More' Query",
        passed=passed,
        response=result2.get("response", "")[:500],
        details=details,
        response_time=result2.get("time", 0)
    )


def test_new_staff_profiles(api_url: str) -> List[TestResult]:
    """Test that new staff profiles are accessible"""
    results = []

    new_staff = [
        ("Nathan Reaver", ["reaver", "hydrology", "springs", "karst"]),
        ("Darlene Velez", ["velez", "environmental"]),
        ("Nicolas Fernandez", ["fernandez", "data science", "water quality"]),
        ("Sarah Marc", ["marc", "communications"]),
    ]

    for name, keywords in new_staff:
        result = send_chat(api_url, f"Tell me about {name}")
        response = result.get("response", "").lower()

        found = [kw for kw in keywords if kw in response]
        # Pass if at least 1 keyword found (profile exists)
        passed = len(found) >= 1

        results.append(TestResult(
            name=f"New Profile: {name}",
            passed=passed,
            response=result.get("response", "")[:300],
            details=f"Found keywords: {found}" if found else "Profile may not be ingested yet",
            response_time=result.get("time", 0)
        ))

    return results


def test_wendy_graham_nsf(api_url: str) -> TestResult:
    """Test that Wendy Graham's profile includes NSF role"""
    result = send_chat(api_url, "Tell me about Wendy Graham's current position")
    response = result.get("response", "").lower()

    # Should mention NSF role
    nsf_indicators = ["nsf", "national science foundation", "division director", "rise", "geosciences"]
    found = [ind for ind in nsf_indicators if ind in response]

    passed = len(found) >= 1

    return TestResult(
        name="Wendy Graham NSF Role",
        passed=passed,
        response=result.get("response", "")[:500],
        details=f"Found NSF indicators: {found}" if found else "NSF role not mentioned - may need re-ingest",
        response_time=result.get("time", 0)
    )


def run_tests(api_url: str, verbose: bool = False):
    """Run all tests and report results"""
    print(f"\n{'='*60}")
    print(f"Testing API: {api_url}")
    print(f"{'='*60}\n")

    all_results = []

    # Category-specific expert tests
    print("Testing Topic-Specific Expert Queries...")
    all_results.append(test_pfas_experts(api_url))
    all_results.append(test_hydrology_experts(api_url))
    all_results.append(test_habs_experts(api_url))

    # Follow-up test
    print("Testing Follow-up Query Handling...")
    all_results.append(test_followup_show_more(api_url))

    # New profile tests
    print("Testing New Staff Profiles...")
    all_results.extend(test_new_staff_profiles(api_url))

    # Updated profile test
    print("Testing Profile Updates...")
    all_results.append(test_wendy_graham_nsf(api_url))

    # Report results
    print(f"\n{'='*60}")
    print("TEST RESULTS")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    for result in all_results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} | {result.name} ({result.response_time:.1f}s)")
        print(f"       {result.details}")

        if verbose or not result.passed:
            print(f"       Response: {result.response[:200]}...")
        print()

        if result.passed:
            passed += 1
        else:
            failed += 1

    # Summary
    total = passed + failed
    print(f"{'='*60}")
    print(f"SUMMARY: {passed}/{total} tests passed ({100*passed/total:.0f}%)")
    print(f"{'='*60}")

    if failed > 0:
        print("\n⚠️  Some tests failed. This may indicate:")
        print("   - Production needs to re-ingest data (new category files)")
        print("   - Production needs to redeploy (code changes)")

    return passed, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test new chatbot features")
    parser.add_argument("--local", action="store_true", help="Test against localhost:8000")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full responses")
    args = parser.parse_args()

    api_url = LOCAL_API if args.local else PROD_API
    run_tests(api_url, args.verbose)
