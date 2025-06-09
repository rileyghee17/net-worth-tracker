import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
import datetime

# File to store history snapshots
HISTORY_FILE = "net_worth_history.csv"

# Page configuration
st.set_page_config(layout="wide")
st.title("My Net-Worth Tracker")

# --- URL query parameters for defaults ---
params = st.query_params

def get_param(key, default, cast_func):
    if key in params:
        try:
            return cast_func(params[key][0])
        except:
            return default
    return default

# --- Inputs ---
cash = st.number_input(
    "💵 Cash Balance (AUD)",
    min_value=0.0,
    value=get_param("cash", 21081.0, float),
    step=100.0,
    key="cash"
)
property_val = st.number_input(
    "🏠 Property Market Value (AUD)",
    min_value=0.0,
    value=get_param("property_val", 605000.0, float),
    step=1000.0,
    key="property_val"
)
loan = st.number_input(
    "🏠 Property Loan Balance (AUD)",
    min_value=0.0,
    value=get_param("loan", 541735.0, float),
    step=1000.0,
    key="loan"
)
super_balance = st.number_input(
    "💰 Superannuation Balance (AUD)",
    min_value=0.0,
    value=get_param("super_balance", 68000.0, float),
    step=1000.0,
    key="super_balance"
)

# Pre-set share/crypto holdings
holdings_defaults = {
    "INR.AX": get_param("hold_INR.AX", 4854, int),
    "IVV.AX": get_param("hold_IVV.AX", 88, int),
    "VAS.AX": get_param("hold_VAS.AX", 65, int),
    "BABA": get_param("hold_BABA", 9.39, float),
    "XPEV": get_param("hold_XPEV", 58.07, float),
    "AUR": get_param("hold_AUR", 142.20, float),
    "NVDA": get_param("hold_NVDA", 4.88, float),
}
US_TICKERS = ["BABA", "XPEV", "AUR", "NVDA"]
holdings = {}
for sym, default in holdings_defaults.items():
    if sym in US_TICKERS:
        holdings[sym] = st.number_input(
            f"Shares {sym}",
            min_value=0.0,
            value=float(default),
            step=0.01,
            key=f"hold_{sym}"
        )
    else:
        holdings[sym] = st.number_input(
            f"Shares {sym}",
            min_value=0,
            value=int(default),
            step=1,
            key=f"hold_{sym}"
        )

btc_amount = st.number_input(
    "₿ Bitcoin Holding",
    min_value=0.0,
    value=get_param("btc_amount", 0.018302, float),
    step=0.0001,
    key="btc_amount"
)
goal = st.number_input(
    "🎯 Net Worth Goal (AUD)",
    min_value=0.0,
    value=get_param("goal", 1000000.0, float),
    step=1000.0,
    key="goal"
)

st.markdown("---")

# --- Fetch FX and calculate values ---
fx_rate = yf.Ticker("USDAUD=X").history(period="1d", interval="5m")["Close"].iloc[-1]
rows = []
total_value = 0.0
for sym, cnt in holdings.items():
    # fetch price
    if sym in US_TICKERS:
        hist = yf.Ticker(sym).history(period="1d", interval="5m")
        price = hist["Close"].iloc[-1] * fx_rate if not hist.empty else 0.0
    else:
        hist = yf.Ticker(sym).history(period="1d")
        price = hist["Close"].iloc[-1] if not hist.empty else 0.0
    val = cnt * price
    total_value += val
    rows.append({"Ticker": sym, "Shares": cnt, "Price (AUD)": price, "Value (AUD)": val})
# BTC value
btc_hist = yf.Ticker("BTC-USD").history(period="1d", interval="5m")
btc_price = btc_hist["Close"].iloc[-1] * fx_rate if not btc_hist.empty else 0.0
btc_val = btc_amount * btc_price
total_value += btc_val
rows.append({"Ticker": "BTC", "Shares": btc_amount, "Price (AUD)": btc_price, "Value (AUD)": btc_val})

df = pd.DataFrame(rows)

# --- Equity calculations ---
total_equity = property_val - loan
equity_pct = (total_equity / property_val * 100) if property_val else 0
user_pct = 32.0
user_equity = total_equity * (user_pct / 100)
net_worth = cash + user_equity + super_balance + total_value

# --- Auto-save snapshot ---
today = datetime.date.today()
if os.path.exists(HISTORY_FILE):
    hist_df = pd.read_csv(HISTORY_FILE, parse_dates=["Date"])
    last_date = hist_df["Date"].max().date()
else:
    last_date = None
if last_date != today:
    pd.DataFrame([{"Date": today, "Net Worth": net_worth}]).to_csv(
        HISTORY_FILE,
        mode="a",
        index=False,
        header=not os.path.exists(HISTORY_FILE)
    )

# --- Overview Display ---
st.header("📊 Overview")
st.write(f"💵 Cash Balance: ${cash:,.2f}")
st.write(f"🏠 Property Value: ${property_val:,.2f}")
st.write(f"🏠 Loan Balance: ${loan:,.2f}")
st.write(f"Total Equity: ${total_equity:,.2f} ({equity_pct:.1f}% of property)")
st.write(f"Your Equity (32%): ${user_equity:,.2f}")
st.write(f"💰 Super Balance: ${super_balance:,.2f}")
st.write(f"💼 Investments & Crypto Value: ${total_value:,.2f}")
st.write(f"💡 Net Worth: **${net_worth:,.2f}**")
st.progress(net_worth / goal if goal else 0)
st.write(f"{(net_worth / goal * 100) if goal else 0:.1f}% of goal reached")
# show last update timestamp
st.write(f"Last Data Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.dataframe(df.style.format({"Price (AUD)": "${:,.2f}", "Value (AUD)": "${:,.2f}"}))

st.markdown("---")

# --- Forecast ---
st.header("🔮 Forecast")
prop_rate = st.slider("Property Growth %", 0.0, 20.0, get_param("prop_rate", 5.0, float), 0.1, key="prop_rate")
share_rate = st.slider("Investments Growth %", 0.0, 20.0, get_param("share_rate", 7.0, float), 0.1, key="share_rate")
super_rate = st.slider("Super Growth %", 0.0, 20.0, get_param("super_rate", 4.0, float), 0.1, key="super_rate")
years = st.slider("Years to Forecast", 1, 30, get_param("years", 5, int), key="years")

# project values
prop_vals = [property_val]
for _ in range(years): prop_vals.append(prop_vals[-1] * (1 + prop_rate/100))
eq_vals = [(pv - loan) * user_pct/100 for pv in prop_vals]
inv_vals = [total_value]
for _ in range(years): inv_vals.append(inv_vals[-1] * (1 + share_rate/100))
sup_vals = [super_balance]
for _ in range(years): sup_vals.append(sup_vals[-1] * (1 + super_rate/100))
forecast_df = pd.DataFrame({
    "Year": list(range(years+1)),
    "Equity": eq_vals,
    "Investments": inv_vals,
    "Super": sup_vals
})
forecast_df["Total"] = forecast_df.sum(axis=1) + cash
st.line_chart(forecast_df.set_index("Year"))

st.markdown("---")

# --- History Tab (Fortnightly) ---
st.header("🕒 Net Worth History (14-day)")
if os.path.exists(HISTORY_FILE):
    hist_df = pd.read_csv(HISTORY_FILE, parse_dates=["Date"]).set_index("Date").sort_index()
    fortnightly = hist_df["Net Worth"].resample('14D').last().dropna()
    st.line_chart(fortnightly)
    last_snapshot = hist_df.index.max().date()
    st.write(f"Last Snapshot: {last_snapshot}")
else:
    st.info("No history found. The app will auto-save your net worth daily.")
