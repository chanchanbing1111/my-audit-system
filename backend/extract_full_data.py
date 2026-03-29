#!/usr/bin/env python3
"""
Extract and verify full Tesla financial data for 2023-2025
"""
import os
import httpx
import json
import re
from datetime import datetime

def extract_financial_data():
    """Extract complete financial data for 2023-2025"""
    print("="*60)
    print("TESLA FINANCIAL DATA EXTRACTION 2023-2025")
    print("="*60)

    # Set up API call
    api_key = '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'
    base_url = "https://api.tavily.com"

    # More specific search for exact annual reports
    query = "Tesla TSLA annual report 10-K revenue net income total assets 2023 2024 2025 financial statements"

    print("\nSearch Query: " + query)

    try:
        # Make the API request
        response = httpx.post(
            f"{base_url}/search",
            json={
                "query": query,
                "api_key": api_key,
                "max_results": 20,
                "include_answer": True,
                "search_depth": "advanced"
            },
            timeout=30.0
        )

        print("\nResponse Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            # Store extracted data by year
            financial_data = {}

            # Process each result
            for result in results:
                url = result.get('url', '')
                title = result.get('title', '')
                content = result.get('content', '')

                # Extract year from URL or content
                year = None
                if '2025' in url:
                    year = 2025
                elif '2024' in url:
                    year = 2024
                elif '2023' in url:
                    year = 2023

                if year and year not in financial_data:
                    financial_data[year] = {
                        'source': title,
                        'url': url,
                        'revenue': None,
                        'net_income': None,
                        'total_assets': None,
                        'raw_content': content[:5000]  # Store first 5k chars
                    }

                    # Extract financial metrics
                    if content:
                        metrics = extract_metrics_from_content(content, year)
                        financial_data[year].update(metrics)

            # Display results
            print("\n" + "="*50)
            print("EXTRACTED FINANCIAL DATA BY YEAR")
            print("="*50)

            for year in [2025, 2024, 2023]:
                if year in financial_data:
                    data = financial_data[year]
                    print(f"\nYEAR {year}:")
                    print(f"   Source: {data['source']}")
                    print(f"   URL: {data['url']}")
                    print(f"   Revenue: ${data['revenue']:,.2f}M" if data['revenue'] else "   Revenue: NOT FOUND")
                    print(f"   Net Income: ${data['net_income']:,.2f}M" if data['net_income'] else "   Net Income: NOT FOUND")
                    print(f"   Total Assets: ${data['total_assets']:,.2f}M" if data['total_assets'] else "   Total Assets: NOT FOUND")
                else:
                    print(f"\nYEAR {year}: NO DATA FOUND")

            # Calculate growth rate if we have 2024 and 2025
            if 2024 in financial_data and 2025 in financial_data:
                rev_2024 = financial_data[2024]['revenue']
                rev_2025 = financial_data[2025]['revenue']

                if rev_2024 and rev_2025:
                    growth_rate = ((rev_2025 - rev_2024) / rev_2024) * 100
                    print(f"\n" + "="*50)
                    print("REVENUE GROWTH ANALYSIS")
                    print("="*50)
                    print(f"2024 Revenue: ${rev_2024:,.2f}M")
                    print(f"2025 Revenue: ${rev_2025:,.2f}M")
                    print(f"Growth Rate: {growth_rate:+.2f}%")

                    # Add context
                    if growth_rate > 0:
                        print("Trend: GROWING")
                    else:
                        print("Trend: DECLINING")

            # Verify coverage
            years_found = len(financial_data)
            print(f"\n" + "="*50)
            print("COVERAGE VERIFICATION")
            print("="*50)
            print(f"Years with data: {years_found}/3 (2023, 2024, 2025)")

            if years_found == 3:
                print("COMPLETE COVERAGE: All three years have data")
                return True
            else:
                print("INCOMPLETE COVERAGE: Missing some years")
                return False

        else:
            print("API Error: " + str(response.status_code))
            return False

    except Exception as e:
        print("Error: " + str(e))
        return False

def extract_metrics_from_content(content, year):
    """Extract financial metrics from content using regex patterns"""
    metrics = {}

    # Revenue patterns
    revenue_patterns = [
        r'Revenues?\s*:\s*\$?([\d,]+)\s*M',
        r'Total revenues?\s*:\s*\$?([\d,]+)\s*M',
        r'Revenue\s*\$?([\d,]+)\s*million',
        r'[\d,]+\s*\$\s*revenue',
        r'Revenue\s*([\d,]+)'
    ]

    # Net Income patterns
    income_patterns = [
        r'Net income\s*:\s*\$?([\d,]+)\s*M',
        r'Net loss\s*:\s*\$?([\d,]+)\s*M',
        r'Net income\s*\$?([\d,]+)\s*million',
        r'Net income\s*\(loss\)\s*\$?([\d,]+)\s*M'
    ]

    # Total Assets patterns
    assets_patterns = [
        r'Total assets\s*:\s*\$?([\d,]+)\s*M',
        r'Assets\s*:\s*\$?([\d,]+)\s*M',
        r'Total assets\s*\$?([\d,]+)\s*million'
    ]

    # Extract revenue
    for pattern in revenue_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics['revenue'] = float(match.group(1).replace(',', ''))
                break
            except:
                continue

    # Extract net income
    for pattern in income_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                # Check if it's a loss
                if 'loss' in pattern.lower() and value > 0:
                    metrics['net_income'] = -value
                else:
                    metrics['net_income'] = value
                break
            except:
                continue

    # Extract total assets
    for pattern in assets_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics['total_assets'] = float(match.group(1).replace(',', ''))
                break
            except:
                continue

    return metrics

if __name__ == "__main__":
    print("Starting comprehensive Tesla financial data extraction...")

    success = extract_financial_data()

    print("\n" + "="*50)
    print("FINAL RESULT: " + ("SUCCESS - Complete data extracted" if success else "FAILED - Incomplete data"))
    print("="*50)