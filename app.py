import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -------------------------
# Infosys FY2025 Base Data (₹ crore, consolidated)
# -------------------------
default_base_data = {
    "Revenue": 162990.0,
    "COGS": 113347.0,
    "SG&A": 7588.0 + 7631.0,   # Selling + G&A
    "R&D": 1296.0,
    "EBIT": 34424.0,
    "D&A": 4812.0,
    "CapEx": 2237.0,
    "ΔNWC": 3611.0,
    "Tax Expense": 10858.0,
    "Tax Rate": 0.2887,
    "Shares Diluted": 4152051184 / 1e7,  # scaled to crore (₹ per share later)
}

# Session state init
if "base_data" not in st.session_state:
    st.session_state.base_data = default_base_data.copy()

# -------------------------
# Sidebar — Base Data Section
# -------------------------
with st.sidebar.expander("📊 Company Base Data (FY2025, consolidated)", expanded=False):
    st.caption("Defaults are Infosys FY2025 consolidated values — editable if you want to override.")

    if st.button("Reset to Infosys FY2025 defaults"):
        st.session_state.base_data = default_base_data.copy()

    base_data = {}
    for key, val in st.session_state.base_data.items():
        base_data[key] = st.number_input(key, value=float(val), format="%.4f")
    st.session_state.base_data = base_data  # update session state after edits

# Derived margins
margins = {
    "cogs_pct": base_data["COGS"] / base_data["Revenue"],
    "sgna_pct": base_data["SG&A"] / base_data["Revenue"],
    "rnd_pct": base_data["R&D"] / base_data["Revenue"],
    "da_pct": base_data["D&A"] / base_data["Revenue"],
    "capex_pct": base_data["CapEx"] / base_data["Revenue"],
}

# -------------------------
# Sidebar — Line-item Margins Section
# -------------------------
with st.sidebar.expander("⚙️ Line-item Margins (defaults from FY2025)", expanded=False):
    cogs_pct = st.number_input("COGS % of revenue", value=float(margins["cogs_pct"]), format="%.4f")
    sgna_pct = st.number_input("SG&A % of revenue", value=float(margins["sgna_pct"]), format="%.4f")
    rnd_pct = st.number_input("R&D % of revenue", value=float(margins["rnd_pct"]), format="%.4f")
    da_pct = st.number_input("D&A % of revenue", value=float(margins["da_pct"]), format="%.4f")
    capex_pct = st.number_input("CapEx % of revenue", value=float(margins["capex_pct"]), format="%.4f")

# -------------------------
# Sidebar — Working Capital, Tax, Discounting
# -------------------------
st.sidebar.header("Working capital & tax")
use_actual_nwc = st.sidebar.checkbox(f"Use observed ΔNWC FY2025 (₹{int(base_data['ΔNWC']):,} Cr)", value=True)
tax_rate = st.sidebar.number_input("Effective tax rate", value=float(base_data["Tax Rate"]), format="%.4f")

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
revenue = base_data["Revenue"]

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
    nwc = base_data["ΔNWC"] if use_actual_nwc else 0
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

per_share_gordon = (equity_value_gordon * 1e7) / base_data["Shares Diluted"]
per_share_multiple = (equity_value_multiple * 1e7) / base_data["Shares Diluted"]

# -------------------------
# Output
# -------------------------
st.title("Interactive DCF — Infosys Limited (INFY)")
st.caption("Source: Consolidated FY2024–25 annual report (₹ crore). No assumptions beyond reported line-items.")

st.subheader("Valuation Summary (₹ crore)")
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
        ps = (ev * 1e7) / base_data["Shares Diluted"]
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

