import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from typing import cast


def _validate_type(option_type):
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")


def d1_d2(S, K, T, r, q, sigma):
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    if T <= 0:
        shape = np.broadcast(S, K, sigma).shape
        return (
            np.full(shape, np.nan),
            np.full(shape, np.nan),
        )

    sqrt_t = np.sqrt(T)
    denom = sigma * sqrt_t

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        d1 = (
            np.log(S / K)
            + (r - q + 0.5 * sigma**2) * T
        ) / denom

        d2 = d1 - denom

    return d1, d2


def vectorized_price(option_type, S, K, T, r, q, sigma):
    _validate_type(option_type)

    K = np.asarray(K, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    if T <= 0:
        if option_type == "call":
            return np.maximum(S - K, 0.0)

        return np.maximum(K - S, 0.0)

    d1, d2 = d1_d2(S, K, T, r, q, sigma)

    dq = np.exp(-q * T)
    dr = np.exp(-r * T)

    with np.errstate(invalid="ignore"):
        if option_type == "call":
            return (
                S * dq * norm.cdf(d1)
                - K * dr * norm.cdf(d2)
            )

        return (
            K * dr * norm.cdf(-d2)
            - S * dq * norm.cdf(-d1)
        )


def vectorized_greeks(option_type, S, K, T, r, q, sigma):
    _validate_type(option_type)

    K = np.asarray(K, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    shape = np.broadcast(S, K, sigma).shape
    z = np.zeros(shape, dtype=float)

    if T <= 0:
        return {
            "Delta": z,
            "Gamma": z,
            "Theta": z,
            "Vega": z,
            "Rho": z,
        }

    d1, d2 = d1_d2(S, K, T, r, q, sigma)

    pdf = norm.pdf(d1)
    sqrt_t = np.sqrt(T)

    dq = np.exp(-q * T)
    dr = np.exp(-r * T)

    with np.errstate(divide="ignore", invalid="ignore"):

        gamma = (
            dq * pdf
            / (S * sigma * sqrt_t)
        )

        vega = (
            S * dq * pdf * sqrt_t
            / 100.0
        )

        common = (
            -S * dq * pdf * sigma
            / (2.0 * sqrt_t)
        )

        if option_type == "call":

            delta = dq * norm.cdf(d1)

            theta = (
                common
                - r * K * dr * norm.cdf(d2)
                + q * S * dq * norm.cdf(d1)
            ) / 365.0

            rho = (
                K * T * dr * norm.cdf(d2)
                / 100.0
            )

        else:

            delta = dq * (
                norm.cdf(d1) - 1.0
            )

            theta = (
                common
                + r * K * dr * norm.cdf(-d2)
                - q * S * dq * norm.cdf(-d1)
            ) / 365.0

            rho = (
                -K * T * dr * norm.cdf(-d2)
                / 100.0
            )

    return {
        "Delta": np.asarray(delta, dtype=float),
        "Gamma": np.asarray(gamma, dtype=float),
        "Theta": np.asarray(theta, dtype=float),
        "Vega": np.asarray(vega, dtype=float),
        "Rho": np.asarray(rho, dtype=float),
    }


def implied_volatility_diagnostic(
    option_type,
    market_price,
    S,
    K,
    T,
    r,
    q,
    low=1e-6,
    high=1.0,
    max_high=5.0,
):
    """
    Robust Black-Scholes implied-volatility inversion.

    Returns:
        (iv, status)

    IV is NaN whenever the quote cannot produce a
    reliable numerical solution.
    """

    _validate_type(option_type)

    inputs = [market_price, S, K, T]

    if not all(np.isfinite(x) for x in inputs):
        return np.nan, "Unavailable: non-finite input"

    if market_price <= 0:
        return np.nan, "Unavailable: non-positive market price"

    if S <= 0 or K <= 0 or T <= 0:
        return np.nan, "Unavailable: invalid S/K/T"

    discount_spot = np.exp(-q * T)
    discount_strike = np.exp(-r * T)

    # European no-arbitrage bounds
    if option_type == "call":

        lower_bound = max(
            0.0,
            S * discount_spot
            - K * discount_strike
        )

        upper_bound = S * discount_spot

    else:

        lower_bound = max(
            0.0,
            K * discount_strike
            - S * discount_spot
        )

        upper_bound = K * discount_strike

    price_tolerance = max(
        1e-8,
        1e-7 * max(S, K, market_price)
    )

    # Market price violates theoretical bounds.
    if market_price < lower_bound - price_tolerance:
        return (
            np.nan,
            "Unavailable: below no-arbitrage bound"
        )

    if market_price > upper_bound + price_tolerance:
        return (
            np.nan,
            "Unavailable: above no-arbitrage bound"
        )

    # Exactly at intrinsic value, IV is not reliably identifiable.
    if market_price <= lower_bound + price_tolerance:
        return (
            np.nan,
            "Unavailable: at intrinsic boundary"
        )

    if market_price >= upper_bound - price_tolerance:
        return (
            np.nan,
            "Unavailable: at upper price boundary"
        )

    def objective(vol):
        model_price = vectorized_price(
            option_type,
            S,
            np.array([K], dtype=float),
            T,
            r,
            q,
            np.array([vol], dtype=float),
        )[0]

        return float(model_price - market_price)

    try:

        f_low = objective(low)

        if not np.isfinite(f_low):
            return (
                np.nan,
                "Unavailable: invalid low-volatility price"
            )

        # Dynamically expand the upper bracket.
        hi = max(float(high), 0.05)

        f_high = objective(hi)

        while (
            np.isfinite(f_high)
            and f_high < 0.0
            and hi < max_high
        ):

            hi = min(
                hi * 2.0,
                max_high
            )

            f_high = objective(hi)

        if not np.isfinite(f_high):
            return (
                np.nan,
                "Unavailable: non-finite root bracket"
            )

        # Root is effectively at zero volatility.
        if abs(f_low) <= price_tolerance:
            return (
                np.nan,
                "Unavailable: IV too close to zero"
            )

        # Brent requires a sign change.
        if f_low * f_high > 0.0:
            return (
                np.nan,
                "Unavailable: no implied-volatility root"
            )

        root = brentq(
            objective,
            low,
            hi,
            xtol=1e-8,
            rtol=1e-8, # type: ignore
            maxiter=100,
            full_output=False,
            disp=False,
        )

        # Pylance currently has an overly broad SciPy
        # return annotation, so explicitly cast the scalar.
        iv = cast(float, root)

        if not np.isfinite(iv):
            return (
                np.nan,
                "Unavailable: non-finite IV root"
            )

        if iv <= 0.0:
            return (
                np.nan,
                "Unavailable: non-positive IV root"
            )

        if iv > max_high:
            return (
                np.nan,
                "Unavailable: implausibly high IV"
            )

        return float(iv), "OK"

    except (
        ValueError,
        RuntimeError,
        FloatingPointError,
        OverflowError,
    ):
        return (
            np.nan,
            "Unavailable: root solver did not converge"
        )


def implied_volatility(
    option_type,
    market_price,
    S,
    K,
    T,
    r,
    q,
    low=1e-6,
    high=1.0,
):
    iv, _ = implied_volatility_diagnostic(
        option_type,
        market_price,
        S,
        K,
        T,
        r,
        q,
        low=low,
        high=high,
    )

    return iv


def implied_volatility_vectorized(
    option_type,
    S,
    K,
    T,
    r,
    q,
    market_prices,
    return_status=False,
):
    K = np.asarray(K, dtype=float)
    prices = np.asarray(
        market_prices,
        dtype=float
    )

    out = np.full(
        K.shape,
        np.nan,
        dtype=float,
    )

    status = np.full(
        K.shape,
        "Unavailable: no valid market mid",
        dtype=object,
    )

    for i in range(len(K)):

        out[i], status[i] = (
            implied_volatility_diagnostic(
                option_type,
                prices[i],
                float(S),
                float(K[i]),
                T,
                r,
                q,
            )
        )

    if return_status:
        return out, status

    return out