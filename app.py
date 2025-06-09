import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
import datetime

# Page config
st.set_page_config(layout="wide")
st.title("My Net-Worth Tracker")

# --- Persist inputs via URL query parameters ---
# Use new API st.query_params
params = st.query_params

def get_param_float(key, default):
    try:
        return float(params.get(key, [default])[0])
    except:
        return default

def get_param_int(key, default):
    try:
        return int(params.get(key, [default])[0])
    except:
        return default

def get_param_str(key, default):
    return params.get(key, [default])[0]

# Load persisted defaults
cash_default = get_param_float("cash", 21081.0)
property_val_default = get_param_float("property_val", 605000.0)
loan_default = get_param_float("loan", 541735.0)
super_default = get_param_float("super_balance", 68000.0)

ticker_defaults = {
    "INR.AX": 4854,
    "IVV.AX": 88,
    "VAS.AX": 65,
    "BABA": 9.39,
    "XPEV": 58.07,
    "AUR": 142.20,
    "NVDA": 4.88
}
US_TICKERS = ["BABA", "XPEV", "AUR", "NVDA"]

# Use ints for ASX holdings and floats for US
holdings_default = {
    sym: (
        get_param_float(f"hold_{sym}", ticker_defaults[sym]) if sym in US_TICKERS
        else get_param_int(f"hold_{sym}", ticker_defaults[sym])
    )
    for sym in ticker_defaults
}

btc_default = get_param_float("btc_amount", 0.018302)
goal_default = get_param_float("goal", 1000000.0)

# Forecast defaults
contrib_freq_default = get_param_str("contrib_freq", "None")
contrib_prop_default = get_param_float("contrib_prop", 0.0)
contrib_inv_default = get_param_float("contrib_invest", 0.0)
contrib_sup_default = get_param_float("contrib_super", 0.0)
prop_rate_default = get_param_float("prop_rate", 5.0)
share_rate_default = get_param_float("share_rate", 7.0)
super_rate_default = get_param_float("super_rate", 4.0)
years_default = get_param_int("years", 5)

HISTORY_FILE = "net_worth_history.csv"

# Tabs
tab1, tab2, tab3 = st.tabs(["Overview", "Forecast", "History"])

# ===== Overview Tab =====
with tab1:
    cash = st.number_input("💵 Cash Balance (AUD)", min_value=0.0, value=cash_default, step=100.0, key="cash")
    property_val = st.number_input("🏠 Property Market Value (AUD)", 0.0, property_val_default, 1000.0, key="property_val")
    loan = st.number_input("🏠 Property Loan Balance (AUD)", 0.0, loan_default, 1000.0, key="loan")
    total_equity = property_val - loan
    equity_pct = (total_equity / property_val * 100) if property_val else 0
    user_pct = 32.0
    user_equity = total_equity * (user_pct / 100)
    super_balance = st.number_input("💰 Superannuation Balance (AUD)", 0.0, super_default, 1000.0, key="super_balance")

    st.markdown("---")
    # Share & Crypto inputs
    holdings = {}
    for sym in ticker_defaults:
        default = holdings_default[sym]
        if sym in US_TICKERS:
            holdings[sym] = st.number_input(f"Shares {sym}", 0.0, default, 0.01, key=f"hold_{sym}")
        else:
            holdings[sym] = st.number_input(f"Shares {sym}", 0, default, 1, key=f"hold_{sym}")
    btc_amount = st.number_input("₿ Bitcoin Holding", 0.0, btc_default, 0.0001, key="btc_amount")
    goal = st.number_input("🎯 Net Worth Goal (AUD)", 0.0, goal_default, 1000.0, key="goal")

    # Fetch prices & compute values
    fx_rate = yf.Ticker("USDAUD=X").history(period="1d", interval="5m")["Close"].iloc[-1]
    rows, total_value = [], 0.0
    for sym, cnt in holdings.items():
        if sym in US_TICKERS:
            price_raw = yf.Ticker(sym).history(period="1d", interval="5m")["Close"].iloc[-1]
            price = price_raw * fx_rate
        else:
            price = yf.Ticker(sym).history(period="1d")["Close"].iloc[-1]
        val = cnt * price
        total_value += val
        rows.append({"Ticker": sym, "Shares": cnt, "Price (AUD)": price, "Value (AUD)": val})
    btc_price = yf.Ticker("BTC-USD").history(period="1d", interval="5m")["Close"].iloc[-1] * fx_rate
    btc_val = btc_amount * btc_price
    total_value += btc_val
    rows.append({"Ticker": "BTC", "Shares": btc_amount, "Price (AUD)": btc_price, "Value (AUD)": btc_val})

    df = pd.DataFrame(rows)
    net_worth = cash + user_equity + super_balance + total_value

    # Display
    last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Data last updated: {last_update}")
    st.dataframe(df.style.format({"Price (AUD)": "${:,.2f}", "Value (AUD)": "${:,.2f}"}))
    st.write(f"**Total Investments & Crypto Value:** ${total_value:,.2f} AUD")
    st.plotly_chart(px.bar(df, x="Ticker", y="Value (AUD)", title="Value by Holding"))
    st.markdown("---")
    st.header("💡 Current Net Worth")
    st.write(f"**${net_worth:,.2f} AUD**")
    progress = net_worth / goal if goal else 0
    st.progress(progress)
    st.write(f"{progress*100:.1f}% of goal reached")

    # Auto-save snapshot
    today = datetime.date.today()
    if os.path.exists(HISTORY_FILE):
        hist = pd.read_csv(HISTORY_FILE, parse_dates=["Date"])
        last = hist["Date"].max().date()
    else:
        last = None
    if last != today:
        pd.DataFrame([{"Date": today, "Net Worth": net_worth}]).to_csv(
            HISTORY_FILE, mode='a', index=False, header=not os.path.exists(HISTORY_FILE)
        )

    # Persist inputs in URL
    st.experimental_set_query_params(
        cash=cash,
        property_val=property_val,
        loan=loan,
        super_balance=super_balance,
        **{f"hold_{sym}": holdings[sym] for sym in holdings},
        btc_amount=btc_amount,
        goal=goal,
        contrib_freq=contrib_freq_default,
        contrib_prop=contrib_prop_default,
        contrib_invest=contrib_inv_default,
        contrib_super=contrib_sup_default,
        prop_rate=prop_rate_default,
        share_rate=share_rate_default,
        super_rate=super_rate_default,
        years=years_default
    )

# ===== Forecast Tab =====
with tab2:
    st.header("🔮 Net Worth Forecast")
    contrib_freq = st.selectbox("Contribution Frequency", ["None", "Weekly", "Monthly", "Yearly"], index=["None", "Weekly", "Monthly", "Yearly"].index(contrib_freq_default), key="contrib_freq")
    contrib_prop = st.number_input("Additional Property Contribution per period (AUD)", 0.0, contrib_prop_default, 100.0, key="contrib_prop")
    contrib_invest = st.number_input("Additional Investments & Crypto Contribution per period (AUD)", 0.0, contrib_inv_default, 100.0, key="contrib_invest")
    contrib_super = st.number_input("Additional Super Contribution per period (AUD)", 0.0, contrib_sup_default, 100.0, key="contrib_super")
    if contrib_freq == "Weekly": freq_mul = 52
    elif contrib_freq == "Monthly": freq_mul = 12
    elif contrib_freq == "Yearly": freq_mul = 1
    else: freq_mul = 0
    annual_prop_contrib = contrib_prop * freq_mul
    annual_inv_contrib = contrib_invest * freq_mul
    annual_sup_contrib = contrib_super * freq_mul

    prop_rate = st.slider("Property Annual Growth Rate (%)", 0.0, 20.0, prop_rate_default, 0.1, key="prop_rate")
    share_rate = st.slider("Shares & Crypto Annual Growth Rate (%)", 0.0, 20.0, share_rate_default, 0.1, key="share_rate")
    super_rate = st.slider("Superannuation Growth Rate (%)", 0.0, 20.0, super_rate_default, 0.1, key="super_rate")
    years = st.slider("Forecast Horizon (years)", 1, 30, years_default, key="years")

    # Projections with contributions
    prop_vals = [property_val]
    for i in range(1, years + 1):
        prop_vals.append(prop_vals[-1] * (1 + prop_rate / 100) + annual_prop_contrib)
    eq_list = [(pv - loan) * (user_pct / 100) for pv in prop_vals]

    inv_list = [total_value]
    sup_list = [super_balance]
    for i in range(1, years + 1):
        inv_list.append(inv_list[-1] * (1 + share_rate / 100) + annual_inv_contrib)
        sup_list.append(sup_list[-1] * (1 + super_rate / 100) + annual_sup_contrib)

    forecast_df = pd.DataFrame({
        "Year": list(range(years + 1)),
        "Property Equity (AUD)": eq_list,
        "Investments & Crypto (AUD)": inv_list,
        "Superannuation (AUD)": sup_list
    })
    forecast_df["Total Net Worth (AUD)"] = forecast_df.sum(axis=1) + cash
    st.dataframe(forecast_df.style.format({
        "Property Equity (AUD)": "${:,.2f}",
        "Investments & Crypto (AUD)": "${:,.2f}",
        "Superannuation (AUD)": "${:,.2f}",
        "Total Net Worth (AUD)": "${:,.2f}"
    }))
    st.plotly_chart(px.line(
        forecast_df,
        x="Year",
        y=["Property Equity (AUD)", "Investments & Crypto (AUD)", "Superannuation (AUD)", "Total Net Worth (AUD)"],
        title="Net Worth Projection with Contributions"
    ))

# ===== History Tab =====
with tab3:
    st.header("🕒 Net Worth History (Fortnightly)")
    if os.path.exists(HISTORY_FILE):
        df_hist = pd.read_csv(HISTORY_FILE, parse_dates=["Date"])
        df_hist.set_index("Date", inplace=True)
        df_hist.sort_index(inplace=True)
        fortnightly = df_hist["Net Worth"].resample('14D').last().dropna()
        st.line_chart(fortni
