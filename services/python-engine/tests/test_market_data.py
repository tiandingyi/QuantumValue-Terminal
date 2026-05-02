from app.providers.market_data import fetch_market_data_for_period


def test_fetch_market_data_uses_static_seed_for_aapl_latest_quarter() -> None:
    market_data = fetch_market_data_for_period(
        ticker="AAPL",
        period_end="2026-03-28",
        shares_outstanding=14_800_000_000,
    )

    assert market_data["market_cap"] == 3_430_000_000_000
    assert market_data["spot_price"] is not None
    assert market_data["spot_price"] > 0


def test_fetch_market_data_uses_static_seed_for_cost_latest_quarter() -> None:
    market_data = fetch_market_data_for_period(
        ticker="COST",
        period_end="2026-02-15",
        shares_outstanding=445_000_000,
    )

    assert market_data["market_cap"] == 436_900_000_000
    assert market_data["spot_price"] is not None
    assert market_data["spot_price"] > 0
