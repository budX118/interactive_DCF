import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -------------------------
# Infosys FY2025 Base Data (₹ crore, consolidated)
# -------------------------
base_data = {
    "revenue": 162990,
    "cogs": 113347,
    "sgna": 7588 + 7631,   # Selling + G&A
    "rnd": 1296,
    "ebit": 34424,
    "da": 4812,
    "capex": 2237,
    "nwc_change": 3611,
    "tax_expense": 10858,
    "tax_rate": 0.2887,
    "shares_diluted": 4152051184 / 1e7,  # scaled to crore (₹ per share later)
}

# Derived margins
margins = {
    "cogs_pct": base_data["cogs"] / base_data["revenue"],
    "sgna_pct": base_data["sgna"] / base_data["revenue"],
    "rnd_pct": base_data["rnd"] / base_data["revenue"],
    "da_pct": base_data["da"] / base_data["revenue"],
    "capex_pct": base_data["capex"] / base_data["revenue"],
}

# -------------------------
# Streamlit Sidebar Inputs
# -------------------------
st.sidebar.header("Line-item margins (defaults from FY2025)")
cogs_pct = st.sidebar.number_input("COGS % of revenue", value=margins["cogs_pct"], format="%.4f")
sgna_pct = st.sidebar.number_input("SG&A % of revenue", value=margins["sgna_pct"], format="%.4f")
rnd_pct = st.sidebar.number_input("R&D % of revenue", value=margins["rnd_pct"], format="%.4f")
da_pct = st.sidebar.number_input("D&A % of revenue", value=margins["da_pct"], format="%.4f")
capex_pct = st.sidebar.number_input("CapEx % of revenue", value=margins["capex_pct"], format="%.4f")

st.sidebar.header("Working capital & tax")
use_actual_nwc = st.sidebar.checkbox("Use observed ΔNWC FY2025 (₹3,611 Cr)", value=True)
tax_rate = st.sidebar.number_input("Effective tax rate", value=base_data["tax_rate"], format="%.4f")

st.sidebar.header("Discounting / Terminal")
wacc = st.sidebar.slider("WACC (decimal)", 0.06, 0.15, 0.10)
terminal_growth = st.sidebar.slider("Terminal Growth (decimal)", 0.00, 0.05, 0.02)
ebitda_exit_multiple = st.sidebar.slider("EBITDA Exit Multiple (x)", 8.0, 20.0, 12.0)
projection_years = st.sidebar.slider("Projection Years", 3, 10, 5)

growth_rate = st.sidebar.slider("Revenue Growth Rate", 0.04, 0.12, 0.06)

# -------------------------
# Projections
# -------------------------
projections = []
revenue = base_data["revenue"]

for year in range(1, projection_years + 1):
    revenue *= (1 + growth_rate)
    cogs = revenue * cogs_pct
    sgna = revenue * sgna_pct
    rnd = revenue * rnd_pct
    da = revenue * da_pct
    ebitda = revenue - cogs - sgna - rnd
    ebit = ebitda - da
    nopat = ebit * (1 - tax_rate)
    capex = revenue * capex_pct
    nwc = base_data["nwc_change"] if use_actual_nwc else 0
    fcf = nopat + da - capex - nwc
    discount_factor = 1 / ((1 + wacc) ** year)
    pv_fcf = fcf * discount_factor

    projections.append([year, revenue, cogs, sgna, rnd, ebitda, da, ebit, nopat, capex, nwc, fcf, discount_factor, pv_fcf])

df = pd.DataFrame(projections, columns=["Year","Revenue","COGS","SG&A","R&D","EBITDA","D&A","EBIT","NOPAT","CapEx","ΔNWC","FCF","Discount Factor","PV FCF"])

# -------------------------
# Valuation
# -------------------------
pv_fcfs = df["PV FCF"].sum()
terminal_value_gordon = (df.iloc[-1]["FCF"] * (1 + terminal_growth)) / (wacc - terminal_growth)
pv_terminal_gordon = terminal_value_gordon / ((1 + wacc) ** projection_years)

terminal_value_multiple = df.iloc[-1]["EBITDA"] * ebitda_exit_multiple
pv_terminal_multiple = terminal_value_multiple / ((1 + wacc) ** projection_years)

ev_gordon = pv_fcfs + pv_terminal_gordon
ev_multiple = pv_fcfs + pv_terminal_multiple

equity_value_gordon = ev_gordon  # Infosys is net cash (no debt)
equity_value_multiple = ev_multiple

per_share_gordon = (equity_value_gordon * 1e7) / base_data["shares_diluted"]
per_share_multiple = (equity_value_multiple * 1e7) / base_data["shares_diluted"]

# -------------------------
# Output
# -------------------------
st.title("Interactive DCF — Infosys Limited (INFY)")
st.caption("Source: Consolidated FY2024–25 annual report (₹ crore). No assumptions beyond reported line-items.")

st.subheader("Valuation Summary (₹ crore)")

# Full formatting instead of st.metric()
st.write(f"**Enterprise Value (Gordon growth)**: ₹{ev_gordon:,.2f} Cr")
st.write(f"**Enterprise Value (EBITDA multiple)**: ₹{ev_multiple:,.2f} Cr")
st.write(f"**PV of FCFs**: ₹{pv_fcfs:,.2f} Cr")
st.write(f"**PV of Terminal Value (Gordon)**: ₹{pv_terminal_gordon:,.2f} Cr")
st.write(f"**PV of Terminal Value (Multiple)**: ₹{pv_terminal_multiple:,.2f} Cr")
st.write(f"**Equity Value per Share (Gordon)**: ₹{per_share_gordon:,.2f}")
st.write(f"**Equity Value per Share (Multiple)**: ₹{per_share_multiple:,.2f}")

st.subheader("Projection Table (line-item)")
st.dataframe(df.style.format("{:,.2f}"))

# -------------------------
# Sensitivity Plot
# -------------------------
st.subheader("Sensitivity (Interactive)")

wacc_range = np.linspace(0.06, 0.14, 10)
tg_range = np.linspace(0.00, 0.05, 10)

heatmap_data = []
for w in wacc_range:
    row = []
    for g in tg_range:
        tv = (df.iloc[-1]["FCF"] * (1 + g)) / (w - g)
        ev = pv_fcfs + tv / ((1 + w) ** projection_years)
        ps = (ev * 1e7) / base_data["shares_diluted"]
        row.append(ps)
    heatmap_data.append(row)

fig = px.imshow(
    heatmap_data,
    x=[f"{g:.1%}" for g in tg_range],
    y=[f"{w:.1%}" for w in wacc_range],
    color_continuous_scale="BrBG",  # blue-white-green diverging
    aspect="auto",
    labels=dict(x="Terminal Growth", y="WACC", color="₹/share"),
)

st.plotly_chart(fig, use_container_width=True)

