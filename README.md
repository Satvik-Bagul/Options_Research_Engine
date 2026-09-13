# Quantitative Options Research Engine

Streamlit options analytics app with Black-Scholes, market-calibrated implied volatility, and an American CRR binomial model.

## Key fixes

- Continuous dividend yield `q` in pricing and Greeks.
- Vectorized Greek/pricing calculations instead of `iterrows`.
- Market Mid is distinct from theoretical value.
- `Theo (BS)` is shown separately from Bid/Ask/Mid.
- Brent root-finding backs out IV from valid bid/ask mids when Yahoo IV is unavailable.
- Zero/stale quotes are excluded from IV calibration.
- American CRR supports early exercise and dividend yield.
- Adaptive CRR step count plus Jarrow-Rudd fallback prevents the previous invalid risk-neutral probability crash.
- ITM/OTM labels.
- Yahoo-style chain layout with Bid, Ask, Mid, Spread, IV and Greeks.
- `st.cache_data` is used for serializable Yahoo payloads rather than caching `yf.Ticker` resources.

## Market Mid vs Theo

Mid is `(Bid + Ask) / 2` and is an observed market quote convention.

Theo is a model output. In this project `Theo (BS)` is the Black-Scholes theoretical price using the selected volatility.

If IV is calibrated from the Mid, the BS Theo will naturally be close to the Mid. That is calibration, not an assertion that Mid is theoretical value.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Yahoo Finance quotes may be delayed, stale, zero, or incomplete. Treat this as a research project, not an execution system.

## Suggested future additions

1. Historical delta-hedging P&L simulator.
2. SVI/SABR implied-volatility surface calibration.
3. American-option Greeks by bump-and-revalue.
