"""
Manual test script for the chart data endpoint.

This script tests the /api/v1/market/chart/{symbol} endpoint.

Prerequisites:
1. Backend server running: uv run uvicorn app.main:app --reload --port 8000
2. User logged in and has a strategy subscription
3. Broker connected (or mock data available)

Usage:
    python tests/test_chart_endpoint_manual.py
"""

import requests
import json
from datetime import date, timedelta

# Configuration
API_URL = "http://localhost:8000/api/v1"
ACCESS_TOKEN = None  # Will be set after login

# Test credentials (update these with your test user)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"


def login():
    """Login and get access token."""
    global ACCESS_TOKEN
    print("\n=== Login ===")

    response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )

    if response.status_code == 200:
        data = response.json()
        ACCESS_TOKEN = data.get("access_token")
        print(f"✓ Login successful! Token: {ACCESS_TOKEN[:20]}...")
        return True
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return False


def get_headers():
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


def get_subscriptions():
    """Get user's strategy subscriptions."""
    print("\n=== Get Strategy Subscriptions ===")

    response = requests.get(
        f"{API_URL}/strategies/subscriptions/my",
        headers=get_headers()
    )

    if response.status_code == 200:
        subs = response.json()
        print(f"✓ Found {len(subs)} subscriptions")
        for sub in subs:
            print(f"  - {sub['id']}: Strategy {sub['strategy_id']} ({sub['status']})")
            if sub.get('selected_symbols'):
                print(f"    Symbols: {', '.join(sub['selected_symbols'])}")
        return subs
    else:
        print(f"❌ Failed to get subscriptions: {response.status_code}")
        print(response.text)
        return []


def test_chart_endpoint(subscription_id: str, symbol: str):
    """Test the chart data endpoint."""
    print(f"\n=== Test Chart Endpoint ===")
    print(f"Subscription ID: {subscription_id}")
    print(f"Symbol: {symbol}")

    # Set date range (last 7 days)
    to_date = date.today()
    from_date = to_date - timedelta(days=7)

    params = {
        "subscription_id": subscription_id,
        "exchange": "NSE",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "limit": 200
    }

    print(f"Date range: {from_date} to {to_date}")

    response = requests.get(
        f"{API_URL}/market/chart/{symbol}",
        params=params,
        headers=get_headers()
    )

    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Chart data received successfully!")
        print(f"\nChart Data Summary:")
        print(f"  Symbol: {data.get('symbol')}")
        print(f"  Exchange: {data.get('exchange')}")
        print(f"  Interval: {data.get('interval')}")
        print(f"  Strategy: {data.get('strategy_name')}")
        print(f"  Candles: {len(data.get('candles', []))}")
        print(f"  Indicators: {len(data.get('indicators', []))}")
        print(f"  Trade Markers: {len(data.get('trades', []))}")

        # Print indicator details
        if data.get('indicators'):
            print(f"\n  Indicator Details:")
            for ind in data['indicators']:
                non_null_values = sum(1 for d in ind['data'] if d['value'] is not None)
                print(f"    - {ind['name']} ({ind['type']})")
                print(f"      Pane: {ind['pane']}, Color: {ind['color']}")
                print(f"      Params: {ind['params']}")
                print(f"      Data points: {len(ind['data'])} ({non_null_values} non-null)")

        # Print trade marker details
        if data.get('trades'):
            print(f"\n  Trade Markers:")
            for trade in data['trades'][:5]:  # Show first 5
                print(f"    - {trade['type'].upper()}: {trade['side'].upper()} "
                      f"{trade['quantity']} @ {trade['price']:.2f}")
                if trade.get('pnl'):
                    print(f"      P&L: {trade['pnl']:.2f}")
            if len(data['trades']) > 5:
                print(f"    ... and {len(data['trades']) - 5} more trades")

        # Print sample candles
        if data.get('candles'):
            print(f"\n  Sample Candles (first 3):")
            for candle in data['candles'][:3]:
                print(f"    - {candle['timestamp']}: "
                      f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
                      f"L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")

        return True
    else:
        print(f"\n❌ Chart endpoint failed: {response.status_code}")
        print(response.text)
        return False


def run_tests():
    """Run all manual tests."""
    print("\n" + "="*60)
    print("CHART ENDPOINT MANUAL TESTS")
    print("="*60)

    # Step 1: Login
    if not login():
        print("\n❌ Cannot proceed without login")
        return False

    # Step 2: Get subscriptions
    subscriptions = get_subscriptions()
    if not subscriptions:
        print("\n⚠️  No subscriptions found. Please:")
        print("   1. Create a strategy subscription in the UI")
        print("   2. Select trading symbols")
        print("   3. Run this test again")
        return False

    # Step 3: Test chart endpoint for each subscription
    for sub in subscriptions:
        subscription_id = sub['id']
        symbols = sub.get('selected_symbols', [])

        if not symbols:
            print(f"\n⚠️  Subscription {subscription_id} has no symbols selected")
            continue

        # Test with first symbol
        symbol = symbols[0]
        if not test_chart_endpoint(subscription_id, symbol):
            return False

    print("\n" + "="*60)
    print("✅ ALL MANUAL TESTS COMPLETED!")
    print("="*60 + "\n")
    return True


if __name__ == '__main__':
    print("\n⚠️  MANUAL TEST PREREQUISITES:")
    print("1. Backend server must be running: uv run uvicorn app.main:app --reload --port 8000")
    print("2. Update TEST_EMAIL and TEST_PASSWORD with valid credentials")
    print("3. Ensure you have at least one strategy subscription with symbols")
    print("4. Broker should be connected (or mock data available)")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()

    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
