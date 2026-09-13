import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from typing import cast

def _validate_type(t):
    if t not in ("call","put"): 
        raise ValueError("option_type must be 'call' or 'put'")

def d1_d2(S,K,T,r,q,sigma):
    S=np.asarray(S,float); 
    K=np.asarray(K,float); 
    sigma=np.asarray(sigma,float)

    sqrtT=np.sqrt(max(T,0.0))
    denom=sigma*sqrtT
    
    with np.errstate(divide="ignore",invalid="ignore"):
        d1=(np.log(S/K)+(r-q+0.5*sigma**2)*T)/denom
        d2=d1-denom
    return d1,d2

def vectorized_price(option_type,S,K,T,r,q,sigma):
    _validate_type(option_type)
    K=np.asarray(K,float); sigma=np.asarray(sigma,float)
    if T<=0:
        return np.maximum(S-K,0) if option_type=="call" else np.maximum(K-S,0)
    d1,d2=d1_d2(S,K,T,r,q,sigma)
    dq=np.exp(-q*T); dr=np.exp(-r*T)
    if option_type=="call":
        return S*dq*norm.cdf(d1)-K*dr*norm.cdf(d2)
    return K*dr*norm.cdf(-d2)-S*dq*norm.cdf(-d1)

def vectorized_greeks(option_type,S,K,T,r,q,sigma):
    _validate_type(option_type)
    K=np.asarray(K,float); sigma=np.asarray(sigma,float)
    shape=np.broadcast(S,K,sigma).shape
    z=np.zeros(shape)
    if T<=0:
        return {"Delta":z,"Gamma":z,"Theta":z,"Vega":z,"Rho":z}
    d1,d2=d1_d2(S,K,T,r,q,sigma)
    pdf=norm.pdf(d1); st=np.sqrt(T); dq=np.exp(-q*T); dr=np.exp(-r*T)
    gamma=dq*pdf/(S*sigma*st)
    vega=S*dq*pdf*st/100.0
    common=-S*dq*pdf*sigma/(2*st)
    if option_type=="call":
        delta=dq*norm.cdf(d1)
        theta=(common-r*K*dr*norm.cdf(d2)+q*S*dq*norm.cdf(d1))/365.0
        rho=K*T*dr*norm.cdf(d2)/100.0
    else:
        delta=dq*(norm.cdf(d1)-1)
        theta=(common+r*K*dr*norm.cdf(-d2)-q*S*dq*norm.cdf(-d1))/365.0
        rho=-K*T*dr*norm.cdf(-d2)/100.0
    return {"Delta":np.asarray(delta,float),"Gamma":np.asarray(gamma,float),
            "Theta":np.asarray(theta,float),"Vega":np.asarray(vega,float),
            "Rho":np.asarray(rho,float)}

def implied_volatility(option_type,market_price,S,K,T,r,q,low=1e-6,high=6.0):
    _validate_type(option_type)
    if not np.isfinite(market_price) or market_price<=0 or S<=0 or K<=0 or T<=0: return np.nan
    dq=np.exp(-q*T); dr=np.exp(-r*T)
    if option_type=="call": lo=max(0,S*dq-K*dr); hi=S*dq
    else: lo=max(0,K*dr-S*dq); hi=K*dr
    tol=max(1e-8,1e-6*S)
    if market_price < lo-tol or market_price > hi+tol: return np.nan
    def f(v):
        return float(vectorized_price(option_type,S,np.array([K]),T,r,q,np.array([v]))[0])-market_price

    return cast(float,brentq(f,low, high, xtol=1e-8, maxiter=100,full_output=False))

def implied_volatility_vectorized(option_type,S,K,T,r,q,market_prices):
    K=np.asarray(K,float); 
    prices=np.asarray(market_prices,float)
    out=np.full(K.shape,np.nan)
    for i in range(len(K)):
        out[i]=implied_volatility(option_type,prices[i],float(S),float(K[i]),T,r,q)
    return out
