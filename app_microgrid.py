import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.optimization import MicrogridOptimizer

st.set_page_config(page_title="Northern Microgrid Planner", layout="wide")
st.title("🔋 Northern Ontario Microgrid Planner")

@st.cache_data
def load_data():
    return pd.read_csv("data/raw/microgrid_data.csv", index_col=0, parse_dates=True)

df_full = load_data()

# --- SIDEBAR ---
st.sidebar.header("💰 Northern Economic Inputs")
bat_cost = st.sidebar.number_input("Battery CAPEX ($/kWh)", 500, 2000, 1000)
solar_cost = st.sidebar.number_input("Solar CAPEX ($/kW)", 2000, 6000, 4000)

fuel_price = st.sidebar.slider("Diesel Price ($/L)", 1.5, 3.5, 2.20)
carbon_tax = st.sidebar.slider("Carbon Tax ($/Ton)", 0, 170, 95)

st.sidebar.subheader("System Sizing")
bat_cap = st.sidebar.slider("Battery (kWh)", 0, 2000, 1000)
solar_cap = st.sidebar.slider("Solar (kW)", 0, 1000, 400)
sim_month = st.sidebar.selectbox("Month", [1, 7], format_func=lambda x: "Jan (Winter)" if x==1 else "Jul (Summer)")

# --- SIMULATION ---
def run_sim():
    df_m = df_full[df_full.index.month == sim_month]
    
    cfg = {
        'fuel_price_per_L': fuel_price,
        'carbon_tax_per_ton': carbon_tax,
        'battery_capacity_kwh': bat_cap,
        'solar_capacity_kw': solar_cap, # PASSED FROM SLIDER
        'diesel_capacity_kw': 500.0,
        'diesel_min_stable_kw': 150.0,
        'diesel_intercept_L_hr': 15.0,
        'diesel_slope_L_kwh': 0.24,
        'battery_power_kw': 250.0,
        'battery_efficiency': 0.95
    }
    
    opt = MicrogridOptimizer(config=cfg)
    with st.spinner("Optimizing Dispatch..."):
        res = opt.build_and_solve(df_m)
    return res, cfg

res, cfg = run_sim()

# --- METRICS ---
# Baseline Cost
base_fuel_L = (len(res)*15.0) + (res['load'].sum()*0.24)
price_total = fuel_price + (0.00268 * carbon_tax)
base_cost = base_fuel_L * price_total * 12 # Extrapolated

# Opt Cost
opt_fuel_L = (res['gen_status'].sum()*15.0) + (res['gen_power'].sum()*0.24)
opt_cost = opt_fuel_L * price_total * 12

capex = (bat_cap * bat_cost) + (solar_cap * solar_cost)
savings = base_cost - opt_cost
payback = capex / savings if savings > 0 else 99

c1, c2, c3, c4 = st.columns(4)
c1.metric("CAPEX", f"${capex:,.0f}")
c2.metric("Annual Savings", f"${savings:,.0f}")
c3.metric("Payback", f"{payback:.1f} Yrs", delta_color="inverse")
c4.metric("Diesel Reduction", f"{(base_fuel_L - opt_fuel_L)*12:.0f} L/Yr")

# --- PLOTS ---
st.subheader(f"Dispatch Strategy (Month {sim_month})")
# Zoom 7 days
zoom = res.iloc[:168]

fig = go.Figure()
fig.add_trace(go.Scatter(x=zoom.index, y=zoom['load'], name="Load", line=dict(color='black', dash='dot')))
fig.add_trace(go.Scatter(x=zoom.index, y=zoom['gen_power'], name="Diesel", stackgroup='1', line=dict(color='#444')))
fig.add_trace(go.Scatter(x=zoom.index, y=zoom['bat_discharge'], name="Battery", stackgroup='1', line=dict(color='green')))
fig.add_trace(go.Scatter(x=zoom.index, y=zoom['solar_used'], name="Solar", stackgroup='1', line=dict(color='orange')))
st.plotly_chart(fig, use_container_width=True)