# app.py
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Interactive DCF Model", layout="wide")

st.title("Interactive DCF Valuation Model")

# -------------------------
# Sidebar inputs
# -------------------------
st.sidebar.header("Input Assumptions")

revenue_now = st.sidebar.number_input("Current Revenue ($M)", min_value=10.0, value=500.0, step=10.0)
ebitda_margin = st.sidebar.slider("EBITDA Margin (%)", 0, 80, 30)
growth_rate = st.sidebar.slider("Revenue Growth Rate (YoY %)", 0, 50, 10)
tax_rate = st.sidebar.slider("Tax Rate (%)", 0, 50, 25)
capex_percent = st.sidebar.slider("CapEx (% of Revenue)", 0, 30, 5)
wc_percent = st.sidebar.slider("Change in Working Capital (% of Revenue)", 0, 30, 2)
discount_rate = st.sidebar.slider("Discount Rate (WACC %) ", 1, 20, 10)
terminal_growth = st.sidebar.slider("Terminal Growth Rate (%)", 0, 5, 2)
projection_years = st.sidebar.slider("Projection Years", 3, 10, 5)

# -------------------------
# Build projections
# -------------------------
years = np.arange(1, projection_years + 1)
revenues = [revenue_now * ((1 + growth_rate / 100) ** i) for i in years]
ebitda = [rev * ebitda_margin / 100 for rev in revenues]
ebit = [e * (1 - tax_rate / 100) for e in ebitda]
capex = [rev * capex_percent / 100 for rev in revenues]
wc = [rev * wc_percent / 100 for rev in revenues]

fcf = [ebit[i] - capex[i] - wc[i] for i in range(projection_years)]
discount_factors = [(1 / ((1 + discount_rate / 100) ** yr)) for yr in years]
discounted_fcf = [fcf[i] * discount_factors[i] for i in range(projection_years)]

# Terminal value
terminal_value = fcf[-1] * (1 + terminal_growth / 100) / ((discount_rate / 100) - (terminal_growth / 100))
discounted_terminal = terminal_value * discount_factors[-1]

# Enterprise value
enterprise_value = sum(discounted_fcf) + discounted_terminal

# -------------------------
# Results Display
# -------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("DCF Summary")
    st.metric("Enterprise Value ($M)", f"{enterprise_value:,.0f}")
    st.write("**Breakdown**")
    st.write(f"Present Value of FCFs: ${sum(discounted_fcf):,.0f}M")
    st.write(f"Terminal Value (discounted): ${discounted_terminal:,.0f}M")

with col2:
    st.subheader("Projections Table")
    df = pd.DataFrame({
        "Year": years,
        "Revenue ($M)": revenues,
        "EBITDA ($M)": ebitda,
        "FCF ($M)": fcf,
        "Discounted FCF ($M)": discounted_fcf
    })
    st.dataframe(df.style.format("{:,.0f}"))

# -------------------------
# Chart
# -------------------------
fig = go.Figure()
fig.add_trace(go.Bar(x=years, y=discounted_fcf, name="Discounted FCF"))
fig.add_trace(go.Scatter(x=years, y=fcf, mode="lines+markers", name="FCF (Undiscounted)"))
fig.update_layout(title="Free Cash Flow Projection", xaxis_title="Year", yaxis_title="$M")

st.plotly_chart(fig, use_container_width=True)

st.success("DCF Model Run Complete")
