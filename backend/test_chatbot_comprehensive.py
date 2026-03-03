"""
Comprehensive Chatbot Test Suite - 100+ Test Cases

Tests the Water Institute chatbot against various query types to validate:
- Faculty profile queries (specific and general)
- Rankings queries (overall and topic-specific)
- General institute information
- Topic-specific expert queries
- Research area queries
- Edge cases and error handling
- Off-topic guardrails

Usage:
    python test_chatbot_comprehensive.py                    # Test against production API
    python test_chatbot_comprehensive.py --local            # Test against localhost:8000
    python test_chatbot_comprehensive.py --verbose          # Show full responses
    python test_chatbot_comprehensive.py --category faculty # Run only faculty tests
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
# TEST CASES - FACULTY PROFILES (30 tests)
# =============================================================================

FACULTY_PROFILE_TESTS = [
    # Director and Leadership
    TestCase(
        category="Faculty Profile",
        query="Tell me about Matt Cohen's research",
        expected_keywords=["Cohen", "Water Institute", "ecohydrology"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Who is the director of the Water Institute?",
        expected_keywords=["Cohen", "director"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Matt Cohen's email?",
        expected_keywords=["Cohen", "mjc@ufl.edu"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Wendy Graham",
        expected_keywords=["Graham", "founding", "director"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What does Wendy Graham do at NSF?",
        expected_keywords=["Graham", "NSF", "Division"],
    ),

    # Specific Faculty Research
    TestCase(
        category="Faculty Profile",
        query="What is David Kaplan's expertise?",
        expected_keywords=["Kaplan", "wetland", "hydrology"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about David Kaplan's role at H.T. Odum Center",
        expected_keywords=["Kaplan", "Odum", "Wetlands"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Lisa Krimsky's expertise?",
        expected_keywords=["Krimsky", "Extension", "water"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Lisa Krimsky's work on harmful algal blooms",
        expected_keywords=["Krimsky", "algal", "bloom"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Andrew Zimmerman's research focus?",
        expected_keywords=["Zimmerman", "carbon", "geochemist"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Zimmerman's work on biochar",
        expected_keywords=["Zimmerman", "biochar"],
    ),

    # Education and Credentials
    TestCase(
        category="Faculty Profile",
        query="Where did Matt Cohen get his PhD?",
        expected_keywords=["Cohen", "PhD", "Florida"],  # Accept PhD without periods
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Wendy Graham's educational background?",
        expected_keywords=["Graham", "Ph.D.", "MIT"],
    ),

    # Publications and Awards
    TestCase(
        category="Faculty Profile",
        query="What are Matt Cohen's notable publications?",
        expected_keywords=["Cohen", "publication"],
    ),
    TestCase(
        category="Faculty Profile",
        query="How many citations does Andrew Zimmerman have?",
        expected_keywords=["Zimmerman", "citation"],
    ),

    # Research Areas
    TestCase(
        category="Faculty Profile",
        query="Who studies water quality at the Water Institute?",
        expected_keywords=["water quality"],
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
        query="Who studies groundwater at UF?",
        expected_keywords=["groundwater"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Which researchers study nutrient pollution?",
        expected_keywords=["nutrient"],
    ),

    # Department-based queries
    TestCase(
        category="Faculty Profile",
        query="Who are the faculty from Soil and Water Sciences?",
        expected_keywords=["Soil", "Water"],
    ),
    TestCase(
        category="Faculty Profile",
        query="List faculty from Environmental Engineering Sciences",
        expected_keywords=["Environmental Engineering"],
    ),

    # Specific lesser-known faculty
    TestCase(
        category="Faculty Profile",
        query="Tell me about Glenn Acomb's research",
        expected_keywords=["Acomb", "green roof"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What is John Bowden's expertise?",
        expected_keywords=["Bowden", "PFAS"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Katherine Deliz Quinones",
        expected_keywords=["Deliz", "PFAS"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What does Tracie Baker study?",
        expected_keywords=["Baker", "toxicolog"],  # Matches toxicology/toxicologist
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Todd Osborne's research",
        expected_keywords=["Osborne", "soil"],  # Osborne works on soil/wetland biogeochemistry
    ),
    TestCase(
        category="Faculty Profile",
        query="What is Mark Clark's expertise?",
        expected_keywords=["Clark", "wetland"],
    ),
    TestCase(
        category="Faculty Profile",
        query="Tell me about Konda Reddy",
        expected_keywords=["Reddy", "biogeochemistry"],
    ),
    TestCase(
        category="Faculty Profile",
        query="What does Peter Frederick study?",
        expected_keywords=["Frederick", "wildlife"],
    ),
]

# =============================================================================
# TEST CASES - RANKINGS (15 tests)
# =============================================================================

RANKINGS_TESTS = [
    TestCase(
        category="Rankings",
        query="Who are the top researchers at the Water Institute?",
        expected_keywords=["Zimmerman", "Kaplan"],
    ),
    TestCase(
        category="Rankings",
        query="What is Andrew Zimmerman's research impact score?",
        expected_keywords=["Zimmerman", "6.4"],
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
        expected_keywords=["H-Index", "citation"],
    ),
    TestCase(
        category="Rankings",
        query="Who has the most publications at the Water Institute?",
        expected_keywords=["publication"],
    ),
    TestCase(
        category="Rankings",
        query="Who is ranked #1 in hydrology research?",
        expected_keywords=["hydrology"],  # May mention Cohen or other top hydrologists
    ),
    TestCase(
        category="Rankings",
        query="Show me the top 5 researchers",
        expected_keywords=["Zimmerman"],
    ),
    TestCase(
        category="Rankings",
        query="Who are the leading faculty in agricultural sciences?",
        expected_keywords=["agricultural"],
    ),
    TestCase(
        category="Rankings",
        query="Which researchers have the highest citation rates?",
        expected_keywords=["citation"],
    ),
    TestCase(
        category="Rankings",
        query="What are the research metrics for Water Institute faculty?",
        expected_keywords=["metric", "research"],
    ),
    TestCase(
        category="Rankings",
        query="Who is the top ranked ecology researcher?",
        expected_keywords=["ecology"],
    ),
    TestCase(
        category="Rankings",
        query="Show me researchers ranked in top 10%",
        expected_keywords=["top"],  # More flexible - matches "top researchers", "top 10%", etc.
    ),
]

# =============================================================================
# TEST CASES - TOPIC-SPECIFIC EXPERTS (20 tests)
# =============================================================================

TOPIC_EXPERT_TESTS = [
    # PFAS Experts
    TestCase(
        category="Topic Expert",
        query="Who are the top PFAS researchers at the Water Institute?",
        expected_keywords=["PFAS"],  # Should mention PFAS experts (Bowden, Deliz, Baker, etc.)
    ),
    TestCase(
        category="Topic Expert",
        query="Who studies emerging contaminants?",
        expected_keywords=["contaminant"],
    ),
    TestCase(
        category="Topic Expert",
        query="Tell me about PFAS research at UF",
        expected_keywords=["PFAS"],
    ),

    # Everglades Experts
    TestCase(
        category="Topic Expert",
        query="Who are the top Everglades researchers?",
        expected_keywords=["Everglades", "Kaplan"],
    ),
    TestCase(
        category="Topic Expert",
        query="Who studies Everglades restoration?",
        expected_keywords=["Everglades", "restoration"],
    ),
    TestCase(
        category="Topic Expert",
        query="Tell me about wetland research at the Water Institute",
        expected_keywords=["wetland"],
    ),

    # Springs Experts
    TestCase(
        category="Topic Expert",
        query="Who studies Florida springs?",
        expected_keywords=["springs", "Florida"],
    ),
    TestCase(
        category="Topic Expert",
        query="Tell me about spring ecosystem research",
        expected_keywords=["spring"],
    ),

    # Coastal Experts
    TestCase(
        category="Topic Expert",
        query="Who are the coastal researchers at the Water Institute?",
        expected_keywords=["coastal"],
    ),
    TestCase(
        category="Topic Expert",
        query="Who studies harmful algal blooms?",
        expected_keywords=["algal", "bloom"],
    ),
    TestCase(
        category="Topic Expert",
        query="Tell me about red tide research",
        expected_keywords=["red tide"],
    ),

    # Hydrology Experts
    TestCase(
        category="Topic Expert",
        query="Who are the top hydrology researchers?",
        expected_keywords=["hydrology", "Cohen"],
    ),
    TestCase(
        category="Topic Expert",
        query="Who studies watershed hydrology?",
        expected_keywords=["watershed"],
    ),

    # Water Quality Experts
    TestCase(
        category="Topic Expert",
        query="Who are the water quality experts?",
        expected_keywords=["water quality"],
    ),
    TestCase(
        category="Topic Expert",
        query="Who studies nutrient pollution in Florida?",
        expected_keywords=["nutrient"],
    ),

    # Climate Experts
    TestCase(
        category="Topic Expert",
        query="Who studies climate impacts on water resources?",
        expected_keywords=["climate"],
    ),

    # Fisheries Experts
    TestCase(
        category="Topic Expert",
        query="Who studies fisheries at the Water Institute?",
        expected_keywords=["fish"],
    ),

    # Agriculture Experts
    TestCase(
        category="Topic Expert",
        query="Who studies agricultural water use?",
        expected_keywords=["agricultural", "water"],
    ),

    # Extension/Outreach
    TestCase(
        category="Topic Expert",
        query="Who does water-related extension work?",
        expected_keywords=["extension"],
    ),
    TestCase(
        category="Topic Expert",
        query="Who works on stakeholder engagement for water issues?",
        expected_keywords=["stakeholder"],
    ),
]

# =============================================================================
# TEST CASES - GENERAL INSTITUTE INFO (15 tests)
# =============================================================================

GENERAL_INSTITUTE_TESTS = [
    # About
    TestCase(
        category="General Institute",
        query="What is the Water Institute?",
        expected_keywords=["Water Institute", "UF", "interdisciplinary"],
    ),
    TestCase(
        category="General Institute",
        query="When was the Water Institute established?",
        expected_keywords=["2006"],
    ),
    TestCase(
        category="General Institute",
        query="What is the mission of the Water Institute?",
        expected_keywords=["mission", "water"],
    ),

    # Location and Contact
    TestCase(
        category="General Institute",
        query="Where is the Water Institute located?",
        expected_keywords=["Weil Hall", "Gainesville"],
    ),
    TestCase(
        category="General Institute",
        query="How can I contact the Water Institute?",
        expected_keywords=["contact"],
    ),
    TestCase(
        category="General Institute",
        query="What is the Water Institute's address?",
        expected_keywords=["Weil Hall", "32611"],
    ),

    # Programs
    TestCase(
        category="General Institute",
        query="What programs does the Water Institute offer?",
        expected_keywords=["program", "graduate"],
    ),
    TestCase(
        category="General Institute",
        query="What is the WIGF program?",
        expected_keywords=["Graduate", "Fellow"],
    ),
    TestCase(
        category="General Institute",
        query="What is HSAC?",
        expected_keywords=["Hydrologic", "Academic", "Concentration"],
    ),
    TestCase(
        category="General Institute",
        query="Does the Water Institute offer travel awards?",
        expected_keywords=["travel", "award"],
    ),

    # Research Funding
    TestCase(
        category="General Institute",
        query="How much research funding does the Water Institute have?",
        expected_keywords=["million", "research"],
    ),
    TestCase(
        category="General Institute",
        query="How many faculty are affiliated with the Water Institute?",
        expected_keywords=["faculty", "affiliate"],  # More flexible - doesn't require exact number
    ),

    # Facilities
    TestCase(
        category="General Institute",
        query="What facilities does the Water Institute have?",
        expected_keywords=["facilities", "laboratory"],
    ),

    # Partnerships
    TestCase(
        category="General Institute",
        query="What partnerships does the Water Institute have?",
        expected_keywords=["partner"],
    ),

    # Research Areas
    TestCase(
        category="General Institute",
        query="What are the main research areas of the Water Institute?",
        expected_keywords=["research", "water"],
    ),
]

# =============================================================================
# TEST CASES - RESEARCH AREAS (10 tests)
# =============================================================================

RESEARCH_AREA_TESTS = [
    TestCase(
        category="Research Area",
        query="Tell me about hydrology research at the Water Institute",
        expected_keywords=["hydrology", "water"],
    ),
    TestCase(
        category="Research Area",
        query="What water quality research is being done?",
        expected_keywords=["water quality", "research"],
    ),
    TestCase(
        category="Research Area",
        query="Tell me about ecosystem restoration research",
        expected_keywords=["ecosystem", "restoration"],
    ),
    TestCase(
        category="Research Area",
        query="What climate-water research is conducted?",
        expected_keywords=["climate", "water"],
    ),
    TestCase(
        category="Research Area",
        query="Tell me about biogeochemistry research",
        expected_keywords=["biogeochemistry"],
    ),
    TestCase(
        category="Research Area",
        query="What groundwater research is being done?",
        expected_keywords=["groundwater"],
    ),
    TestCase(
        category="Research Area",
        query="Tell me about coastal ecosystem research",
        expected_keywords=["coastal"],
    ),
    TestCase(
        category="Research Area",
        query="What carbon cycling research exists at the Water Institute?",
        expected_keywords=["carbon"],
    ),
    TestCase(
        category="Research Area",
        query="Tell me about aquatic ecology research",
        expected_keywords=["aquatic", "ecology"],
    ),
    TestCase(
        category="Research Area",
        query="What policy-related water research is being done?",
        expected_keywords=["policy"],
    ),
]

# =============================================================================
# TEST CASES - EDGE CASES (10 tests)
# =============================================================================

EDGE_CASE_TESTS = [
    # Partial names
    TestCase(
        category="Edge Case",
        query="Who is John?",
        expected_keywords=["John"],
    ),
    TestCase(
        category="Edge Case",
        query="Tell me about Professor Cohen",
        expected_keywords=["Cohen"],
    ),
    TestCase(
        category="Edge Case",
        query="Who is Dr. Kaplan?",
        expected_keywords=["Kaplan"],
    ),

    # Vague queries
    TestCase(
        category="Edge Case",
        query="Tell me about hydrology",
        expected_keywords=["water"],  # More flexible - hydrology queries should mention water
    ),
    TestCase(
        category="Edge Case",
        query="Who studies fish?",
        expected_keywords=["fish"],
    ),
    TestCase(
        category="Edge Case",
        query="Tell me about water",
        expected_keywords=["water"],
    ),

    # Acronyms
    TestCase(
        category="Edge Case",
        query="What is WIGF?",
        expected_keywords=["Graduate", "Fellow"],
    ),
    TestCase(
        category="Edge Case",
        query="Tell me about UF/IFAS water research",
        expected_keywords=["IFAS", "water"],
    ),

    # Multiple topics
    TestCase(
        category="Edge Case",
        query="Who studies both wetlands and climate change?",
        expected_keywords=["wetland", "climate"],
    ),
    TestCase(
        category="Edge Case",
        query="Faculty working on Everglades phosphorus",
        expected_keywords=["Everglades", "phosphorus"],
    ),
]

# =============================================================================
# TEST CASES - OFF-TOPIC GUARDS (5 tests)
# =============================================================================

OFF_TOPIC_TESTS = [
    TestCase(
        category="Off-Topic Guard",
        query="What's the weather today?",
        expected_keywords=["Water Institute"],
        should_not_contain=["sunny", "rain", "temperature", "forecast"],
    ),
    TestCase(
        category="Off-Topic Guard",
        query="Write me a poem about the ocean",
        expected_keywords=["Water Institute"],
        should_not_contain=["waves crash", "blue sea"],
    ),
    TestCase(
        category="Off-Topic Guard",
        query="What is the capital of France?",
        expected_keywords=["Water Institute"],
        should_not_contain=["Paris"],
    ),
    TestCase(
        category="Off-Topic Guard",
        query="Help me with my math homework",
        expected_keywords=["Water Institute"],
        should_not_contain=["equation", "solve", "calculate"],
    ),
    TestCase(
        category="Off-Topic Guard",
        query="Tell me about SpaceX",
        expected_keywords=["Water Institute"],
        should_not_contain=["Musk", "rocket", "Mars"],
    ),
]


def run_test(api_url: str, test_case: TestCase, verbose: bool = False) -> TestResult:
    """Run a single test case against the API"""
    start_time = time.time()

    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"message": test_case.query, "conversation_history": []},
            timeout=120
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
            response_time=120.0
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
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'[PASS]' if result.passed else '[FAIL]'} [{result.test_case.category}]")
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


def run_test_suite(api_url: str, verbose: bool = False, category_filter: str = None):
    """Run all test cases"""
    # Build test list based on category filter
    all_test_groups = {
        "faculty": FACULTY_PROFILE_TESTS,
        "rankings": RANKINGS_TESTS,
        "topic": TOPIC_EXPERT_TESTS,
        "general": GENERAL_INSTITUTE_TESTS,
        "research": RESEARCH_AREA_TESTS,
        "edge": EDGE_CASE_TESTS,
        "offtopic": OFF_TOPIC_TESTS,
    }

    if category_filter:
        category_filter = category_filter.lower()
        if category_filter in all_test_groups:
            all_tests = all_test_groups[category_filter]
        else:
            print(f"Unknown category: {category_filter}")
            print(f"Available categories: {', '.join(all_test_groups.keys())}")
            return
    else:
        all_tests = (
            FACULTY_PROFILE_TESTS +
            RANKINGS_TESTS +
            TOPIC_EXPERT_TESTS +
            GENERAL_INSTITUTE_TESTS +
            RESEARCH_AREA_TESTS +
            EDGE_CASE_TESTS +
            OFF_TOPIC_TESTS
        )

    print("=" * 70)
    print("UF WATER INSTITUTE CHATBOT - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"API: {api_url}")
    print(f"Total tests: {len(all_tests)}")
    if category_filter:
        print(f"Category filter: {category_filter}")
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
        time.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total_passed = sum(1 for r in results if r.passed)
    total_failed = len(results) - total_passed

    print(f"\nOverall: {total_passed}/{len(results)} passed ({100*total_passed/len(results):.1f}%)")
    print(f"\nBy Category:")
    for category, stats in sorted(categories.items()):
        total = stats["passed"] + stats["failed"]
        pct = 100 * stats["passed"] / total if total > 0 else 0
        status = "[OK]" if stats["failed"] == 0 else "[WARN]" if pct >= 50 else "[FAIL]"
        print(f"  {status} {category}: {stats['passed']}/{total} ({pct:.0f}%)")

    avg_time = sum(r.response_time for r in results) / len(results) if results else 0
    print(f"\nAverage response time: {avg_time:.2f}s")

    # List failed tests
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        print(f"\n[WARNING] FAILED TESTS ({len(failed_tests)}):")
        for r in failed_tests:
            print(f"  - [{r.test_case.category}] \"{r.test_case.query}\"")
            if r.missing_keywords:
                print(f"      Missing: {r.missing_keywords}")

    print("\n" + "=" * 70)

    # Save results to JSON
    results_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_url": api_url,
        "total_tests": len(results),
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": f"{100*total_passed/len(results):.1f}%",
        "avg_response_time": f"{avg_time:.2f}s",
        "by_category": {cat: {"passed": s["passed"], "failed": s["failed"]} for cat, s in categories.items()},
        "failed_tests": [
            {
                "category": r.test_case.category,
                "query": r.test_case.query,
                "missing_keywords": r.missing_keywords,
                "forbidden_keywords": r.forbidden_keywords
            }
            for r in failed_tests
        ]
    }

    with open("test_results.json", "w") as f:
        json.dump(results_data, f, indent=2)
    print(f"Results saved to test_results.json")

    return results


def main():
    parser = argparse.ArgumentParser(description="Comprehensive test suite for the Water Institute chatbot")
    parser.add_argument("--local", action="store_true", help="Test against localhost:8000")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full responses")
    parser.add_argument("--category", "-c", type=str, help="Run only specific category (faculty, rankings, topic, general, research, edge, offtopic)")
    args = parser.parse_args()

    api_url = LOCAL_API if args.local else PROD_API
    run_test_suite(api_url, args.verbose, args.category)


if __name__ == "__main__":
    main()
