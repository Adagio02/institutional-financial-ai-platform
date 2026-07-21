from datetime import date

import polars as pl

from finai.data.quality.market import validate_market_prices


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["AAPL"],
            "date": [date(2025, 1, 2)],
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "adjusted_close": [101.0],
            "volume": [1_000_000.0],
        }
    )


def test_valid_market_frame() -> None:
    assert validate_market_prices(valid_frame()) == []


def test_duplicate_ticker_date_is_rejected() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])

    assert "duplicate_ticker_date" in validate_market_prices(frame)


def test_high_below_low_is_rejected() -> None:
    frame = valid_frame().with_columns(
        pl.lit(98.0).alias("high"),
        pl.lit(99.0).alias("low"),
    )

    assert "high_below_low" in validate_market_prices(frame)


def test_negative_volume_is_rejected() -> None:
    frame = valid_frame().with_columns(
        pl.lit(-1.0).alias("volume")
    )

    assert "negative_volume" in validate_market_prices(frame)


def test_nonpositive_adjusted_close_is_rejected() -> None:
    frame = valid_frame().with_columns(
        pl.lit(0.0).alias("adjusted_close")
    )

    assert "nonpositive_adjusted_close" in validate_market_prices(frame)


def test_missing_column_is_rejected() -> None:
    frame = valid_frame().drop("volume")

    errors = validate_market_prices(frame)

    assert errors
    assert "missing_columns" in errors[0]