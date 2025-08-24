import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------------------------
# Helper function to format numbers
# ---------------------------
def human_format(num):
    if abs(num) >= 1_000_000_000:
        return f"${num/1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"${num/1_000_000:.2f}M"
    elif abs(num) >= 1_000:
        return f"${num/1_000:.2f}K"
    else:
        return f"${num:.2f}"

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="Apple DCF Valuation",
    page_icon="🍎",
    layout="wide"
)

# ---------------------------
# Header with Apple branding
# ---------------------------
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg", width=80)
with col2:
    st.title("Interactive DCF Valuation Model")
    st.subheader("Apple Inc. (NASDAQ: AAPL)")

st.markdown("---")

# ---------------------------
# Sidebar Inputs
# ---------------------------
st.sidebar.header("Assumptions")

revenue_growth = st.sidebar.slider("Revenue Growth Rate (%)", 2, 15, 10)
discount_rate = st.sidebar.slider("Discount Rate (%)", 5, 15, 10)
terminal_growth = st.sidebar.slider("Terminal Growth Rate (%)", 1, 5, 3)
projection_years = st.sidebar.slider("Projection Years", 3, 10, 5)
starting_revenue = st.sidebar.number_input("Starting Revenue ($M)", value=500.0, step=50.0)
fcf_margin = st.sidebar.slider("Free Cash Flow Margin (%)", 5, 40, 20)

# ---------------------------
# DCF Calculation
# ---------------------------
years = np.arange(1, projection_years + 1)
revenues = [starting_revenue * (1 + revenue_growth/100) ** i for i in years]
fcfs = [rev * (fcf_margin/100) for rev in revenues]
discount_factors = [(1 + discount_rate/100) ** i for i in years]
present_values = [fcf / df for fcf, df in zip(fcfs, discount_factors)]

# Terminal Value
terminal_value = (fcfs[-1] * (1 + terminal_growth/100)) / (discount_rate/100 - terminal_growth/100)
pv_terminal = terminal_value / ((1 + discount_rate/100) ** projection_years)

enterprise_value = sum(present_values) + pv_terminal

# ---------------------------
# Valuation Summary
# ---------------------------
st.header("Valuation Summary")

c1, c2, c3 = st.columns(3)
c1.metric("Enterprise Value", human_format(enterprise_value))
c2.metric("PV of FCFs", human_format(sum(present_values)))
c3.metric("Terminal Value (PV)", human_format(pv_terminal))

st.markdown("---")

# ---------------------------
# Projection Table
# ---------------------------
st.header("Projection Table")

df = pd.DataFrame({
    "Year": years,
    "Revenue ($M)": revenues,
    "FCF ($M)": fcfs,
    "Discount Factor": discount_factors,
    "PV of FCF ($M)": present_values
})

df = df.round(2)
st.dataframe(df, use_container_width=True)

# ---------------------------
# Chart
# ---------------------------
st.header("Free Cash Flow Projection")

fig = go.Figure()
fig.add_trace(go.Bar(x=years, y=fcfs, name="Free Cash Flow", marker_color="lightblue"))
fig.add_trace(go.Scatter(x=years, y=present_values, mode="lines+markers", name="PV of FCF", line=dict(color="blue")))

fig.update_layout(
    title="Apple FCF vs. Present Value",
    xaxis_title="Year",
    yaxis_title="Value ($M)",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

