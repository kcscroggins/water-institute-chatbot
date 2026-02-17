"""
Comprehensive Chatbot Test Suite

Tests the Water Institute chatbot against various query types to validate:
- Faculty rankings queries
- Faculty profile queries (enriched data)
- General institute information
- Edge cases and error handling

Usage:
    python test_chatbot.py                    # Test against production API
    python test_chatbot.py --local            # Test against localhost:8000
    python test_chatbot.py --verbose          # Show full responses
"""

import requests
import json
import argparse
import time
from dataclasses import dataclass
from typing import List, Optional

# API endpoints
PROD_API = "https://water-institute-chatbot.onrender.com"
LOCAL_API = "http://localhost:8000"


@dataclass
class TestCase:
    """A single test case"""
    category: str
    query: str
    expected_keywords: List[str]  # Keywords that should appear in response
    should_not_contain: Optional[List[str]] = None  # Keywords that should NOT appear


@dataclass
class TestResult:
    """Result of a single test"""
    test_case: TestCase
    passed: bool
    response: str
    sources: List[str]
    missing_keywords: List[str]
    forbidden_keywords: List[str]
    response_time: float


# =============================================================================
# TEST CASES
# =============================================================================

RANKINGS_TESTS = [
    TestCase(
        category="Rankings",
        query="Who are the top researchers at the Water Institute?",
        expected_keywords=["Zimmerman", "Kaplan", "score", "impact"],
    ),
    TestCase(
        category="Rankings",
        query="What is Andrew Zimmerman's research impact score?",
        expected_keywords=["Zimmerman", "6.4", "Environmental"],
    ),
    TestCase(
        category="Rankings",
        query="Which faculty have the highest h-index?",
        expected_keywords=["h-index", "Zimmerman"],
    ),
    TestCase(
        category="Rankings",
        query="Who are the top environmental sciences researchers?",
        expected_keywords=["Environmental", "Zimmerman"],
    ),
    TestCase(
        category="Rankings",
        query="Tell me about David Kaplan's research ranking",
        expected_keywords=["Kaplan", "score"],
    ),
    TestCase(
        category="Rankings",
        query="What is the Field Citation Ratio used for?",
        expected_keywords=["citation", "impact", "field"],
    ),
    TestCase(
        category="Rankings",
        query="How are faculty research scores calculated?",
        expected_keywords=["H-Index", "citation", "score"],
    ),
]

FACULTY_PROFILE_TESTS = [
    TestCase(
        category="Faculty Profile",
        query="Tell me about Matt Cohen's research",
        expected_keywords=["Cohen", "Water Institute", "hydrology"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Lisa Krimsky's expertise?",
        expected_keywords=["Krimsky", "Extension", "water"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Who studies water quality at the Water Institute?",
        expected_keywords=["water quality"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What are Wendy Graham's publications?",
        expected_keywords=["Graham", "research"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Sabine Grunwald's education",
        expected_keywords=["Grunwald", "Ph.D."],
    ),
    TestCase(
        category="Faculty Profile",
        query="What awards has Peter Frederick received?",
        expected_keywords=["Frederick"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Who works on climate change?",
        expected_keywords=["climate"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Which faculty study coastal ecosystems?",
        expected_keywords=["coastal"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Gerrit Hoogenboom",
        expected_keywords=["Hoogenboom", "Agricultural"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Nancy Denslow's research focus?",
        expected_keywords=["Denslow"],
    ),
]

GENERAL_INSTITUTE_TESTS = [
    TestCase(
        category="General Institute",
        query="What is the Water Institute?",
        expected_keywords=["Water Institute", "UF", "research"],
    ),
    TestCase(
        category="General Institute",
        query="Where is the Water Institute located?",
        expected_keywords=["Weil Hall", "Gainesville"],
    ),
    TestCase(
        category="General Institute",
        query="Who is the director of the Water Institute?",
        expected_keywords=["Cohen", "director"],
    ),
    TestCase(
        category="General Institute",
        query="What programs does the Water Institute offer?",
        expected_keywords=["program", "graduate", "fellow"],
    ),
    TestCase(
        category="General Institute",
        query="How much research funding does the Water Institute have?",
        expected_keywords=["million", "research", "funding"],
    ),
    TestCase(
        category="General Institute",
        query="What are the main research areas?",
        expected_keywords=["research", "water"],
    ),
    TestCase(
        category="General Institute",
        query="What partnerships does the Water Institute have?",
        expected_keywords=["partner"],
    ),
    TestCase(
        category="General Institute",
        query="How can I contact the Water Institute?",
        expected_keywords=["contact", "email"],
    ),
]

EDGE_CASE_TESTS = [
    TestCase(
        category="Edge Case",
        query="Who is John?",
        expected_keywords=["John"],  # Should find faculty with John in name
    ),
    TestCase(
        category="Edge Case",
        query="Tell me about hydrology research",
        expected_keywords=["hydrology", "water"],
    ),
    TestCase(
        category="Edge Case",
        query="faculty studying everglades",
        expected_keywords=["Everglades"],
    ),
    TestCase(
        category="Edge Case",
        query="What is WIGF?",
        expected_keywords=["Graduate", "Fellow"],
    ),
    TestCase(
        category="Edge Case",
        query="Tell me about someone who studies fish",
        expected_keywords=["fish"],
    ),
]

OFF_TOPIC_TESTS = [
    TestCase(
        category="Off-Topic Guard",
        query="What's the weather today?",
        expected_keywords=["Water Institute", "can't", "don't"],
        should_not_contain=["sunny", "rain", "temperature", "forecast"],
    ),
    TestCase(
        category="Off-Topic Guard",
        query="Write me a poem about the ocean",
        expected_keywords=["Water Institute"],
        should_not_contain=["waves crash", "blue sea"],
    ),
]


def run_test(api_url: str, test_case: TestCase, verbose: bool = False) -> TestResult:
    """Run a single test case against the API"""
    start_time = time.time()

    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"message": test_case.query, "conversation_history": []},
            timeout=60
        )
        response_time = time.time() - start_time

        if response.status_code != 200:
            return TestResult(
                test_case=test_case,
                passed=False,
                response=f"HTTP Error: {response.status_code}",
                sources=[],
                missing_keywords=test_case.expected_keywords,
                forbidden_keywords=[],
                response_time=response_time
            )

        data = response.json()
        bot_response = data.get("response", "").lower()
        sources = data.get("sources", [])

        # Check for expected keywords
        missing_keywords = []
        for keyword in test_case.expected_keywords:
            if keyword.lower() not in bot_response:
                missing_keywords.append(keyword)

        # Check for forbidden keywords
        forbidden_keywords = []
        if test_case.should_not_contain:
            for keyword in test_case.should_not_contain:
                if keyword.lower() in bot_response:
                    forbidden_keywords.append(keyword)

        passed = len(missing_keywords) == 0 and len(forbidden_keywords) == 0

        return TestResult(
            test_case=test_case,
            passed=passed,
            response=data.get("response", ""),
            sources=sources,
            missing_keywords=missing_keywords,
            forbidden_keywords=forbidden_keywords,
            response_time=response_time
        )

    except requests.exceptions.Timeout:
        return TestResult(
            test_case=test_case,
            passed=False,
            response="Request timed out",
            sources=[],
            missing_keywords=test_case.expected_keywords,
            forbidden_keywords=[],
            response_time=60.0
        )
    except Exception as e:
        return TestResult(
            test_case=test_case,
            passed=False,
            response=f"Error: {str(e)}",
            sources=[],
            missing_keywords=test_case.expected_keywords,
            forbidden_keywords=[],
            response_time=time.time() - start_time
        )


def print_result(result: TestResult, verbose: bool = False):
    """Print a single test result"""
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"\n{status} [{result.test_case.category}]")
    print(f"   Query: \"{result.test_case.query}\"")
    print(f"   Time: {result.response_time:.2f}s")

    if not result.passed:
        if result.missing_keywords:
            print(f"   Missing keywords: {result.missing_keywords}")
        if result.forbidden_keywords:
            print(f"   Forbidden keywords found: {result.forbidden_keywords}")

    if result.sources:
        print(f"   Sources: {result.sources[:3]}{'...' if len(result.sources) > 3 else ''}")

    if verbose or not result.passed:
        # Truncate response for display
        response_preview = result.response[:300] + "..." if len(result.response) > 300 else result.response
        print(f"   Response: {response_preview}")


def run_test_suite(api_url: str, verbose: bool = False):
    """Run all test cases"""
    all_tests = (
        RANKINGS_TESTS +
        FACULTY_PROFILE_TESTS +
        GENERAL_INSTITUTE_TESTS +
        EDGE_CASE_TESTS +
        OFF_TOPIC_TESTS
    )

    print("=" * 70)
    print("UF WATER INSTITUTE CHATBOT TEST SUITE")
    print("=" * 70)
    print(f"API: {api_url}")
    print(f"Total tests: {len(all_tests)}")
    print("=" * 70)

    # Check API health first
    try:
        health = requests.get(f"{api_url}/health", timeout=30)
        if health.status_code == 200:
            health_data = health.json()
            print(f"API Status: Healthy")
            print(f"Collection Count: {health_data.get('collection_count', 'N/A')}")
        else:
            print(f"API Status: Unhealthy (HTTP {health.status_code})")
    except Exception as e:
        print(f"API Status: Cannot connect - {e}")
        return

    print("=" * 70)

    results = []
    categories = {}

    for i, test_case in enumerate(all_tests, 1):
        print(f"\nRunning test {i}/{len(all_tests)}...", end="", flush=True)
        result = run_test(api_url, test_case, verbose)
        results.append(result)
        print_result(result, verbose)

        # Track by category
        if test_case.category not in categories:
            categories[test_case.category] = {"passed": 0, "failed": 0}
        if result.passed:
            categories[test_case.category]["passed"] += 1
        else:
            categories[test_case.category]["failed"] += 1

        # Small delay to avoid overwhelming the API
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total_passed = sum(1 for r in results if r.passed)
    total_failed = len(results) - total_passed

    print(f"\nOverall: {total_passed}/{len(results)} passed ({100*total_passed/len(results):.1f}%)")
    print(f"\nBy Category:")
    for category, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        pct = 100 * stats["passed"] / total if total > 0 else 0
        status = "✅" if stats["failed"] == 0 else "⚠️" if pct >= 50 else "❌"
        print(f"  {status} {category}: {stats['passed']}/{total} ({pct:.0f}%)")

    avg_time = sum(r.response_time for r in results) / len(results)
    print(f"\nAverage response time: {avg_time:.2f}s")

    # List failed tests
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        print(f"\n⚠️  FAILED TESTS ({len(failed_tests)}):")
        for r in failed_tests:
            print(f"  - [{r.test_case.category}] \"{r.test_case.query}\"")

    print("\n" + "=" * 70)

    return results


def main():
    parser = argparse.ArgumentParser(description="Test the Water Institute chatbot")
    parser.add_argument("--local", action="store_true", help="Test against localhost:8000")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full responses")
    args = parser.parse_args()

    api_url = LOCAL_API if args.local else PROD_API
    run_test_suite(api_url, args.verbose)


if __name__ == "__main__":
    main()
