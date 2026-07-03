#!/usr/bin/env python3
"""Test pytrends integration"""
from trends_analyzer import TrendsAnalyzer

t = TrendsAnalyzer()
print("Testing pytrends...")

# Test interest over time
result = t.get_interest_over_time(['solar installation'], 'US-CA', 'today 3-m')
print("Interest over time result:")
if 'error' in result:
    print(f"  Error: {result['error']}")
elif 'summary' in result:
    for kw, data in result['summary'].items():
        print(f"  {kw}: avg={data['avg_interest']}, trend={data['trend']}")
else:
    print(f"  Result keys: {result.keys()}")

# Test full opportunity analysis
print("\nTesting full opportunity analysis...")
opportunity = t.analyze_opportunity('solar', 'Los Angeles, CA', 5)
print(f"Monthly searches: {opportunity.get('total_monthly_searches', 'N/A')}")
print(f"Estimated leads: {opportunity.get('estimated_monthly_leads', 'N/A')}")
print(f"Opportunity score: {opportunity.get('opportunity_score', 'N/A')}")
print(f"Avg interest: {opportunity.get('avg_interest_score', 'N/A')}")
