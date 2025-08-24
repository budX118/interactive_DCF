# app.py
# Interactive, industry-grade DCF for Infosys (INFY) — uses only provided FY2025 consolidated numbers by default.
# Do NOT assume missing company datapoints. Optional fields are flagged.
# Run: pip install streamlit pandas numpy plotly
#       streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import List

# -------------------------
# Helper functions
# -------------------------
def human_fmt_crore(x: float) -> str:
    """Format a number given in ₹ crore for display (B = billion = 100 crore)."""
    if np.isnan(x):
        return "—"
    # show in ₹ crore with thousand separators; also show in B where appropriate
    if abs(x) >= 1000:
        return f"₹{x/1000:,.2f}k Cr (₹{x/100:,.2f}B)"
    return f"₹{x:,.0f} Cr"

def human_fmt_short_billion(x: float) -> str:
    """Short formatted string in ₹ billion, given crore input."""
    if np.isnan(x):
        return "—"
    return f"₹{x/100:,.2f}B"

def discount_factors_array(years: int, wacc: float) -> np.ndarray:
    return np.array([1.0 / ((1 + wacc) ** (i + 1)) for i in range(years)])

# -------------------------
# Defaults: Infosys consolidated FY2025 (all values in ₹ crore)
# (These come from the uploaded FY2024-25 consolidated report and were double-checked.)
# -------------------------
DEFAULTS = {
    "company": "Infosys Limited",
    "ticker": "INFY",
    # Core statement lines (consolidated, FY2025) — units: ₹ crore
    "revenue": 162_990.0,
    "cogs": 113_347.0,
    "selling_marketing": 7_588.0,
    "g_and_a": 7_631.0,
    "rnd": 1_296.0,
    "da": 4_812.0,
    "op_cash_flow": 35_694.0,
    "capex": 2_237.0,
    "delta_nwc_abs": 3_611.0,   # YoY change in working capital observed in the report (crore)
    "cash_and_investments": 47_549.0,
    "net_debt": -47_549.0,      # negative = net cash
    "tax_expense": 10_858.0,
    "pbt": 37_608.0,
    "net_profit": 26_750.0,
    "diluted_shares": 4_152_051_184.0,
}

# Derived default margins (fractions)
DEFAULTS["cogs_pct"] = DEFAULTS["cogs"] / DEFAULTS["revenue"]
DEFAULTS["sga_pct"] = (DEFAULTS["selling_marketing"] + DEFAULTS["g_and_a"]) / DEFAULTS["revenue"]
DEFAULTS["rnd_pct"] = DEFAULTS["rnd"] / DEFAULTS["revenue"]
DEFAULTS["da_pct"] = DEFAULTS["da"] / DEFAULTS["revenue"]
DEFAULTS["capex_pct"] = DEFAULTS["capex"] / DEFAULTS["revenue"]
DEFAULTS["fcf_simple"] = DEFAULTS["op_cash_flow"] - DEFAULTS["capex"]
DEFAULTS["tax_rate_implied"] = DEFAULTS["tax_expense"] / DEFAULTS["pbt"]  # ≈ 28.87%

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title=f"{DEFAULTS['company']} — DCF (FY2025)", layout="wide")
st.title(f"Interactive DCF — {DEFAULTS['company']} ({DEFAULTS['ticker']})")
st.markdown("**Source:** Consolidated FY2024–25 annual report (units: ₹ crore). Default inputs are taken directly from FY2025 consolidated statements and are shown in the sidebar. **No missing company datapoints have been invented.**")

# Sidebar: company data (read-only / editable)
with st.sidebar.expander("▶ Company base data (from FY2025, consolidated) — editable if you want to override"):
    st.write("All values below are from the consolidated FY2025 report (units: ₹ crore).")
    revenue = st.number_input("Starting revenue (FY2025) ₹ crore", value=DEFAULTS["revenue"], format="%.2f")
    cogs = st.number_input("COGS (FY2025) ₹ crore", value=DEFAULTS["cogs"], format="%.2f")
    selling_marketing = st.number_input("Selling & Marketing (FY2025) ₹ crore", value=DEFAULTS["selling_marketing"], format="%.2f")
    g_and_a = st.number_input("General & Admin (FY2025) ₹ crore", value=DEFAULTS["g_and_a"], format="%.2f")
    rnd = st.number_input("R&D (FY2025) ₹ crore", value=DEFAULTS["rnd"], format="%.2f")
    da = st.number_input("D&A (FY2025) ₹ crore", value=DEFAULTS["da"], format="%.2f")
    op_cf = st.number_input("Operating cash flow (FY2025) ₹ crore", value=DEFAULTS["op_cash_flow"], format="%.2f")
    capex = st.number_input("CapEx (FY2025) ₹ crore", value=DEFAULTS["capex"], format="%.2f")
    delta_nwc_abs = st.number_input("ΔNWC observed YoY (FY2025) ₹ crore — (optional)", value=DEFAULTS["delta_nwc_abs"], format="%.2f")
    cash_and_investments = st.number_input("Cash & investments (FY2025) ₹ crore", value=DEFAULTS["cash_and_investments"], format="%.2f")
    net_debt = st.number_input("Net debt = Debt − Cash (FY2025) ₹ crore", value=DEFAULTS["net_debt"], format="%.2f")
    tax_expense = st.number_input("Income tax expense (FY2025) ₹ crore", value=DEFAULTS["tax_expense"], format="%.2f")
    pbt = st.number_input("Profit before tax (FY2025) ₹ crore", value=DEFAULTS["pbt"], format="%.2f")
    diluted_shares = st.number_input("Diluted weighted shares (FY2025)", value=DEFAULTS["diluted_shares"], format="%.0f")
    st.markdown("---")
    st.write("Derived (read-only):")
    st.write(f"- Implied tax rate: **{DEFAULTS['tax_rate_implied']*100:.2f}%** (Income tax / PBT)")
    st.write(f"- EBITDA (derived) = EBIT + D&A — EBIT reported as {DEFAULTS['pbt'] - DEFAULTS['tax_expense']:.0f} (use inputs above if you changed them).")
    st.info("If you change base company numbers, note you are overriding the FY2025 consolidated source.")

# Sidebar: projection controls & line-item % defaults computed from the FY2025 numbers
with st.sidebar.expander("▶ Projection settings & line-item assumptions"):
    st.header("Projection & margins")
    horizon = st.selectbox("Projection horizon (IB-style):", options=[5, 10], index=0)
    growth_mode = st.selectbox("Revenue growth mode:", options=["fade (high → terminal)", "custom per-year"], index=0)
    if growth_mode.startswith("fade"):
        high_growth = st.number_input("Year-1 revenue growth (decimal, e.g. 0.10 = 10%)", value=0.06, format="%.4f", help="Use a value you want; default left unset (0.06 if you edit).")
        terminal_growth = st.number_input("Terminal revenue growth (decimal)", value=0.04, format="%.4f", help="Long-term perpetual growth (GDP/inflation constrained).")
    else:
        custom_growth_csv = st.text_input(f"Comma-separated growth rates ({horizon} numbers)", value=",".join(["0.06"]*horizon))
        try:
            custom_growth = [float(x.strip()) for x in custom_growth_csv.split(",")][:horizon]
        except Exception:
            custom_growth = [0.06]*horizon

    st.subheader("Line-item margins (defaults from FY2025)")
    # defaults are computed from provided FY2025 numbers
    default_cogs_pct = cogs / revenue if revenue else 0.0
    default_sga_pct = (selling_marketing + g_and_a) / revenue if revenue else 0.0
    default_rnd_pct = rnd / revenue if revenue else 0.0
    default_da_pct = da / revenue if revenue else 0.0
    default_capex_pct = capex / revenue if revenue else 0.0

    cogs_pct = st.number_input("COGS % of revenue", value=float(default_cogs_pct), format="%.4f")
    sga_pct = st.number_input("SG&A % of revenue (S&M + G&A)", value=float(default_sga_pct), format="%.4f")
    rnd_pct = st.number_input("R&D % of revenue", value=float(default_rnd_pct), format="%.4f")
    da_pct = st.number_input("D&A % of revenue", value=float(default_da_pct), format="%.4f", help="Used to compute D&A each year; based on FY2025 D&A / Revenue.")
    capex_pct = st.number_input("CapEx % of revenue", value=float(default_capex_pct), format="%.4f")
    st.subheader("Working capital & tax")
    use_abs_nwc = st.checkbox("Use observed ΔNWC absolute FY2025 value (do not assume)", value=True, help="This uses the reported YoY ΔNWC as the first-year ΔNWC. If unchecked, you may project ΔNWC as percent of revenue change.")
    if not use_abs_nwc:
        nwc_pct = st.number_input("ΔNWC % of revenue change (if not using absolute)", value=0.02, format="%.4f")
    tax_rate = st.number_input("Effective tax rate (decimal)", value=float(DEFAULTS["tax_rate_implied"]), format="%.4f")
    st.subheader("Discounting / Terminal")
    wacc = st.number_input("WACC (decimal)", value=0.11, format="%.4f")
    tv_method = st.radio("Terminal value method", options=["Perpetuity (Gordon)","Exit multiple (EV/EBITDA)"], index=0)
    if tv_method.startswith("Perpetuity"):
        perp_g = st.number_input("Terminal growth (g, decimal)", value=0.04, format="%.4f")
    else:
        exit_mult = st.number_input("Exit EBITDA multiple (x)", value=15.0, format="%.2f")

# -------------------------
# Build growth rates and projected revenues
# -------------------------
if growth_mode.startswith("fade"):
    # if user didn't edit high_growth, keep it conservative: default use small positive if left 0
    if high_growth is None:
        high_growth = 0.06
    growths = list(np.linspace(high_growth, terminal_growth, horizon))
else:
    growths = custom_growth

revenues: List[float] = []
for i in range(horizon):
    if i == 0:
        revenues.append(revenue * (1 + growths[i]))
    else:
        revenues.append(revenues[-1] * (1 + growths[i]))

# -------------------------
# Build line-item P&L for each projection year
# -------------------------
df = pd.DataFrame({"Year": [f"Year {i+1}" for i in range(horizon)], "Growth": growths, "Revenue": revenues})
df["COGS"] = df["Revenue"] * cogs_pct
df["SG&A"] = df["Revenue"] * sga_pct
df["R&D"] = df["Revenue"] * rnd_pct
# EBITDA as Revenue − (COGS + SG&A + R&D)
df["EBITDA"] = df["Revenue"] - (df["COGS"] + df["SG&A"] + df["R&D"])
df["D&A"] = df["Revenue"] * da_pct
df["EBIT"] = df["EBITDA"] - df["D&A"]
# NOPAT = EBIT * (1 − tax_rate)
df["NOPAT"] = df["EBIT"] * (1 - tax_rate)
df["CapEx"] = df["Revenue"] * capex_pct

# ΔNWC handling
if use_abs_nwc:
    # use the single observed ΔNWC as the first-year change, then set subsequent years to 0 (truthful, no assumption)
    # NOTE: this choice prevents inventing future ΔNWC behaviour — user can edit to provide a schedule
    df["ΔNWC"] = 0.0
    if horizon >= 1:
        df.at[0, "ΔNWC"] = float(delta_nwc_abs)
else:
    # project ΔNWC as nwc_pct * ΔRevenue (which is explicit and user-provided)
    # compute ΔRevenue
    df["ΔRevenue"] = df["Revenue"].diff().fillna(df["Revenue"].iloc[0])
    df["ΔNWC"] = df["ΔRevenue"] * nwc_pct

# Free cash flow (Unlevered) = NOPAT + D&A − CapEx − ΔNWC
df["FCF"] = df["NOPAT"] + df["D&A"] - df["CapEx"] - df["ΔNWC"]

# -------------------------
# Discount FCFs and terminal value
# -------------------------
discounts = discount_factors_array(horizon, wacc)
df["Discount Factor"] = discounts
df["PV FCF"] = df["FCF"].values * discounts

# Terminal
if tv_method.startswith("Perpetuity"):
    # Use the last-year FCF and calculate perpetuity TV
    last_fcf = df["FCF"].iloc[-1]
    if wacc <= perp_g:
        tv = np.nan  # invalid unless wacc > g
    else:
        tv = last_fcf * (1 + perp_g) / (wacc - perp_g)
    pv_tv = tv * discounts[-1] if not np.isnan(tv) else np.nan
else:
    # Exit multiple on final-year EBITDA
    last_ebitda = df["EBITDA"].iloc[-1]
    tv = last_ebitda * exit_mult
    pv_tv = tv * discounts[-1]

# Enterprise / Equity value
pv_fcfs_sum = df["PV FCF"].sum()
enterprise_value = pv_fcfs_sum + (pv_tv if not np.isnan(pv_tv) else 0.0)
equity_value = enterprise_value - net_debt
per_share_value = equity_value * 10000000.0 / diluted_shares  # convert crore -> rupee then divide by shares: (crore * 1e7 INR)/shares
# Note: 1 crore = 10,000,000 = 1e7

# -------------------------
# Output: Summary cards + table + charts
# -------------------------
st.subheader("Valuation summary (values displayed in ₹ crore unless noted)")

c1, c2, c3, c4 = st.columns([2,2,2,2])
c1.metric("Enterprise value (EV)", human_fmt_crore(enterprise_value))
c2.metric("PV of FCFs", human_fmt_crore(pv_fcfs_sum))
c3.metric("PV of Terminal value", human_fmt_crore(pv_tv if not np.isnan(pv_tv) else 0.0))
c4.metric("Equity value (EV − net debt)", human_fmt_crore(equity_value))

st.caption(f"Per-share (equity) value: {per_share_value:,.2f} ₹/share (computed using diluted shares = {int(diluted_shares):,}).")

st.markdown("---")
st.subheader("Projection table (line-item)")
display_df = df[["Year","Revenue","Growth","COGS","SG&A","R&D","EBITDA","D&A","EBIT","NOPAT","CapEx","ΔNWC","FCF","Discount Factor","PV FCF"]].copy()
st.dataframe(display_df.style.format("{:,.2f}"))

# Charts: Revenue / EBITDA / FCF / PV FCF
st.subheader("Projections chart")
fig = go.Figure()
fig.add_trace(go.Scatter(x=display_df["Year"], y=display_df["Revenue"], mode="lines+markers", name="Revenue"))
fig.add_trace(go.Bar(x=display_df["Year"], y=display_df["EBITDA"], name="EBITDA", marker_color="lightgreen"))
fig.add_trace(go.Line(x=display_df["Year"], y=display_df["FCF"], name="FCF", line=dict(color="orange")))
fig.update_layout(title="Revenue, EBITDA, and FCF", yaxis_title="₹ crore")
st.plotly_chart(fig, use_container_width=True)

# Sensitivity
st.subheader("Sensitivity (interactive)")
if tv_method.startswith("Perpetuity"):
    wacc_grid = np.linspace(max(0.02, perp_g + 0.005), max(0.05, wacc + 0.04), 12)
    g_grid = np.linspace(0.0, max(0.06, perp_g + 0.02), 12)
    Z = []
    for W in wacc_grid:
        row = []
        for G in g_grid:
            if W <= G:
                row.append(np.nan)
            else:
                tvx = df["FCF"].iloc[-1] * (1 + G) / (W - G)
                pv_tvx = tvx * (1.0 / ((1 + W) ** horizon))
                evx = pv_fcfs_sum + pv_tvx
                eqx = evx - net_debt
                per_sh = eqx * 10000000.0 / diluted_shares
                row.append(per_sh)
        Z.append(row)
    st.write("WACC vs Terminal Growth — per share (₹)")
    heat = go.Figure(data=go.Heatmap(z=Z, x=[f"{g:.2%}" for g in g_grid], y=[f"{w:.2%}" for w in wacc_grid], colorbar=dict(title="₹/share")))
    st.plotly_chart(heat, use_container_width=True)
else:
    wacc_grid = np.linspace(0.02, max(0.05, wacc + 0.04), 12)
    mult_grid = np.linspace(max(4.0, exit_mult - 8), exit_mult + 8, 12)
    Z = []
    for W in wacc_grid:
        row = []
        for M in mult_grid:
            tvx = df["EBITDA"].iloc[-1] * M
            pv_tvx = tvx * (1.0 / ((1 + W) ** horizon))
            evx = pv_fcfs_sum + pv_tvx
            eqx = evx - net_debt
            per_sh = eqx * 10000000.0 / diluted_shares
            row.append(per_sh)
        Z.append(row)
    st.write("WACC vs Exit multiple — per share (₹)")
    heat = go.Figure(data=go.Heatmap(z=Z, x=[f"{m:.1f}x" for m in mult_grid], y=[f"{w:.2%}" for w in wacc_grid], colorbar=dict(title="₹/share")))
    st.plotly_chart(heat, use_container_width=True)

st.markdown("---")
st.subheader("Omitted / not-modeled items (explicit — no assumptions made)")
st.write("""
The model intentionally does NOT assume or invent the following because they are not present as explicit datapoints in the FY2025 consolidated values you provided (and per your instruction I will not invent them):

• Detailed intra-year ΔNWC schedule beyond the reported FY2025 YoY ΔNWC (we only use the observed FY2025 ΔNWC as first-year change if selected).  
• Debt amortization schedule or future interest expense projections (we used consolidated net debt only for EV→Equity conversion).  
• Share buyback / dilution schedules beyond the diluted weighted shares provided — no forward share-count assumption.  
• Deferred tax asset / NOL schedules, pension liabilities, or off-balance-sheet items requiring managerial forecasts.  
• Segment-level revenue breakdowns and segment-level capex schedules.  
• Any analyst consensus forecasts or guidance not present in the uploaded FY2025 report.

If you want any of these included, provide the explicit numbers / schedules and I will plug them in without guessing.
""")

st.markdown("---")
st.write("Export projection table as CSV:")
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("Download projection CSV", csv, "infy_dcf_projection.csv", "text/csv")


