import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.data.market_data import fetch_market_snapshot, fetch_option_chain
from src.models.black_scholes import vectorized_price, vectorized_greeks, implied_volatility_vectorized
from src.models.crr import CRRBinomial

st.set_page_config(page_title="Quantitative Options Research Engine", page_icon="📈", layout="wide")
st.title("Quantitative Options Research Engine")
st.caption("Market-calibrated European and American option analytics. Yahoo Finance is a research-data source, not an execution feed.")

with st.sidebar:
    st.header("Market Configuration")
    ticker = st.text_input("Underlying", "SPY", max_chars=20).upper().strip()
    r_pct = st.number_input("Risk-free rate (%)", -5.0, 25.0, 4.50, 0.05)
    q_pct = st.number_input("Dividend yield (%)", -5.0, 25.0, 0.00, 0.05)
    iv_source = st.selectbox("IV source", ["auto", "Yahoo IV", "Market Mid"])
    st.divider()
    st.header("Model Comparison")
    crr_steps = st.slider("CRR steps", 25, 2000, 400, 25)
    model_type = st.selectbox("American model", ["CRR Binomial", "Black-Scholes European"])
    st.divider()
    exact_time = st.checkbox("Use exact calendar time", True)

try:
    snapshot = fetch_market_snapshot(ticker)
except Exception as exc:
    st.error(f"Unable to retrieve market data for {ticker}: {exc}")
    st.stop()

if snapshot is None:
    st.error(f"No usable market data found for {ticker}.")
    st.stop()

spot = float(snapshot["spot"])
expirations = snapshot["expirations"]
with st.sidebar:
    st.success(f"Spot: ${spot:,.2f}")

if not expirations:
    st.warning(f"{ticker} has no option expirations returned by Yahoo Finance.")
    st.stop()

selected_exp = st.sidebar.selectbox("Expiration", expirations)

try:
    calls, puts = fetch_option_chain(ticker, selected_exp)
except Exception as exc:
    st.error(f"Unable to retrieve option chain: {exc}")
    st.stop()

def build_chain(raw, option_type):
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    for col in ["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]:
        if col not in df.columns:
            df[col] = np.nan

    valid_quote = (
        df["bid"].notna() & df["ask"].notna() &
        (df["bid"] >= 0) & (df["ask"] >= df["bid"]) &
        ((df["bid"] > 0) | (df["ask"] > 0))
    )
    df["Market Mid"] = np.where(valid_quote, (df["bid"] + df["ask"]) / 2.0, np.nan)

    exp_date = pd.Timestamp(selected_exp)
    if exact_time:
        now = pd.Timestamp.now(tz="America/New_York")
        expiry = pd.Timestamp(year=exp_date.year, month=exp_date.month, day=exp_date.day,
                              hour=16, minute=0, tz="America/New_York")
        T = max((expiry - now).total_seconds() / (365.0 * 24 * 3600), 0.0)
    else:
        T = max((exp_date.normalize() - pd.Timestamp.today().normalize()).days / 365.0, 0.0)

    K = df["strike"].to_numpy(float)
    yahoo_iv = df["impliedVolatility"].to_numpy(float)
    yahoo_iv = np.where(np.isfinite(yahoo_iv) & (yahoo_iv > 0) & (yahoo_iv < 10), yahoo_iv, np.nan)
    mids = df["Market Mid"].to_numpy(float)

    calculated_iv = implied_volatility_vectorized(option_type, spot, K, T, r_pct/100, q_pct/100, mids)

    if iv_source == "Yahoo IV":
        sigma = yahoo_iv
    elif iv_source == "Market Mid":
        sigma = calculated_iv
    else:
        sigma = np.where(np.isfinite(yahoo_iv), yahoo_iv, calculated_iv)

    sigma_safe = np.where(np.isfinite(sigma) & (sigma > 1e-6), sigma, 0.20)
    theo = vectorized_price(option_type, spot, K, T, r_pct/100, q_pct/100, sigma_safe)
    greeks = vectorized_greeks(option_type, spot, K, T, r_pct/100, q_pct/100, sigma_safe)

    itm = spot > K if option_type == "call" else spot < K

    out = pd.DataFrame({
        "Type": option_type.capitalize(),
        "ITM/OTM": np.where(itm, "ITM", "OTM"),
        "Strike": K,
        "Bid": df["bid"].to_numpy(),
        "Ask": df["ask"].to_numpy(),
        "Market Mid": mids,
        "Spread": df["ask"].to_numpy() - df["bid"].to_numpy(),
        "Spread %": np.where(np.isfinite(mids) & (mids > 0),
                            (df["ask"].to_numpy() - df["bid"].to_numpy()) / mids * 100, np.nan),
        "Yahoo IV": yahoo_iv,
        "Calculated IV": calculated_iv,
        "IV Used": sigma,
        "Theo (BS)": theo,
        "Last": df["lastPrice"].to_numpy(),
        "Volume": df["volume"].to_numpy(),
        "Open Interest": df["openInterest"].to_numpy(),
        "Delta": greeks["Delta"],
        "Gamma": greeks["Gamma"],
        "Theta / Day": greeks["Theta"],
        "Vega / 1%": greeks["Vega"],
        "Rho / 1%": greeks["Rho"],
    })
    out.loc[~valid_quote.to_numpy(), "Calculated IV"] = np.nan
    return out.sort_values("Strike").reset_index(drop=True)

calls_df = build_chain(calls, "call")
puts_df = build_chain(puts, "put")
chain = pd.concat([calls_df, puts_df], ignore_index=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Greeks", "IV Smile", "BS vs CRR", "Raw Chain"])

with tab1:
    valid = chain["Market Mid"].notna()
    iv_count = chain["Calculated IV"].notna().sum()
    spreads = chain.loc[valid, "Spread %"]
    a,b,c,d,e = st.columns(5)
    a.metric("Spot", f"${spot:,.2f}")
    b.metric("Contracts", f"{len(chain):,}")
    c.metric("Valid Quotes", f"{valid.sum():,}")
    d.metric("IV Calibrated", f"{iv_count:,}")
    e.metric("Avg Spread", f"{spreads.mean():.2f}%" if len(spreads) else "N/A")

    st.subheader(f"Option Chain — {selected_exp}")
    st.caption("Market Mid = (Bid + Ask) / 2. It is an observed quote, not theoretical value. Theo (BS) is the model value. ITM/OTM is based on spot vs strike.")

    cols = ["Type","ITM/OTM","Strike","Bid","Ask","Market Mid","Spread %","Yahoo IV","Calculated IV","Theo (BS)","Delta","Gamma","Theta / Day","Vega / 1%"]
    view = chain[cols].copy()
    view["Yahoo IV"] *= 100
    view["Calculated IV"] *= 100
    st.dataframe(view.style.format({
        "Strike":"${:,.2f}","Bid":"${:,.2f}","Ask":"${:,.2f}","Market Mid":"${:,.2f}",
        "Theo (BS)":"${:,.2f}","Spread %":"{:.2f}%","Yahoo IV":"{:.2f}%","Calculated IV":"{:.2f}%",
        "Delta":"{:.4f}","Gamma":"{:.6f}","Theta / Day":"{:.4f}","Vega / 1%":"{:.4f}"
    }, na_rep="—"), use_container_width=True, height=650)

with tab2:
    greek = st.selectbox("Greek", ["Delta","Gamma","Theta / Day","Vega / 1%","Rho / 1%"])
    filt = st.radio("Option type", ["Both","Call","Put"], horizontal=True)
    p = chain if filt == "Both" else chain[chain["Type"] == filt]
    fig = go.Figure()
    for typ in ["Call","Put"]:
        d = p[p["Type"] == typ].sort_values("Strike")
        if not d.empty:
            fig.add_trace(go.Scatter(x=d["Strike"], y=d[greek], mode="lines+markers", name=typ))
    fig.add_vline(x=spot, line_dash="dash", annotation_text=f"Spot ${spot:,.2f}")
    fig.update_layout(template="plotly_dark", title=f"{greek} vs Strike", height=550, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    p = chain.dropna(subset=["Calculated IV"])
    if p.empty:
        st.warning("No valid bid/ask mids were available for IV calibration.")
    else:
        fig = go.Figure()
        for typ in ["Call","Put"]:
            d = p[p["Type"] == typ]
            fig.add_trace(go.Scatter(x=d["Strike"], y=d["Calculated IV"]*100, mode="markers", name=typ))
        fig.add_vline(x=spot, line_dash="dash", annotation_text="Spot")
        fig.update_layout(template="plotly_dark", title="Market-Calibrated Implied Volatility",
                          yaxis_title="IV (%)", xaxis_title="Strike", height=550)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("European Black-Scholes vs American CRR")
    typ = st.selectbox("Option", ["Call","Put"])
    source = calls_df if typ == "Call" else puts_df
    source = source.dropna(subset=["IV Used"])
    rows = []
    if not source.empty:
        T = max((pd.Timestamp(selected_exp).normalize() - pd.Timestamp.today().normalize()).days / 365.0, 1/365.0)
        sample = source.iloc[np.linspace(0, len(source)-1, min(15,len(source))).astype(int)].drop_duplicates()
        for _, row in sample.iterrows():
            K = float(row["Strike"]); sigma = float(row["IV Used"])
            bs = float(vectorized_price(typ.lower(), spot, np.array([K]), T, r_pct/100, q_pct/100, np.array([sigma]))[0])
            try:
                cr = CRRBinomial.price(typ.lower(), spot, K, T, r_pct/100, q_pct/100, sigma, crr_steps, True)
                status = "OK"
            except Exception as exc:
                cr = np.nan; status = str(exc)
            rows.append({"Strike":K,"Market Mid":row["Market Mid"],"BS Theo":bs,"CRR American":cr,
                         "American Premium":cr-bs if np.isfinite(cr) else np.nan,"Status":status})
    if rows:
        st.dataframe(pd.DataFrame(rows).style.format({
            "Strike":"${:,.2f}","Market Mid":"${:,.2f}","BS Theo":"${:,.4f}",
            "CRR American":"${:,.4f}","American Premium":"${:,.4f}"
        }, na_rep="—"), use_container_width=True)
    else:
        st.warning("No usable volatility data for model comparison.")
    st.info("CRR allows early exercise and is therefore the relevant American-option benchmark. Black-Scholes is retained as the European benchmark.")

with tab5:
    raw = pd.concat([calls.assign(optionType="call"), puts.assign(optionType="put")], ignore_index=True)
    st.dataframe(raw, use_container_width=True, height=650)
