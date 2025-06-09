import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
import datetime

# Page configuration
st.set_page_config(layout="wide")
st.title("My Net-Worth Tracker")

# Utility to handle URL query params
params = st.experimental_get_query_params()
def get_param(key, default, cast_func):
    try:
        return cast_func(params.get(key, [default])[0])
    except:
        return default

# Defaults from URL or hard-coded
cash = get_param("cash", 21081.0, float)
property_val = get_param("property_val", 605000.0, float)
loan = get_param("loan", 541735.0, float)
super_balance = get_param("super_balance", 68000.0, float)

tickers = {
    "INR.AX": 4854,
    "IVV.AX": 88,
    "VAS.AX": 65,
    "BABA": 9.39,
    "XPEV": 58.07,
    "AUR": 142.20,
    "NVDA": 4.88
}
US_TICKERS = ["BABA", "XPEV", "AUR", "NVDA"]
holdings = {}
for sym, default in tickers.items():
    if sym in US_TICKERS:
        holdings[sym] = st.number_input(
            f"Shares {sym}",
            value=get_param(f"hold_{sym}", default, float),
            step=0.01,
            key=f"hold_{sym}"
        )
    else:
        holdings[sym] = st.number_input(
            f"Shares {sym}",
            value=get_param(f"hold_{sym}", default, int),
            step=1,
            key=f"hold_{sym}"
        )
btc_amount = st.number_input(
    "₿ Bitcoin Holding",
    value=get_param("btc_amount", 0.018302, float),
    step=0.0001,
    key="btc_amount"
)
goal = st.number_input(
    "🎯 Net Worth Goal (AUD)",
    value=get_param("goal", 1000000.0, float),
    step=1000.0,
    key="goal"
)

st.markdown("---")
# Calculate values
fx_rate = yf.Ticker("USDAUD=X").history(period="1d", interval="5m")["Close"].iloc[-1]
rows = []
total_value = 0.0
for sym, cnt in holdings.items():
    hist = yf.Ticker(sym).history(period="1d", interval=("5m" if sym in US_TICKERS else None))
    price = hist["Close"].iloc[-1] * fx_rate if sym in US_TICKERS else hist["Close"].iloc[-1]
    val = cnt * price
    total_value += val
    rows.append({"Ticker": sym, "Shares": cnt, "Price (AUD)": price, "Value (AUD)": val})
# BTC value
btc_price = yf.Ticker("BTC-USD").history(period="1d", interval="5m")["Close"].iloc[-1] * fx_rate
btc_val = btc_amount * btc_price
total_value += btc_val
rows.append({"Ticker": "BTC", "Shares": btc_amount, "Price (AUD)": btc_price, "Value (AUD)": btc_val})

df = pd.DataFrame(rows)
# Equity calculations
total_equity = property_val - loan
equity_pct = (total_equity / property_val * 100) if property_val else 0
user_pct = 32.0
user_equity = total_equity * (user_pct / 100)
net_worth = cash + user_equity + super_balance + total_value

# Display overview
st.header("📊 Overview")
st.write(f"💵 Cash: ${cash:,.2f}")
st.write(f"🏠 Property value: ${property_val:,.2f}")
st.write(f"🏠 Loan balance: ${loan:,.2f}")
st.write(f"Total equity: ${total_equity:,.2f} ({equity_pct:.1f}% of property)")
st.write(f"Your equity (32%): ${user_equity:,.2f}")
st.write(f"💰 Super balance: ${super_balance:,.2f}")
st.write(f"💼 Investments & Crypto value: ${total_value:,.2f}")
st.write(f"💡 Net Worth: **${net_worth:,.2f}**")
st.progress(net_worth / goal if goal else 0)
st.write(f"{(net_worth/goal*100) if goal else 0:.1f}% of goal reached")
st.dataframe(df.style.format({"Price (AUD)": "${:,.2f}", "Value (AUD)": "${:,.2f}"}))

st.markdown("---")
# Forecast tab
st.header("🔮 Forecast")
prop_rate = st.slider("Property growth %", 0.0, 20.0, get_param("prop_rate", 5.0, float), 0.1, key="prop_rate")
share_rate = st.slider("Investments growth %", 0.0, 20.0, get_param("share_rate", 7.0, float), 0.1, key="share_rate")
super_rate = st.slider("Super growth %", 0.0, 20.0, get_param("super_rate", 4.0, float), 0.1, key="super_rate")
years = st.slider("Years to forecast", 1, 30, get_param("years", 5, int), key="years")

# Project equity
prop_vals = [property_val]
for i in range(years):
    prop_vals.append(prop_vals[-1] * (1 + prop_rate/100))
eq_vals = [(pv - loan) * user_pct/100 for pv in prop_vals]
inv_vals = [total_value]
for i in range(years): inv_vals.append(inv_vals[-1] * (1 + share_rate/100))
sup_vals = [super_balance]
for i in range(years): sup_vals.append(sup_vals[-1] * (1 + super_rate/100))
forecast_df = pd.DataFrame({
    "Year": list(range(years+1)),
    "Equity": eq_vals,
    "Investments": inv_vals,
    "Super": sup_vals
})
forecast_df["Total"] = forecast_df.sum(axis=1) + cash
st.line_chart(forecast_df.set_index("Year"))

st.markdown("---")
# History tab
st.header("🕒 History (14-day) ")
if os.path.exists(HISTORY_FILE):
    hist = pd.read_csv(HISTORY_FILE, parse_dates=["Date"]).set_index("Date").sort_index()
    fortnightly = hist["Net Worth"].resample('14D').last().dropna()
    st.line_chart(fortnightly)
else:
    st.info("No history found.")
