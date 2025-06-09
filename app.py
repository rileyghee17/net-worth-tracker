import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
import datetime
import json

st.set_page_config(layout="wide")
st.title("My Net-Worth Tracker")

# Navigation tabs: Overview, Forecast, History
tab1, tab2, tab3 = st.tabs(["Overview", "Forecast", "History"])
US_TICKERS = ["BABA", "XPEV", "AUR", "NVDA"]
HISTORY_FILE = "net_worth_history.csv"
SETTINGS_FILE = "user_inputs.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(data: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)


settings = load_settings()

# ===== Overview Tab =====
with tab1:
    # Cash input
    cash = st.number_input(
        "💵 Cash Balance (AUD)",
        min_value=0.0,
        value=float(settings.get("cash", 21081.0)),
        step=100.0,
    )
    st.markdown("---")

    # Investment Property
    st.header("🏠 Investment Property")
    property_val = st.number_input(
        "Market Value (AUD)",
        min_value=0.0,
        value=float(settings.get("property_val", 605000.0)),
        step=1000.0,
    )
    loan = st.number_input(
        "Loan Balance (AUD)",
        min_value=0.0,
        value=float(settings.get("loan", 541735.0)),
        step=1000.0,
    )
    total_equity = property_val - loan
    equity_pct = (total_equity / property_val * 100) if property_val else 0
    user_pct = 32.0
    user_equity = total_equity * (user_pct / 100)
    st.write(f"Total equity: **{equity_pct:.1f}%** (${total_equity:,.2f})")
    st.write(f"Your equity share ({user_pct:.0f}%): **${user_equity:,.2f}**")
    st.markdown("---")

    # Superannuation input
    st.header("💰 Superannuation Balance (AUD)")
    super_balance = st.number_input(
        "Balance",
        min_value=0.0,
        value=float(settings.get("super_balance", 68000.0)),
        step=1000.0,
    )
    st.write(f"Your super balance is ${super_balance:,.2f}")
    st.markdown("---")

    # Investments & Crypto
    st.header("📈 Investments & Crypto")
    tickers = {
        "INR.AX": "Ioneer Ltd",
        "IVV.AX": "iShares S&P 500 ETF (ASX)",
        "VAS.AX": "Vanguard Australian Shares ETF",
        "BABA": "Alibaba Group (US)",
        "XPEV": "XPeng Inc. (US)",
        "AUR": "Aurora Innovation (NASDAQ)",
        "NVDA": "NVIDIA Corp. (US)",
    }
    defaults = {"INR.AX": 4854, "IVV.AX": 88, "VAS.AX": 65, "BABA": 9.39, "XPEV": 58.07, "AUR": 142.20, "NVDA": 4.88}
    holdings = {}
    stored_holdings = settings.get("holdings", {})
    for sym, name in tickers.items():
        is_us = sym in US_TICKERS
        val = stored_holdings.get(sym, defaults[sym])
        if not is_us:
            val = int(val)
        holdings[sym] = st.number_input(
            f"{name} ({sym}) shares",
            min_value=0.0 if is_us else 0,
            value=val,
            step=0.01 if is_us else 1,
            format="%.2f" if is_us else "%d",
            key=f"hold_{sym}"
        )
    btc_amount = st.number_input(
        "₿ Bitcoin Holding",
        min_value=0.0,
        value=float(settings.get("btc_amount", 0.018302)),
        step=0.0001,
        format="%.6f",
    )
    st.markdown("---")

    # Fetch FX and compute values
    fx_rate = yf.Ticker("USDAUD=X").history(period="1d", interval="5m")["Close"].iloc[-1]
    rows, total_value = [], 0.0
    for sym, cnt in holdings.items():
        if sym in US_TICKERS:
            hist = yf.Ticker(sym).history(period="1d", interval="5m")
            price_raw = hist["Close"].iloc[-1] if not hist.empty else 0.0
            price_aud = price_raw * fx_rate
        else:
            price_aud = yf.Ticker(sym).history(period="1d")["Close"].iloc[-1]
        val = cnt * price_aud
        total_value += val
        rows.append({"Ticker":sym, "Shares":cnt, "Price (AUD)":price_aud, "Value (AUD)":val})
    btc_price = yf.Ticker("BTC-USD").history(period="1d", interval="5m")["Close"].iloc[-1]
    btc_val = btc_amount * btc_price * fx_rate
    total_value += btc_val
    rows.append({"Ticker":"BTC","Shares":btc_amount,"Price (AUD)":btc_price*fx_rate,"Value (AUD)":btc_val})

    df = pd.DataFrame(rows)
    net_worth = cash + user_equity + super_balance + total_value
    last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Data last updated: {last_update}")
    st.dataframe(df.style.format({"Price (AUD)":"${:,.2f}","Value (AUD)":"${:,.2f}"}))
    st.write(f"**Total Investments & Crypto Value:** ${total_value:,.2f} AUD")
    st.plotly_chart(px.bar(df, x="Ticker", y="Value (AUD)", title="Value by Holding"))
    st.markdown("---")

    # Net Worth Summary and Goal
    st.header("💡 Current Net Worth")
    st.write(f"**${net_worth:,.2f} AUD**")
    goal = st.number_input(
        "🎯 Net Worth Goal (AUD)",
        min_value=0.0,
        value=float(settings.get("goal", 1000000.0)),
        step=1000.0,
    )
    progress = net_worth/goal if goal else 0
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
        pd.DataFrame([{"Date":today, "Net Worth":net_worth}]).to_csv(
            HISTORY_FILE, mode='a', index=False, header=not os.path.exists(HISTORY_FILE)
        )

# ===== Forecast Tab =====
with tab2:
    st.header("🔮 Net Worth Forecast")
    contrib_freq = st.selectbox(
        "Contribution Frequency",
        ["None", "Weekly", "Monthly", "Yearly"],
        index=["None", "Weekly", "Monthly", "Yearly"].index(settings.get("contrib_freq", "None")),
    )
    contrib_prop = st.number_input(
        "Additional Property Contribution per period (AUD)",
        min_value=0.0,
        value=float(settings.get("contrib_prop", 0.0)),
        step=100.0,
    )
    contrib_invest = st.number_input(
        "Additional Investments & Crypto Contribution per period (AUD)",
        min_value=0.0,
        value=float(settings.get("contrib_invest", 0.0)),
        step=100.0,
    )
    contrib_super = st.number_input(
        "Additional Super Contribution per period (AUD)",
        min_value=0.0,
        value=float(settings.get("contrib_super", 0.0)),
        step=100.0,
    )
    if contrib_freq=="Weekly": freq_mul=52
    elif contrib_freq=="Monthly": freq_mul=12
    elif contrib_freq=="Yearly": freq_mul=1
    else: freq_mul=0
    annual_prop_contrib=contrib_prop*freq_mul
    annual_inv_contrib=contrib_invest*freq_mul
    annual_sup_contrib=contrib_super*freq_mul
    prop_rate=st.slider(
        "Property Annual Growth Rate (%)",
        0.0,
        20.0,
        float(settings.get("prop_rate", 5.0)),
        0.1,
    )
    share_rate=st.slider(
        "Shares & Crypto Annual Growth Rate (%)",
        0.0,
        20.0,
        float(settings.get("share_rate", 7.0)),
        0.1,
    )
    super_rate=st.slider(
        "Superannuation Growth Rate (%)",
        0.0,
        20.0,
        float(settings.get("super_rate", 4.0)),
        0.1,
    )
    years=st.slider(
        "Forecast Horizon (years)",
        1,
        30,
        int(settings.get("years", 5)),
    )
    prop_vals=[property_val]
    for i in range(1,years+1): prop_vals.append(prop_vals[-1]*(1+prop_rate/100)+annual_prop_contrib)
    eq_list=[(pv-loan)*(user_pct/100) for pv in prop_vals]
    inv_list=[total_value]
    sup_list=[super_balance]
    for i in range(1,years+1):
        inv_list.append(inv_list[-1]*(1+share_rate/100)+annual_inv_contrib)
        sup_list.append(sup_list[-1]*(1+super_rate/100)+annual_sup_contrib)
    years_list=list(range(years+1))
    forecast_df=pd.DataFrame({"Year":years_list,"Property Equity (AUD)":eq_list,"Investments & Crypto (AUD)":inv_list,"Superannuation (AUD)":sup_list})
    forecast_df["Total Net Worth (AUD)"]=forecast_df.sum(axis=1)+cash
    st.dataframe(forecast_df.style.format({"Property Equity (AUD)":"${:,.2f}","Investments & Crypto (AUD)":"${:,.2f}","Superannuation (AUD)":"${:,.2f}","Total Net Worth (AUD)":"${:,.2f}"}))
    st.plotly_chart(px.line(forecast_df,x="Year",y=["Property Equity (AUD)","Investments & Crypto (AUD)","Superannuation (AUD)","Total Net Worth (AUD)"],title="Net Worth Projection with Contributions"))

# ===== History Tab =====
with tab3:
    st.header("🕒 Net Worth History")
    if os.path.exists(HISTORY_FILE):
        # Load and prepare historical data
        df_hist = pd.read_csv(HISTORY_FILE, parse_dates=["Date"] )
        df_hist.set_index("Date", inplace=True)
        df_hist.sort_index(inplace=True)
        # Resample to fortnightly (14-day) frequency, taking last snapshot
        fortnightly = df_hist["Net Worth"].resample('14D').last()
        st.line_chart(fortnightly)
    else:
        st.info("No history found. Save a snapshot to populate history.")

# Persist user inputs to disk
save_settings(
    {
        "cash": cash,
        "property_val": property_val,
        "loan": loan,
        "super_balance": super_balance,
        "holdings": holdings,
        "btc_amount": btc_amount,
        "goal": goal,
        "contrib_freq": contrib_freq,
        "contrib_prop": contrib_prop,
        "contrib_invest": contrib_invest,
        "contrib_super": contrib_super,
        "prop_rate": prop_rate,
        "share_rate": share_rate,
        "super_rate": super_rate,
        "years": years,
    }
)
