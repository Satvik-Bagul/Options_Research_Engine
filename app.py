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
    iv_source = st.selectbox("IV / Model Input",["auto","Market Mid → IV","Yahoo IV",],)
    st.divider()
    st.header("Model Comparison")
    st.header("Quote Quality")

max_spread_pct = st.number_input(
    "Max spread for IV calibration (%)",
    min_value=1.0,
    max_value=200.0,
    value=50.0,
    step=1.0,
)

min_open_interest = st.number_input(
    "Minimum open interest",
    min_value=0,
    max_value=100000,
    value=10,
    step=10,
)

min_volume = st.number_input(
    "Minimum daily volume",
    min_value=0,
    max_value=100000,
    value=1,
    step=1,
)
crr_steps = st.slider("CRR steps", 25, 2000, 400, 25)
model_type = st.selectbox("American model/European Model", ["CRR Binomial", "Black-Scholes European"])
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
def calculate_time_to_expiry(expiration_date, use_exact_time):
    exp_date = pd.Timestamp(expiration_date)

    if use_exact_time:
        now = pd.Timestamp.now(
            tz="America/New_York"
        )

        expiry = pd.Timestamp(
            year=exp_date.year,
            month=exp_date.month,
            day=exp_date.day,
            hour=16,
            minute=0,
            tz="America/New_York",
        )

        return max(
            (
                expiry - now
            ).total_seconds()
            / (365.0 * 24.0 * 3600.0),
            0.0,
        )

    today = pd.Timestamp.today().normalize()

    return max(
        (exp_date.normalize() - today).days / 365.0,
        0.0,
    )


T = calculate_time_to_expiry(
    selected_exp,
    exact_time,
)

try:
    calls, puts = fetch_option_chain(ticker, selected_exp)
except Exception as exc:
    st.error(f"Unable to retrieve option chain: {exc}")
    st.stop()

def build_chain(raw, option_type):

    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    numeric_columns = [
        "strike",
        "bid",
        "ask",
        "lastPrice",
        "volume",
        "openInterest",
        "impliedVolatility",
    ]

    for col in numeric_columns:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

        else:
            df[col] = np.nan

    K = df["strike"].to_numpy(float)

    bid = df["bid"].to_numpy(float)
    ask = df["ask"].to_numpy(float)
    last = df["lastPrice"].to_numpy(float)
    volume = df["volume"].to_numpy(float)
    open_interest = df[
        "openInterest"
    ].to_numpy(float)

    # ---------------------------------------------------------
    # QUOTE VALIDATION
    # ---------------------------------------------------------

    finite_bid = np.isfinite(bid)
    finite_ask = np.isfinite(ask)

    missing_quote = (
        ~finite_bid
        | ~finite_ask
    )

    crossed_market = (
        finite_bid
        & finite_ask
        & (ask < bid)
    )

    no_bid = (
        finite_bid
        & finite_ask
        & (bid <= 0)
    )

    valid_quote = (
        finite_bid
        & finite_ask
        & (bid > 0)
        & (ask > 0)
        & (ask >= bid)
    )

    market_mid = np.where(
        valid_quote,
        (bid + ask) / 2.0,
        np.nan,
    )

    spread = np.where(
        valid_quote,
        ask - bid,
        np.nan,
    )

    spread_pct = np.where(
        valid_quote & (market_mid > 0),
        spread / market_mid * 100.0,
        np.nan,
    )

    # ---------------------------------------------------------
    # QUOTE STATUS
    # ---------------------------------------------------------

    quote_status = np.full(
        len(df),
        "INVALID",
        dtype=object,
    )

    quote_status[
        missing_quote
    ] = "MISSING"

    quote_status[
        crossed_market
    ] = "CROSSED"

    quote_status[
        no_bid
    ] = "NO BID"

    quote_status[
        valid_quote
    ] = "VALID"

    # ---------------------------------------------------------
    # LIQUIDITY CLASSIFICATION
    # ---------------------------------------------------------

    has_activity = (
        (open_interest >= min_open_interest)
        | (volume >= min_volume)
    )

    liquidity_status = np.full(
        len(df),
        "ILLIQUID",
        dtype=object,
    )

    liquid_mask = (
        valid_quote
        & np.isfinite(spread_pct)
        & (spread_pct <= max_spread_pct)
        & has_activity
    )

    thin_mask = (
        valid_quote
        & np.isfinite(spread_pct)
        & (spread_pct <= max_spread_pct)
        & ~has_activity
    )

    wide_mask = (
        valid_quote
        & np.isfinite(spread_pct)
        & (spread_pct > max_spread_pct)
    )

    liquidity_status[
        liquid_mask
    ] = "LIQUID"

    liquidity_status[
        thin_mask
    ] = "THIN"

    liquidity_status[
        wide_mask
    ] = "WIDE"

    # ---------------------------------------------------------
    # IV ELIGIBILITY
    # ---------------------------------------------------------

    iv_eligible = (
        valid_quote
        & np.isfinite(market_mid)
        & (market_mid > 0)
        & np.isfinite(spread_pct)
        & (spread_pct <= max_spread_pct)
        & has_activity
    )

    iv_market_prices = np.where(
        iv_eligible,
        market_mid,
        np.nan,
    )

    # ---------------------------------------------------------
    # YAHOO IV
    # ---------------------------------------------------------

    yahoo_iv_raw = df[
        "impliedVolatility"
    ].to_numpy(float)

    yahoo_iv = np.where(
        np.isfinite(yahoo_iv_raw)
        & (yahoo_iv_raw > 0)
        & (yahoo_iv_raw < 10.0),
        yahoo_iv_raw,
        np.nan,
    )

    yahoo_iv_status = np.full(
        len(df),
        "Unavailable",
        dtype=object,
    )

    yahoo_iv_status[
        np.isfinite(yahoo_iv)
    ] = "Reference"

    yahoo_iv_status[
        np.isfinite(yahoo_iv_raw)
        & (yahoo_iv_raw >= 10.0)
    ] = "Rejected: extreme Yahoo IV"

    # ---------------------------------------------------------
    # MARKET-IMPLIED IV
    # ---------------------------------------------------------

    calculated_iv, calculated_iv_status = (
        implied_volatility_vectorized(
            option_type,
            spot,
            K,
            T,
            r_pct / 100.0,
            q_pct / 100.0,
            iv_market_prices,
            return_status=True,
        )
    )

    calculated_iv_status = np.asarray(
        calculated_iv_status,
        dtype=object,
    )

    # Override numerical status with quote-quality status
    calculated_iv_status[
        ~valid_quote
    ] = "Unavailable: invalid quote"

    calculated_iv_status[
        valid_quote & ~has_activity
    ] = "Unavailable: illiquid quote"

    calculated_iv_status[
        valid_quote
        & has_activity
        & (spread_pct > max_spread_pct)
    ] = "Unavailable: spread too wide"

    # ---------------------------------------------------------
    # SELECT IV SOURCE
    # ---------------------------------------------------------

    if iv_source == "Yahoo IV":

        sigma = yahoo_iv.copy()

        iv_used_source = np.full(
            len(df),
            "Yahoo IV",
            dtype=object,
        )

        iv_used_source[
            ~np.isfinite(sigma)
        ] = "Unavailable"

    elif iv_source == "Market Mid → IV":

        sigma = calculated_iv.copy()

        iv_used_source = np.full(
            len(df),
            "Mid-Implied IV",
            dtype=object,
        )

        iv_used_source[
            ~np.isfinite(sigma)
        ] = "Unavailable"

    else:

        # Prefer clean market-calibrated IV.
        # Fall back to Yahoo's reference IV only
        # when a clean market IV cannot be calculated.

        use_market_iv = np.isfinite(
            calculated_iv
        )

        use_yahoo_iv = (
            ~use_market_iv
            & np.isfinite(yahoo_iv)
        )

        sigma = np.where(
            use_market_iv,
            calculated_iv,
            np.where(
                use_yahoo_iv,
                yahoo_iv,
                np.nan,
            ),
        )

        iv_used_source = np.full(
            len(df),
            "Unavailable",
            dtype=object,
        )

        iv_used_source[
            use_market_iv
        ] = "Mid-Implied IV"

        iv_used_source[
            use_yahoo_iv
        ] = "Yahoo IV"

    # ---------------------------------------------------------
    # MODEL VALUES
    # ---------------------------------------------------------

    model_available = (
        np.isfinite(sigma)
        & (sigma > 0)
    )

    theo = np.full(
        len(df),
        np.nan,
        dtype=float,
    )

    if model_available.any():

        theo = vectorized_price(
            option_type,
            spot,
            K,
            T,
            r_pct / 100.0,
            q_pct / 100.0,
            sigma,
        )

    greeks = vectorized_greeks(
        option_type,
        spot,
        K,
        T,
        r_pct / 100.0,
        q_pct / 100.0,
        sigma,
    )

    model_status = np.where(
        model_available,
        "OK",
        "Unavailable: no trusted IV",
    )

    # ---------------------------------------------------------
    # ITM / OTM
    # ---------------------------------------------------------

    if option_type == "call":

        itm = spot > K

    else:

        itm = spot < K

    # ---------------------------------------------------------
    # FINAL DATAFRAME
    # ---------------------------------------------------------

    out = pd.DataFrame({

        "Type":
            option_type.capitalize(),

        "ITM/OTM":
            np.where(
                itm,
                "ITM",
                "OTM",
            ),

        "Strike":
            K,

        "Bid":
            bid,

        "Ask":
            ask,

        "Market Mid":
            market_mid,

        "Spread":
            spread,

        "Spread %":
            spread_pct,

        "Quote Status":
            quote_status,

        "Liquidity":
            liquidity_status,

        "Yahoo IV":
            yahoo_iv,

        "Yahoo IV Status":
            yahoo_iv_status,

        "Calculated IV":
            calculated_iv,

        "IV Status":
            calculated_iv_status,

        "IV Used":
            sigma,

        "IV Used Source":
            iv_used_source,

        "Model Status":
            model_status,

        "Theo (BS)":
            theo,

        "Edge vs Mid":
            theo - market_mid,

        "Last":
            last,

        "Volume":
            volume,

        "Open Interest":
            open_interest,

        "Delta":
            greeks["Delta"],

        "Gamma":
            greeks["Gamma"],

        "Theta / Day":
            greeks["Theta"],

        "Vega / 1%":
            greeks["Vega"],

        "Rho / 1%":
            greeks["Rho"],
    })

    return (
        out
        .sort_values("Strike")
        .reset_index(drop=True)
    )

calls_df = build_chain(calls, "call")
puts_df = build_chain(puts, "put")
chain = pd.concat([calls_df, puts_df], ignore_index=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Greeks", "IV Smile", "BS vs CRR", "Raw Chain"])

with tab1:

    valid_quotes = (
        chain["Market Mid"].notna()
    )

    iv_count = (
        chain["Calculated IV"].notna()
    ).sum()

    spreads = chain.loc[
        valid_quotes,
        "Spread %"
    ]

    a, b, c, d, e = st.columns(5)

    a.metric(
        "Spot",
        f"${spot:,.2f}"
    )

    b.metric(
        "Contracts",
        f"{len(chain):,}"
    )

    c.metric(
        "Valid Quotes",
        f"{valid_quotes.sum():,}"
    )

    d.metric(
        "IV Calibrated",
        f"{iv_count:,}"
    )

    e.metric(
        "Avg Spread",
        (
            f"{spreads.mean():.2f}%"
            if len(spreads)
            else "N/A"
        )
    )

    st.subheader(
        f"Option Chain — {selected_exp}"
    )

    st.caption(
        "Bid / Ask / Market Mid are market observations. "
        "Yahoo IV is an external reference value. "
        "Mid-Implied IV is calculated by solving Black-Scholes "
        "against a filtered market midpoint. "
        "Theo is a model value, not a market quote."
    )

    # ---------------------------------------------------------
    # STRADDLE VIEW
    # ---------------------------------------------------------

    call_view = calls_df[
        [
            "Strike",
            "ITM/OTM",
            "Bid",
            "Ask",
            "Market Mid",
            "Spread %",
            "Calculated IV",
            "IV Status",
            "Theo (BS)",
            "Delta",
            "Gamma",
            "Theta / Day",
            "Vega / 1%",
        ]
    ].copy()

    put_view = puts_df[
        [
            "Strike",
            "ITM/OTM",
            "Bid",
            "Ask",
            "Market Mid",
            "Spread %",
            "Calculated IV",
            "IV Status",
            "Theo (BS)",
            "Delta",
            "Gamma",
            "Theta / Day",
            "Vega / 1%",
        ]
    ].copy()

    call_view.columns = [
        "Strike",
        "Call ITM/OTM",
        "Call Bid",
        "Call Ask",
        "Call Mid",
        "Call Spread %",
        "Call IV",
        "Call IV Status",
        "Call Theo",
        "Call Delta",
        "Call Gamma",
        "Call Theta",
        "Call Vega",
    ]

    put_view.columns = [
        "Strike",
        "Put ITM/OTM",
        "Put Bid",
        "Put Ask",
        "Put Mid",
        "Put Spread %",
        "Put IV",
        "Put IV Status",
        "Put Theo",
        "Put Delta",
        "Put Gamma",
        "Put Theta",
        "Put Vega",
    ]

    straddle = pd.merge(
        call_view,
        put_view,
        on="Strike",
        how="outer",
    ).sort_values("Strike")

    # Put columns on the left and right around strike.
    straddle = straddle[
        [
            "Call ITM/OTM",
            "Call Bid",
            "Call Ask",
            "Call Mid",
            "Call Spread %",
            "Call IV",
            "Call IV Status",
            "Call Theo",
            "Call Delta",
            "Call Gamma",
            "Call Theta",
            "Call Vega",

            "Strike",

            "Put Vega",
            "Put Theta",
            "Put Gamma",
            "Put Delta",
            "Put Theo",
            "Put IV",
            "Put IV Status",
            "Put Spread %",
            "Put Mid",
            "Put Ask",
            "Put Bid",
            "Put ITM/OTM",
        ]
    ]

    # Display IV in percentage terms.
    for col in [
        "Call IV",
        "Put IV",
    ]:
        straddle[col] = (
            straddle[col] * 100.0
        )

    st.dataframe(
        straddle.style.format(
            {
                "Strike": "${:,.2f}",

                "Call Bid": "${:,.2f}",
                "Call Ask": "${:,.2f}",
                "Call Mid": "${:,.2f}",
                "Call Theo": "${:,.2f}",

                "Put Bid": "${:,.2f}",
                "Put Ask": "${:,.2f}",
                "Put Mid": "${:,.2f}",
                "Put Theo": "${:,.2f}",

                "Call Spread %": "{:.2f}%",
                "Put Spread %": "{:.2f}%",

                "Call IV": "{:.2f}%",
                "Put IV": "{:.2f}%",

                "Call Delta": "{:.4f}",
                "Put Delta": "{:.4f}",

                "Call Gamma": "{:.6f}",
                "Put Gamma": "{:.6f}",

                "Call Theta": "{:.4f}",
                "Put Theta": "{:.4f}",

                "Call Vega": "{:.4f}",
                "Put Vega": "{:.4f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        height=650,
    )

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
    with tab4:

        st.subheader(
        "European Black-Scholes vs American CRR"
    )

    st.caption(
        "Both models use the same spot, expiry, "
        "interest rate, dividend yield and IV. "
        "CRR additionally permits early exercise."
    )

    typ = st.selectbox(
        "Option",
        ["Call", "Put"],
    )

    source = (
        calls_df
        if typ == "Call"
        else puts_df
    )

    source = source[
        source["IV Used"].notna()
    ].copy()

    rows = []

    if not source.empty and T > 0:

        sample = source.iloc[
            np.linspace(
                0,
                len(source) - 1,
                min(15, len(source)),
            ).astype(int)
        ].drop_duplicates()

        for _, row in sample.iterrows():

            K = float(row["Strike"])
            sigma = float(row["IV Used"])

            bs = float(
                vectorized_price(
                    typ.lower(),
                    spot,
                    np.array([K]),
                    T,
                    r_pct / 100.0,
                    q_pct / 100.0,
                    np.array([sigma]),
                )[0]
            )

            try:

                cr = CRRBinomial.price(
                    typ.lower(),
                    spot,
                    K,
                    T,
                    r_pct / 100.0,
                    q_pct / 100.0,
                    sigma,
                    crr_steps,
                    True,
                )

                status = "OK"

            except Exception as exc:

                cr = np.nan
                status = (
                    "Unavailable: "
                    + str(exc)
                )

            rows.append(
                {
                    "Strike": K,

                    "Market Mid":
                        row["Market Mid"],

                    "IV Used":
                        sigma,

                    "IV Source":
                        row["IV Used Source"],

                    "BS Theo":
                        bs,

                    "CRR American":
                        cr,

                    "American Premium":
                        (
                            cr - bs
                            if np.isfinite(cr)
                            else np.nan
                        ),

                    "Status":
                        status,
                }
            )

    if rows:

        comparison = pd.DataFrame(rows)

        comparison["IV Used"] *= 100.0

        st.dataframe(
            comparison.style.format(
                {
                    "Strike": "${:,.2f}",
                    "Market Mid": "${:,.4f}",
                    "IV Used": "{:.2f}%",
                    "BS Theo": "${:,.4f}",
                    "CRR American": "${:,.4f}",
                    "American Premium": "${:,.4f}",
                },
                na_rep="—",
            ),
            use_container_width=True,
        )

    else:

        st.warning(
            "No contracts have a reliable IV "
            "available for model comparison."
        )

    st.info(
        "Black-Scholes is the European benchmark. "
        "CRR allows early exercise and is therefore "
        "the American-option benchmark."
    )

with tab5:
    raw = pd.concat([calls.assign(optionType="call"), puts.assign(optionType="put")], ignore_index=True)
    st.dataframe(raw, use_container_width=True, height=650)
