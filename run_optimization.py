import pandas as pd
import matplotlib.pyplot as plt
import os
import logging
from src.optimization import MicrogridOptimizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    # 1. Load Data
    try:
        df_full = pd.read_csv("data/raw/microgrid_data.csv", index_col=0, parse_dates=True)
    except FileNotFoundError:
        logging.error("Run 'run_microgrid.py' first!")
        return

    # 2. Select a Window: SUMMER (July 4th - July 6th)
    # We choose Summer because it shows the Battery logic best (Solar > Load)
    start_time = "2024-07-04 00:00:00"
    end_time = "2024-07-06 00:00:00"
    
    # Ensure data exists (handle potential 2023 vs 2024 issues in synthetic data)
    # If 2024 dates don't exist, fallback to first 48 hours
    if start_time not in df_full.index:
        logging.warning("Selected date range not found. Using first 48 hours.")
        df_horizon = df_full.iloc[:48]
    else:
        df_horizon = df_full.loc[start_time:end_time]
    
    logging.info(f"Optimizing window: {df_horizon.index[0]} to {df_horizon.index[-1]}")
    
    # 3. Optimize
    opt = MicrogridOptimizer()
    res = opt.build_and_solve(df_horizon)
    
    # 4. Financials
    total_diesel = res['gen_power'].sum()
    total_fuel = total_diesel * 0.30
    total_cost = total_fuel * 2.50
    logging.info(f"Optimization Results:")
    logging.info(f"  Diesel Energy: {total_diesel:.1f} kWh")
    logging.info(f"  Fuel Burned:   {total_fuel:.1f} L")
    logging.info(f"  Total Cost:    ${total_cost:.2f}")

    # 5. Visualize
    os.makedirs("outputs/figures", exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # A. Dispatch Stack
    ax1.set_title("Optimal Dispatch: Summer (High Solar)")
    ax1.stackplot(res.index, 
                  res['gen_power'], res['bat_dis'], res['solar_used'],
                  labels=['Diesel', 'Battery Disch', 'Solar'],
                  colors=['#333333', '#2ca02c', '#ff7f0e'], alpha=0.8)
    ax1.plot(res.index, res['load'], color='red', linestyle='--', linewidth=2, label='Load')
    ax1.legend(loc='upper right')
    ax1.set_ylabel("Power (kW)")
    
    # B. SOC
    ax2.set_title("Battery State of Charge")
    ax2.plot(res.index, res['bat_soc'], color='purple', linewidth=2, label='SOC (kWh)')
    ax2.axhline(1000, color='gray', linestyle=':')
    ax2.set_ylabel("Energy (kWh)")
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig("outputs/figures/01_optimization_result.png")
    logging.info("Saved plot: outputs/figures/01_optimization_result.png")

if __name__ == "__main__":
    main()