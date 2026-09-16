**Quantitative Options Research Engine**

A Python + Streamlit application for learning how options are priced,
how market prices imply volatility, and how different pricing models
behave.

The project combines option-chain data from Yahoo Finance with
quantitative finance models including Black-Scholes and the
Cox-Ross-Rubinstein (CRR) binomial model.

Considering this project is the cumulation options trading concepts learned 
across 3 months', I want this document to serve as a "journal" of my 
learning process. Not only do I hope that this helps me reinforce my 
undeerstanding but also be understandable to someone who has never traded an
option, while still demonstrating concepts used in quantitative finance
and options market making.

Important: This is a research and educational project. Yahoo
Finance data can be delayed, stale, incomplete, or inconsistent. This
application is not an execution system and should not be used as a
source of executable trading prices.

-----------------------------------------------------------------------------------------


**Things that I want to talk about:**


1. What is this project?

2. Options explained simply

3. What the application does

4.Market data vs model data

5.Bid, Ask, Mid, Spread, and Last

6. How option prices are
determined

7. Black-Scholes

8. Dividend yield

9. Implied volatility

10. Why Brent root-finding is used

11. Bad quotes and liquidity
filtering

12. What happens when IV cannot be
calculated

13. Theo (theoretical value)

14. The Greeks

15. European vs American options

16. CRR binomial model

17. CRR numerical stability

18. Jarrow-Rudd fallback

19. ITM, ATM, and OTM

20. IV smile and volatility skew

21. Application workflow

22. Performance and vectorization

23. Caching

24. Numerical safety

25. Project structure

26. Running the application

27. Testing

28. Learning resources

29. Future improvements

30. Limitations

31. Disclaimer (IDK I was told that this was required :/ )

-----------------------------------------------------------------------------------------

**What is this project?**


The Quantitative Options Research Engine is an options analytics
application built with:

PYTHON for quantitative calculations

NUMPY for numerical computation

PANDAS for market-data processing

SCIPY for statistics and numerical root-finding

YFINANCE for Yahoo Finance market data

STREAMLIT for the interactive interface

PLOTLY for charts

***************************************************************************************

**The application takes an option chain and answers questions such as:**

1. What is the market currently quoting?

2. What volatility is implied by that market price?

3. What does a pricing model think the option is worth?

4. How sensitive is the option to changes in the underlying, volatility,
time, and interest rates?

5. Does an American-style model produce a different value from a
European-style model?

The project is therefore both an options calculator and a
demonstration of how a small quantitative research system can be
structured.

----------------------------------------------------------------------------------------

**Options explained simply**

An option is a financial contract whose value depends on another
asset, called the underlying. 

This contract gives the holder the right, but not the obligation to buy or sell an underlying for a pre-determined price (Strike Price) at a later date (Date of Expiry). 

For example:

Underlying: SPY
Strike:     $600
Expiration: December 2026

##There are two basic types.

1. Call option

A call gives the buyer the right, but not the obligation, to BUY the
underlying at the strike price.

Example:

SPY = $620
Call strike = $600

The call has value because the holder has the right to buy at $600 when
the market is at $620.  Thus, the holder makes a profit of $20.

2. Put option

A put gives the buyer the right, but not the obligation, to SELL the
underlying at the strike price.

Example:

SPY = $580
Put strike = $600

The put has value because the holder can sell at $600 when the market
is at $580. Thus, making a profit of $20.

The price paid for an option is called the PREMIUM.

//Beginner resource://
https://www.optionseducation.org/optionsoverview/what-is-an-option

------------------------------------------------------------------------------------

**What the application does:**

The application retrieves an option chain and processes the contracts.

##It can work with:

-Underlying price
-Strike
-Expiration
-Call / Put
-Bid
-Ask
-Last price
-Volume
-Open interest
-Yahoo IV

##It then calculates or displays:

-Market Mid
-Spread
-Calculated IV
-Theoretical value
-Delta
-Gamma
-Theta
-Vega
-Rho
-ITM / OTM classification


##The application also compares:

Black-Scholes with CRR Binomial

---------------------------------------------------------------------------------

**Market data vs model data:**

This is one of the most important ideas in the project.

There are two fundamentally different kinds of numbers.

##Market values

These come from the market-data source:

Bid
Ask
Last
Volume
Open Interest

##Model values

These are calculated by mathematical models:

Theo
Calculated IV
Delta
Gamma
Theta
Vega
Rho

The distinction is:

MARKET
Bid
Ask
Mid
Spread
Last
Volume
Open Interest

MODEL
Theo
IV
Delta
Gamma
Theta
Vega
Rho

Keeping these categories separate prevents a model estimate from being
presented as an observed market price.

This distinction is especially important in options market making.

One of the courses that got me hooked onto options trading is:
##Akuna Capital's Options 101 course covers theoretical values ("Theos"),
volatility, Greeks, and delta hedging:

https://akunacapital.teachable.com/p/options101

-----------------------------------------------------------------------------------

**Bid, Ask, Mid, Spread, and Last**

##Bid

The bid is the price currently offered by a buyer.

Bid = $9.80

##Ask

The ask, or offer, is the price at which a seller is offering the
option.

Ask = $10.20

##Mid

When both quotes are valid:

Mid = (Bid + Ask) / 2

Example:

Bid = $9.80
Ask = $10.20

Mid = $10.00

The Mid is a market-derived value, not a model price.

##Spread

Spread = Ask - Bid

Example:

$10.20 - $9.80 = $0.40

A large spread can indicate lower liquidity or a less reliable quote.

##Last

Last is the most recent reported trade.

It is not necessarily the price available now.

For example:

Last = $10.00
Bid  = $8.50
Ask  = $11.50

The last trade may have happened earlier under different market
conditions.

That is why the application does not automatically treat Last as the
current Mid.

------------------------------------------------------------------------------------

**How option prices are determined**

An option's value depends on several factors.

The main inputs are:

S  = underlying price
K  = strike price
T  = time remaining
r  = risk-free interest rate
q  = dividend yield
σ  = volatility

In plain English:

##Underlying price (S)

If the underlying moves, the option usually moves too.

##Strike price(K)

The strike is the price at which the option can be exercised.

##Time to expiration(T)

More time generally gives the option more opportunity to become
valuable. This is an important concept that affects volatility. 
More time == higher chance the option ends up "IN THE MONEY"

##Interest rate(r)

Interest rates affect the value of money paid or received in the future.

##Dividend yield(q)

Dividends affect the economics of holding the underlying.

##Volatility(σ)

Volatility describes how much the underlying is expected to move.

Higher volatility generally increases the value of both calls and puts
because larger possible moves create more potential payoff.

Beginner resource:

https://www.optionseducation.org/optionsoverview/options-pricing

----------------------------------------------------------------------------------------

**Black-Scholes**

The application uses the Black-Scholes model as its main
European-style pricing model. 

##The simplified idea is:

Inputs
  ↓
Black-Scholes
  ↓
Theoretical option price

##For a call:

C = S e^(-qT) N(d1) - K e^(-rT) N(d2)

##For a put:

P = K e^(-rT) N(-d2) - S e^(-qT) N(-d1)

##where:

d1 = [ln(S/K) + (r-q+σ²/2)T] / (σ√T)

d2 = d1 - σ√T

Honeslty it looks a bit complicated but, 
The idea is that the model converts assumptions about:

Price
Strike
Time
Rates
Dividends
Volatility

into an estimated option value.

Black-Scholes is:

Well known

Fast

Mathematically useful

A foundation for many quantitative finance concepts

But it is not a perfect description of real markets.

----------------------------------------------------------------

**Dividend yield**

The application includes a continuous dividend yield (q).

A simplified Black-Scholes implementation may assume:

q = 0

but stocks and ETFs can pay dividends.

The application therefore includes q in its pricing, Greeks, and IV
calculations.

The basic intuition is:

Higher dividend yield
        ↓
Generally lowers call value
Generally increases put value

The exact effect depends on all the other inputs.

Different dividend assumptions are also one reason two IV calculations
can differ. (Also why our calculated IV in this program may differ from the Yahoo IV [We do not know the parameters considered by Yahoo Finance.])

------------------------------------------------------------------------------

**Implied volatility**

Implied volatility, or IV, works backwards from an option price.

In the sense that, we take the option's market price and solve for
the volatility that would make a pricing model (The Black-Scholes/CRR Binomial) 
produce that price.



##Normal pricing:

Volatility + other inputs
            ↓
        Option price

##Implied volatility:

Market option price
        ↓
     Pricing model
        ↓
"What volatility makes the model
 produce this price?"
        ↓
 Implied volatility

Example:

Market Mid = $10.00
Calculated IV = 25%

This means that, under the model assumptions, 25% volatility produces a
price close to the observed market price.

IV is therefore calculated, not directly observed like Bid or Ask.

-----------------------------------------------------------------------------------------

**Why Brent root-finding is used**

##Black-Scholes naturally answers:

Given volatility → calculate price

##We want to solve:

Given price → calculate volatility

There is no simple closed-form formula for standard Black-Scholes
implied volatility.

##So the application solves:

ModelPrice(IV) - MarketPrice = 0 ................... ModelPrice(IV) = Price calculated with the calculated IV.   

##using SciPy's brentq() root finder.

Brent's method searches for a root inside a bracket where the function
changes sign.

Resource:

https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html

##Why brentq() can fail

Not every market price corresponds to a valid IV.

For example:

Impossible market price
        ↓
No volatility can reproduce it
        ↓
No mathematical root
        ↓
brentq cannot converge

##The application therefore checks:

1. Are the inputs are valid?

2. Is the market price is finite?

3. Is the market price is inside theoretical bounds?

4. Is the root is bracketed?

5. Does Brent actually converge?

##If not, the table outputs:

"Calculated IV = unavailable"

instead of crashing.

--------------------------------------------------------------------------

**Bad quotes and liquidity filtering**

Real market data is messy.

The dataset we use provided by Yahoo Finance can contain:

1. Missing bids

2. Missing asks

3. Zero bids

4. Zero asks

5. Very wide spreads

6. Stale trades

7. Missing volume

8. Missing open interest

9. Extreme IV values

10. Prices that violate theoretical bounds

Therefore the application has to filter and classify quotes before using them for IV
calibration.

There are other unique scenarious in our dataset where:

1. Zero quote

Bid = $0
Ask = $0

This should not automatically become:

Mid = $0

It may mean that no meaningful two-sided market is available.

The application can therefore mark the Mid and IV as unavailable.

2. Crossed market

Bid = $10
Ask = $9

This is not a normal valid market and should be rejected.

3. Wide spread

Bid = $10
Ask = $20

The mathematical midpoint is $15, but the quote is extremely wide.

A wide quote can therefore be excluded from reliable IV calibration.

The principle is:

A number appearing in a data feed does not automatically make it a
trustworthy market observation.

---------------------------------------------------------------------------------

**What happens when IV cannot be calculated:**

The application deliberately avoids creating a fake IV such as:
Yea so i did that initially when I was testing out my IV models (which sounds alot worse than it actually is), however i reverted from that because while having a default IV is good to prevent the program from crashing, it generated incorrect Greeks for options if the bid and ask prices are too far apart.

IV = 0.20

when the real calculation fails.

That creates a phantom IV.

For example:

Bad quote
   ↓
IV solver fails
   ↓
20% inserted
   ↓
Theo calculated
   ↓
Greeks calculated

##The numbers can look precise even though they are based on an arbitrary
assumption.##

Instead, I've opted for an output that looks like:

IV = unavailable

and, when there is no reliable volatility input:

Theo = unavailable
Greeks = unavailable

It is better to show:

N/A

than a precise-looking number with no reliable basis.

--------------------------------------------------------------------------------

**Theo: theoretical value**

Theo means theoretical value.

It means:

"According to the model, what should this option be worth?"

For example:

Bid         $9.80
Ask         $10.20
Market Mid  $10.00

Model IV    24%

Theo        $10.15

The market provides one set of information.

The model provides another.

Therefore:

Market Mid ≠ Theo

as concepts.

However, there is an important detail.

If we calculate IV directly from the Market Mid and then use that IV to
calculate Black-Scholes Theo, the Theo will naturally be very close to
the Mid.

That is expected:

Market Mid
    ↓
calibrate IV
    ↓
Black-Scholes
    ↓
Theo ≈ Market Mid

This is calibration, not proof that Mid and Theo are the same thing.

In a more advanced market-making system, Theo can come from a volatility
surface or other model assumptions rather than fitting each contract
independently to its own midpoint.

Akuna Capital Options 101:

https://akunacapital.teachable.com/p/options101

------------------------------------------------------------------------------

**The Greeks**

The Greeks describe how sensitive an option is to changes in
different inputs.

The application calculates:

1. Delta
2. Gamma
3. Theta
4. Vega
5. Rho

Beginner resource:

https://www.optionseducation.org/advancedconcepts/understanding-options-greeks

1. Delta

Delta measures sensitivity to the underlying price.

For example:

Delta = 0.60

roughly means a small $1 move in the underlying changes the option's
theoretical value by about $0.60, assuming other inputs stay constant.

Typical ranges:

Call:  0 to 1
Put:  -1 to 0

2. Gamma

Gamma measures how quickly Delta changes.

Think of it as:

Delta = current slope
Gamma = how quickly the slope changes

Gamma is especially important near the strike and near expiration.

3. Theta

Theta measures sensitivity to the passage of time.

For many long options:

Time passes
    ↓
Less time remains
    ↓
Option often loses time value

4. Vega

Vega measures sensitivity to volatility.

If an option has positive vega, increasing volatility generally
increases its theoretical value.

5. Rho

Rho measures sensitivity to interest rates.

It is generally more important for longer-dated options.

-------------------------------------------------------------------------------------------------

**European vs American options**

1. European option

A European option can only be exercised at expiration.

2. American option

An American option can generally be exercised before expiration, subject
to the contract terms.

Many listed equity and ETF options are American-style.

##This matters because early exercise can have value.

Black-Scholes is fundamentally a European-style model:

Black-Scholes
      ↓
European-style value

The application also uses CRR for American-style valuation:

CRR Binomial
      ↓
American-style value
      ↓
Early exercise can be considered

This distinction is particularly relevant for some dividend-paying
underlyings and deep in-the-money options.

-----------------------------------------------------------------------------------------

**CRR binomial model**

The Cox-Ross-Rubinstein (CRR) binomial model approaches option
pricing differently from Black-Scholes.

Instead of assuming one continuous path, it creates a tree of possible
up and down movements.

Simplified:

                 S
              /     \
            Su       Sd
           /  \     /  \
        Su²  Sud   Sud  Sd²
         ...

At expiration, the model calculates the option payoff.

Then it works backwards through the tree.

For an American option, each node compares:

Value from continuing to hold

against:

Value from exercising now

and takes the larger value.

That is how early exercise is incorporated.

------------------------------------------------------------

**CRR numerical stability**

The standard CRR model calculates:

dt = T / N

u = exp(σ√dt)

d = 1/u

p = [exp((r-q)dt) - d] / (u-d)

The risk-neutral probability should satisfy:

0 <= p <= 1

For certain combinations of inputs, a finite-step CRR tree can produce:

p < 0

or:

p > 1

##This can be more likely with:

1. Very short expiration

2. Very low volatility

3. Large interest-rate/dividend drift

4. Too few tree steps


The application does not simply use:

``p = np.clip(p, 0, 1)``

because that hides the numerical problem and changes the model.

Instead it can:

1. Start with the requested step count.

2. Check the probability.

3. Increase the number of steps if needed.

4. Recalculate.

Use a Jarrow-Rudd fallback if necessary.

-----------------------------------------------------------------------

**Jarrow-Rudd fallback**

The Jarrow-Rudd binomial model is another binomial-tree
construction.

The application can use it as a fallback when the standard CRR
construction remains numerically unsuitable.

Conceptually:

Try CRR
   ↓
Invalid probability?
   ↓
Increase steps
   ↓
Try again
   ↓
Still unsuitable?
   ↓
Jarrow-Rudd fallback

If no reliable result can be produced, the application should report the
failure instead of inventing a price.

-----------------------------------------------------------------------------------------

**ITM, ATM, and OTM**

Options are commonly classified as:

ITM = In the Money

ATM = At the Money

OTM = Out of the Money

##Call

Underlying > Strike → ITM
Underlying ≈ Strike → ATM
Underlying < Strike → OTM

##Put

Underlying < Strike → ITM
Underlying ≈ Strike → ATM
Underlying > Strike → OTM

These labels make the option chain easier to understand.

-----------------------------------------------------------------------------------

**IV smile and volatility skew**

If every strike had exactly the same implied volatility, an IV chart
across strikes would be roughly flat.

Real markets often do not behave that way.

IV can vary by strike, producing patterns such as:

          IV
           ^
           |
      \   /
       \ /
        \____
           → Strike

This is often called an IV smile ( This is the best i can represent 
the graph in this documentation. Refer to the website opengine.streamlit.app
 for a proper example of an IV smile graph).

If one side consistently has higher IV, this is commonly called
volatility skew.

These patterns show that the market does not necessarily assign the same
volatility to every strike.

The application's IV Smile view provides an introduction to this idea.

------------------------------------------------------------------------------------------

**Application workflow**

The general pipeline is:

Yahoo Finance
      │
      ▼
Option Chain
      │
      ▼
Quote Validation
      │
      ├── Bad quote ────────► Reject / Flag
      │
      └── Usable quote
              │
              ▼
        Market Mid
              │
              ▼
       IV Calibration
              │
              ▼
   Black-Scholes/CRR Binomial
              │
        ┌─────┴─────┐
        ▼           ▼
      Theo        Greeks
        │
        ▼
    Streamlit UI

Separate model comparison:

        CRR Binomial
              │
              ▼
     American-style Theo

-------------------------------------------------------------------------------------

**Performance and vectorization**

An option chain can contain many contracts.

An inefficient approach would calculate every option with:

DataFrame.iterrows()

That's why in this project I instead use NumPy-based vectorized calculations where
possible.

Conceptually:

Row by row:

Option 1 → calculate
Option 2 → calculate
Option 3 → calculate

Vectorized:

[Option 1, Option 2, Option 3, ...]
                 ↓
        NumPy calculation

This reduces Python-level looping and improves performance.

The IV solver still works contract-by-contract because each contract has
its own numerical root-finding problem.

---------------------------------------------------------------------------------------

**Caching**

Streamlit reruns the application when widgets change.

Without caching, the same Yahoo Finance data could be downloaded
repeatedly.

The project therefore uses:

@st.cache_data

for serializable market-data results.

##Streamlit documentation:

https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data

The application avoids treating a yfinance.Ticker object as ordinary
cached data and instead caches the serializable data required by the
application.

--------------------------------------------------------------------------------------------

**Numerical safety**

Financial formulas can behave badly around edge cases.

The application checks conditions such as:

1. S <= 0
2. K <= 0
3. T <= 0
4. σ <= 0
5. NaN values
6. Infinite values
7. Invalid market prices
8. Impossible option prices
9. Unbracketed IV roots
10. IV non-convergence
11. Invalid CRR probabilities

--------------------------------------------------------------------------------------------------

**Expiration approaching zero**

Black-Scholes contains terms involving:

1 / √T

As:

T → 0

these terms can become unstable, because we can't divide by zero (obviously).

The application therefore treats expiration as a special case rather
than blindly evaluating a division by zero.

At exact expiration, the option price becomes its payoff/intrinsic
value. Ordinary Black-Scholes Greeks are not well-behaved at that exact
point, so the application should avoid presenting unstable values as if
they were precise.

-------------------------------------------------------------------------------------------

**Project structure**

quant_options_engine/
│
├── app.py
│
├── src/
│   ├── __init__.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── black_scholes.py
│   │   └── crr.py
│   │
│   └── data/
│       ├── __init__.py
│       └── market_data.py
│
├── requirements.txt
├── README.md
├── .gitignore
└── run_app.bat

##app.py

Streamlit interface and application workflow.

##black_scholes.py

Contains:

1. Black-Scholes pricing

2. Dividend-aware calculations

3. Greeks

4. Implied volatility

5. Brent root-finding

6. Numerical safety checks

##crr.py

Contains:

1. CRR binomial pricing

2. American early-exercise logic

3. Adaptive step count

4. Jarrow-Rudd fallback

##market_data.py

Handles:

1. Yahoo Finance data

2. Underlying information

3. Option-chain retrieval

4. Data preparation

----------------------------------------------------------------------------------------------------

**Running the application**

(ChatGPT'ed this part to follow usual GitHub repo lingo)

1. Clone the repository

git clone <your-repository-url>
cd quant_options_engine

2. Create a virtual environment

Windows

python -m venv .venv
.venv\Scripts\activate

macOS / Linux

python -m venv .venv
source .venv/bin/activate

Python virtual environments:

https://docs.python.org/3/library/venv.html

3. Install dependencies

pip install -r requirements.txt

4. Start Streamlit

streamlit run app.py

-----------------------------------------------------------------------------------------

**Testing**

The application should be tested at both the mathematical and
data-quality levels.

##Mathematical tests

1. Black-Scholes benchmark

Use known inputs and compare the result against a trusted benchmark.

Put-call parity

For European options with continuous dividends:

C - P = S e^(-qT) - K e^(-rT)

The calculated values should approximately satisfy this relationship.

IV round trip

Start with:

IV = 25%

Calculate an option price.

Feed that price into the IV solver.

The result should be close to:

25%

Greek sanity checks

For a normal long call:

Delta > 0
Gamma > 0
Vega > 0

For a normal long put:

Delta < 0
Gamma > 0
Vega > 0

CRR convergence

Increase CRR steps:

100
200
400
800

The price should generally become more stable.

American vs European

When early exercise has value:

American value >= European value

Bad-data tests

Test:

Bid = 0
Ask = 0

Missing Bid
Missing Ask

Bid > Ask

Very wide spread

Market price below theoretical lower bound

Market price above theoretical upper bound

Expected behavior:

No application crash
Invalid contracts flagged or excluded
IV shown as unavailable when appropriate

Brent failure test

Provide a market price that cannot produce an implied-volatility
solution.

Expected:

No application crash
IV = unavailable

CRR stability test

Test very short expiration and low volatility.

Expected:

No "Risk-neutral probability outside [0,1]" crash

The implementation should adapt its tree or use its fallback logic.

Learning resources

Options fundamentals

The Options Industry Council is a good starting point for:

Calls

Puts

Strike prices

Expiration

Premiums

Option pricing

https://www.optionseducation.org/

Begin here:

https://www.optionseducation.org/optionsoverview/what-is-an-option

Options pricing

https://www.optionseducation.org/optionsoverview/options-pricing

Greeks

https://www.optionseducation.org/advancedconcepts/understanding-options-greeks

Akuna Capital Options 101

This is particularly relevant because it approaches options from a
market-making perspective.

Topics include:

Options basics

Time premium

Put-call parity

Theoretical values / Theos

Greeks

Volatility

Vega

Delta hedging

https://akunacapital.teachable.com/p/options101

Black-Scholes

The original Black-Scholes paper is:

Fischer Black and Myron Scholes, "The Pricing of Options and Corporate
Liabilities."

https://www.jstor.org/stable/1831029

Numerical methods

SciPy's brentq documentation:

https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html

NumPy

https://numpy.org/doc/

Pandas

https://pandas.pydata.org/docs/

yfinance

https://ranaroussi.github.io/yfinance/

Streamlit

https://docs.streamlit.io/

Future improvements

1. Historical delta-hedging P&L simulator

Simulate:

Option position
      ↓
Delta hedge
      ↓
Underlying moves
      ↓
Rebalance hedge
      ↓
Track P&L

This would connect the Greeks to actual portfolio behavior.

2. SVI volatility-surface calibration

Instead of calculating IV independently for each strike, fit a smooth
surface across:

Strike
Expiration
Volatility

This would make the IV Smile analysis substantially more realistic.

3. SABR volatility model

Add SABR calibration for modeling volatility smiles and term structures.

4. American-option Greeks by bump-and-revalue

Black-Scholes has analytical Greeks.

American options are more complicated.

A future version can estimate American Greeks numerically:

Price(S + bump)
Price(S - bump)
       ↓
Estimate Delta

and similarly for other sensitivities.

5. Maturity-matched interest-rate curve

The current application allows a user-entered risk-free rate.

A more advanced implementation would use an interest-rate curve:

Short maturity → one rate
Medium maturity → another rate
Long maturity → another rate

and interpolate the appropriate rate for each expiration.

6. Dividend curve

Instead of one constant dividend yield, a more advanced model could use
expected discrete dividends or a dividend term structure.

7. Better market-data source

A production-quality system would use a more reliable market-data source
with:

Real-time or appropriately licensed data

Exchange timestamps

Quote conditions

Better liquidity information

More reliable bid/ask updates

Limitations

Yahoo Finance is not an execution feed

Data may be delayed, stale, incomplete, or inconsistent.

Yahoo quote ≠ guaranteed executable market

Risk-free rate

The application currently uses a user-entered risk-free rate rather than
automatically constructing a full yield curve.

Dividend yield

The application uses a dividend-yield assumption rather than a full
discrete-dividend model.

Black-Scholes assumptions

Real markets can have:

Volatility smiles

Volatility skew

Jumps

Transaction costs

Bid/ask spreads

Changing interest rates

Discrete dividends

Early exercise

Liquidity constraints

CRR is still a model

CRR is useful for American-style pricing, but it is still a numerical
approximation based on assumptions.

IV is model-dependent

There is no completely model-independent "true IV."

IV depends on:

Market price
Pricing model
Interest rate
Dividend assumption
Time convention
Numerical method

Two systems can therefore produce different IVs from the same market
data if their assumptions differ.

Disclaimer

This project is for education, research, and software-development
purposes only.

It is not investment advice.

It is not a trading recommendation.

It is not an execution system.

Theoretical prices, implied volatilities, Greeks, and other outputs
depend on model assumptions and the quality of the underlying market
data.

Do not use this application as the sole basis for financial decisions.

Why this project matters for quantitative finance

The project demonstrates a small version of a much larger quantitative
workflow:

Market Data
    ↓
Data Cleaning
    ↓
Mathematical Model
    ↓
Numerical Methods
    ↓
Risk Sensitivities
    ↓
Visualization
    ↓
Research

The interesting part is not simply calculating an option price.

The interesting part is understanding:

What data went into the calculation, what assumptions were made,
what numerical methods were used, and how confident should we be in
the result?

That is the core mindset behind quantitative research.  
