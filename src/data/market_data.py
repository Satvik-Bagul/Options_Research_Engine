import yfinance as yf
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_snapshot(ticker_symbol):
    ticker=yf.Ticker(ticker_symbol)
    hist=ticker.history(period="5d",auto_adjust=False)
    if hist is None or hist.empty or "Close" not in hist.columns: return None
    close=hist["Close"].dropna()
    if close.empty: return None
    try: expirations=list(ticker.options)
    except Exception: expirations=[]
    return {"symbol":ticker_symbol,"spot":float(close.iloc[-1]),"expirations":expirations}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_option_chain(ticker_symbol,expiration_date):
    ticker=yf.Ticker(ticker_symbol)
    chain=ticker.option_chain(expiration_date)
    return chain.calls.copy(), chain.puts.copy()
