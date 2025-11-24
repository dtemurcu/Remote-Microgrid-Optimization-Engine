import pandas as pd
import logging
import matplotlib.pyplot as plt
from src.optimization import MicrogridOptimizer
from tqdm import tqdm
import os
import sys

# Configure Logging to print clearly to console
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("\n=== STARTING DEBUG RUN ===")
    
    # 1. CHECK DATA FILE
    file_path = "data/raw/microgrid_data.csv"
    if not os.path.exists(file_path):
        print(f"CRITICAL ERROR: File not found at {file_path}")
        print("Did you run 'py run_microgrid.py'?")
        return

    print(f"Loading data from {file_path}...")
    df_full = pd.read_csv(file_path, index_col=0, parse_dates=True)
    print(f"Data loaded. Shape: {df_full.shape}")

    # 2. CONFIGURATION
    print("Configuring parameters...")
    cfg = {
        'fuel_price_per_L': 2.20,
        'carbon_tax_per_ton': 95.0,
        'diesel_capacity_kw': 500.0,
        'diesel_min_stable_kw': 150.0,
        'diesel_intercept_L_hr': 15.0,
        'diesel_slope_L_kwh': 0.24,
        'battery_capacity_kwh': 1000.0,
        'battery_power_kw': 250.0,
        'battery_efficiency': 0.95,
        'solar_capacity_kw': 400.0
    }

    # 3. BASELINE CALCULATION
    price_total = cfg['fuel_price_per_L'] + (0.00268 * cfg['carbon_tax_per_ton'])
    hours = len(df_full)
    energy = df_full['load_kw'].sum()
    
    base_fuel = (hours * cfg['diesel_intercept_L_hr']) + (energy * cfg['diesel_slope_L_kwh'])
    base_cost = base_fuel * price_total
    print(f"Baseline Calculation Complete. Annual Cost: ${base_cost:,.0f}")

    # 4. OPTIMIZATION LOOP
    print("Initializing Optimization Engine...")
    opt = MicrogridOptimizer(config=cfg)
    
    annual_res = []
    months = df_full.index.month.unique()
    print(f"Starting Optimization for {len(months)} months...")

    # REMOVED TRY/EXCEPT -> Let it crash if it fails!
    for m in tqdm(months, desc="Optimizing"):
        df_month = df_full[df_full.index.month == m]
        if df_month.empty: continue
        
        # This is where it likely failed before. Now we will see why.
        res = opt.build_and_solve(df_month)
        annual_res.append(res)
    
    print("Optimization Complete. Consolidating results...")
    df_opt = pd.concat(annual_res)
    
    # 5. RESULTS
    opt_fuel = (df_opt['gen_status'].sum() * cfg['diesel_intercept_L_hr']) + \
               (df_opt['gen_power'].sum() * cfg['diesel_slope_L_kwh'])
    opt_cost = opt_fuel * price_total
    
    savings = base_cost - opt_cost
    
    # Print Final Report
    print("\n" + "="*40)
    print("NORTHERN ONTARIO FEASIBILITY RESULTS")
    print("="*40)
    print(f"Baseline Cost:  ${base_cost:,.0f}")
    print(f"Optimized Cost: ${opt_cost:,.0f}")
    print(f"Savings:        ${savings:,.0f} ({savings/base_cost:.1%})")
    print("="*40 + "\n")
    
    # 6. VISUALIZATION
    print("Generating plots...")
    os.makedirs("outputs/figures", exist_ok=True)
    
    df_opt['month'] = df_opt.index.month
    df_full['month'] = df_full.index.month
    
    # Monthly Grouping
    monthly_opt_fuel = (df_opt.groupby('month')['gen_status'].sum() * cfg['diesel_intercept_L_hr']) + \
                       (df_opt.groupby('month')['gen_power'].sum() * cfg['diesel_slope_L_kwh'])
    monthly_opt_cost = monthly_opt_fuel * price_total
    
    hours_per_month = df_full.groupby('month')['load_kw'].count()
    load_per_month = df_full.groupby('month')['load_kw'].sum()
    monthly_base_fuel = (hours_per_month * cfg['diesel_intercept_L_hr']) + (load_per_month * cfg['diesel_slope_L_kwh'])
    monthly_base_cost = monthly_base_fuel * price_total
    
    plt.figure(figsize=(10, 6))
    width = 0.35
    x = list(range(1, 13))
    
    plt.bar([p - width/2 for p in x], monthly_base_cost, width, label='Diesel Baseline', color='gray')
    plt.bar([p + width/2 for p in x], monthly_opt_cost, width, label='Hybrid Microgrid', color='green')
    
    plt.xlabel("Month")
    plt.ylabel("Cost ($)")
    plt.title(f"Annual Savings: ${savings/1000:.0f}k")
    plt.xticks(x, ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    output_path = "outputs/figures/02_annual_savings.png"
    plt.savefig(output_path)
    print(f"Plot saved to {output_path}")
    print("DONE.")

if __name__ == "__main__":
    main()