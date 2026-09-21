import time

import pandas as pd
import yfinance as yf
import streamlit as st

from yfinance.exceptions import YFRateLimitError


# ---------------------------------------------------------
# Yahoo Finance safety helpers
# ---------------------------------------------------------

def _is_rate_limit_error(exc):
    """
    Detect Yahoo/yfinance rate-limit errors.

    Handles both the official yfinance exception and cases where
    the underlying error is surfaced with a 429/Too Many Requests
    message.
    """
    if isinstance(exc, YFRateLimitError):
        return True

    message = str(exc).lower()

    return (
        "429" in message
        or "too many requests" in message
        or "rate limited" in message
        or "rate-limit" in message
    )


def _safe_yahoo_call(func, retries=1):
    """
    Execute a Yahoo Finance request without allowing a Yahoo failure
    to crash the Streamlit application.

    Rate-limit errors are not aggressively retried because repeated
    requests can make the rate-limit worse.

    Other transient errors receive one retry.
    """
    for attempt in range(retries + 1):
        try:
            return func()

        except Exception as exc:
            # Yahoo rate limit:
            # fail gracefully instead of repeatedly hammering Yahoo.
            if _is_rate_limit_error(exc):
                print(
                    "Yahoo Finance rate limit encountered. "
                    "Using safe fallback instead."
                )
                return None

            # Retry one time for non-rate-limit transient failures.
            if attempt < retries:
                time.sleep(2)
                continue

            print(
                f"Yahoo Finance request failed: "
                f"{type(exc).__name__}: {exc}"
            )
            return None

    return None


# ---------------------------------------------------------
# Market snapshot
# ---------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_snapshot(ticker_symbol):
    """
    Fetch the underlying price and available option expirations.

    Returns:
        dict | None

    If Yahoo Finance is temporarily unavailable or rate-limited,
    returns None instead of crashing the application.
    """

    ticker_symbol = str(ticker_symbol).strip().upper()

    if not ticker_symbol:
        return None

    ticker = yf.Ticker(ticker_symbol)

    # ---------------------------------------------
    # Fetch recent underlying price
    # ---------------------------------------------

    hist = _safe_yahoo_call(
        lambda: ticker.history(
            period="5d",
            auto_adjust=False
        )
    )

    if hist is None:
        return None

    if hist.empty or "Close" not in hist.columns:
        return None

    close = hist["Close"].dropna()

    if close.empty:
        return None

    # ---------------------------------------------
    # Fetch available option expirations
    # ---------------------------------------------

    expirations = _safe_yahoo_call(
        lambda: list(ticker.options)
    )

    # If Yahoo is rate-limited while retrieving
    # expirations, keep the valid underlying price
    # rather than crashing.
    if expirations is None:
        expirations = []

    return {
        "symbol": ticker_symbol,
        "spot": float(close.iloc[-1]),
        "expirations": expirations,
    }


# ---------------------------------------------------------
# Option chain
# ---------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_option_chain(ticker_symbol, expiration_date):
    """
    Fetch calls and puts for a specific expiration.

    Returns:
        (calls, puts)

    On Yahoo Finance failure/rate limiting, returns two empty
    DataFrames instead of raising an exception.
    """

    ticker_symbol = str(ticker_symbol).strip().upper()

    if not ticker_symbol or not expiration_date:
        return pd.DataFrame(), pd.DataFrame()

    ticker = yf.Ticker(ticker_symbol)

    chain = _safe_yahoo_call(
        lambda: ticker.option_chain(expiration_date)
    )

    if chain is None:
        return pd.DataFrame(), pd.DataFrame()

    try:
        calls = chain.calls.copy()
        puts = chain.puts.copy()

    except Exception as exc:
        print(
            f"Yahoo option-chain response could not be processed: "
            f"{type(exc).__name__}: {exc}"
        )
        return pd.DataFrame(), pd.DataFrame()

    return calls, puts