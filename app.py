from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Stock Market Dashboard - Metrics", layout="wide")
st.title("📊 Stock Market Dashboard")
st.subheader("Iteration 1b: Key Statistics and Metrics")

# ---------- USER INPUT ----------
ticker_symbol = st.text_input("Enter Stock Ticker Symbol", "AAPL").upper().strip()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", date.today() - timedelta(days=365))
with col2:
    end_date = st.date_input("End Date", date.today())

# ---------- INPUT VALIDATION ----------
if start_date > end_date or start_date > date.today() or end_date > date.today():
    st.warning("Please enter a valid date range.")
    st.stop()

# ---------- FETCH & PROCESS DATA ----------

@st.cache_data(ttl=3600)
def get_stock_data(ticker, start, end):
    try:
        df = yf.download(ticker, start=start, end=end, group_by="ticker")

        if df.empty:
            return None

        # ✅ Flatten MultiIndex by joining both levels (e.g., ('Close', 'AAPL') → 'Close_AAPL')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns]

        # ✅ Try to find the 'Close' column dynamically
        close_candidates = [col for col in df.columns if "close" in col.lower()]
        if not close_candidates:
            st.error("No 'Close' column found in the data.")
            return None

        close_col = close_candidates[0]
        df["Close"] = df[close_col]  # Standardize for later access

        # ✅ Add calculated metrics
        df["Daily Return"] = df["Close"].pct_change()
        df["Cumulative Return"] = (1 + df["Daily Return"]).cumprod() - 1
        df["Max Drawdown"] = (df["Close"] / df["Close"].cummax()) - 1

        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

with st.spinner(f"Loading data for {ticker_symbol}..."):
    stock_data = get_stock_data(ticker_symbol, start_date, end_date)

if stock_data is None:
    st.error(f"No data found for {ticker_symbol}. Please try another symbol.")
    st.stop()

# ---------- CHART ----------
st.subheader("📈 Stock Price Over Time")

# Defensive copy
plot_df = stock_data.copy().reset_index()

# Diagnostic output (remove before final submission)
st.write("DataFrame preview:", plot_df.head())
st.write("DataFrame columns:", plot_df.columns.tolist())

# Ensure 'Date' and 'Close' exist
if "Date" not in plot_df.columns:
    # If the first column looks like a date, rename it
    possible_date = plot_df.columns[0]
    if pd.api.types.is_datetime64_any_dtype(plot_df[possible_date]):
        plot_df.rename(columns={possible_date: "Date"}, inplace=True)
    else:
        st.error("No 'Date' column found or inferred.")
        st.stop()

if "Close" not in plot_df.columns:
    # Try to infer from possible multi-named columns
    close_candidates = [col for col in plot_df.columns if "close" in col.lower()]
    if close_candidates:
        plot_df["Close"] = plot_df[close_candidates[0]]
    else:
        st.error("No 'Close' column found in the data.")
        st.stop()

# Final safety check
if plot_df["Close"].dropna().empty:
    st.error("Close column contains only null values.")
    st.stop()

# Plot the chart
fig = px.line(
    plot_df,
    x="Date",
    y="Close",
    title=f"{ticker_symbol} Closing Price",
    labels={"Close": "Price (USD)", "Date": "Date"},
    template="plotly_white",
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Price (USD)",
    hovermode="x unified",
    height=500,
)
fig.update_xaxes(rangeslider_visible=True)
st.plotly_chart(fig, use_container_width=True)
# ---------- METRIC CARDS ----------
st.subheader("📌 Key Performance Metrics")

total_return = stock_data["Cumulative Return"].iloc[-1]
avg_daily_return = stock_data["Daily Return"].mean()
volatility = stock_data["Daily Return"].std()
max_drawdown = stock_data["Max Drawdown"].min()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 Total Return", f"{total_return:.2%}")
col2.metric("🔁 Avg Daily Return", f"{avg_daily_return:.3%}")
col3.metric("📉 Volatility", f"{volatility:.3%}")
col4.metric("⛔ Max Drawdown", f"{max_drawdown:.2%}")

# ---------- DATA TABLE ----------
st.subheader("📅 Historical Data with Daily Returns")

table_df = stock_data[["Close", "Daily Return"]].reset_index()
table_df.rename(columns={"Date": "Date", "Close": "Close Price"}, inplace=True)

def highlight_returns(val):
    if pd.isna(val):
        return ""
    return "color: green" if val > 0 else "color: red"

st.dataframe(
    table_df.style
        .format({"Close Price": "${:.2f}", "Daily Return": "{:.2%}"})
        .applymap(highlight_returns, subset=["Daily Return"]),
    use_container_width=True
)
