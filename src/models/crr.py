import math
import numpy as np

class CRRBinomial:
    @staticmethod
    def _parameters(T,r,q,sigma,steps):
        dt=T/steps
        u=math.exp(sigma*math.sqrt(dt)); d=1/u
        p=(math.exp((r-q)*dt)-d)/(u-d)
        return dt,u,d,p

    @classmethod
    def price(cls,option_type,S,K,T,r,q,sigma,steps=400,american=True,max_steps=2000):
        if option_type not in ("call","put"): 
            raise ValueError("Invalid option type")
        if S<=0 or K<=0: 
            raise ValueError("S and K must be positive")
        if not np.isfinite(T) or T <= 0: 
            return max(S-K,0) if option_type=="call" else max(K-S,0)
        if not np.isfinite(sigma) or sigma <= 0: return max(S-K,0) if option_type=="call" else max(K-S,0)

        n=max(1,int(steps))
        while True:
            dt,u,d,p=cls._parameters(T,r,q,sigma,n)
            if 0<=p<=1: break
            n*=2
            if n > max_steps:

                fallback_steps = min(int(max_steps),2000,)
                return cls._jarrow_rudd(option_type,S,K,T,r,q,sigma,fallback_steps,american,)

        disc=math.exp(-r*dt)
        j=np.arange(n+1); stock=S*(u**j)*(d**(n-j))
        values=np.maximum(stock-K,0) if option_type=="call" else np.maximum(K-stock,0)

        for step in range(n-1,-1,-1):
            cont=disc*(p*values[1:]+(1-p)*values[:-1])
            if american:
                j=np.arange(step+1); stock=S*(u**j)*(d**(step-j))
                exercise=np.maximum(stock-K,0) if option_type=="call" else np.maximum(K-stock,0)
                values=np.maximum(cont,exercise)
            else:
                values=cont
        return float(values[0])

    @staticmethod
    def _jarrow_rudd(option_type,S,K,T,r,q,sigma,n,american):
        dt=T/n; p=0.5
        u=math.exp((r-q-0.5*sigma*sigma)*dt+sigma*math.sqrt(dt))
        d=math.exp((r-q-0.5*sigma*sigma)*dt-sigma*math.sqrt(dt))
        disc=math.exp(-r*dt)
        j=np.arange(n+1); stock=S*(u**j)*(d**(n-j))
        values=np.maximum(stock-K,0) if option_type=="call" else np.maximum(K-stock,0)
        for step in range(n-1,-1,-1):
            cont=disc*(p*values[1:]+(1-p)*values[:-1])
            if american:
                j=np.arange(step+1); stock=S*(u**j)*(d**(step-j))
                exercise=np.maximum(stock-K,0) if option_type=="call" else np.maximum(K-stock,0)
                values=np.maximum(cont,exercise)
            else: values=cont
        return float(values[0])
