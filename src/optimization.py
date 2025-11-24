import pyomo.environ as pyo
import pandas as pd
import numpy as np
import logging

class MicrogridOptimizer:
    def __init__(self, config=None):
        # Defaults updated to Northern Ontario Economics
        self.config = config or {
            'diesel_capacity_kw': 500.0,
            'diesel_min_stable_kw': 150.0,
            'diesel_intercept_L_hr': 15.0,
            'diesel_slope_L_kwh': 0.24,
            'fuel_price_per_L': 2.20,       # Northern Price
            'carbon_tax_per_ton': 95.0,     # 2025 Price
            'battery_capacity_kwh': 1000.0,
            'battery_power_kw': 250.0,
            'battery_efficiency': 0.95,
            'solar_capacity_kw': 400.0
        }
        
    def build_and_solve(self, df_horizon):
        model = pyo.ConcreteModel()
        T = len(df_horizon)
        model.T = pyo.RangeSet(0, T-1)
        
        # PARAMETERS
        solar_cap = self.config.get('solar_capacity_kw', 400.0)
        available_solar = df_horizon['solar_pu'].values * solar_cap
        load_demand = df_horizon['load_kw'].values
        
        # VARIABLES
        model.gen_status = pyo.Var(model.T, domain=pyo.Binary)
        model.gen_power = pyo.Var(model.T, domain=pyo.NonNegativeReals)
        model.bat_charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
        model.bat_discharge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
        model.bat_soc = pyo.Var(model.T, domain=pyo.NonNegativeReals)
        model.solar_curtailed = pyo.Var(model.T, domain=pyo.NonNegativeReals)
        
        # CONSTRAINTS
        
        # 1. Energy Balance (Single Equality)
        def energy_balance(m, t):
            return (m.gen_power[t] + m.bat_discharge[t] + (available_solar[t] - m.solar_curtailed[t]) 
                    == load_demand[t] + m.bat_charge[t])
        model.EnergyBalance = pyo.Constraint(model.T, rule=energy_balance)
        
        # 2. Generator Limits (SPLIT - NO TUPLES ALLOWED)
        def gen_min(m, t):
            return m.gen_power[t] >= self.config['diesel_min_stable_kw'] * m.gen_status[t]
        model.GenMin = pyo.Constraint(model.T, rule=gen_min)
        
        def gen_max(m, t):
            return m.gen_power[t] <= self.config['diesel_capacity_kw'] * m.gen_status[t]
        model.GenMax = pyo.Constraint(model.T, rule=gen_max)
        
        # 3. Battery Physics
        initial_soc = 0.5 * self.config['battery_capacity_kwh']
        eff = self.config['battery_efficiency']
        
        def soc_tracking(m, t):
            if t == 0: return m.bat_soc[t] == initial_soc
            return m.bat_soc[t] == m.bat_soc[t-1] + m.bat_charge[t]*eff - m.bat_discharge[t]/eff
        model.SOCTracking = pyo.Constraint(model.T, rule=soc_tracking)
        
        def bat_limits(m, t): 
            return m.bat_soc[t] <= self.config['battery_capacity_kwh']
        model.BatLimits = pyo.Constraint(model.T, rule=bat_limits)
        
        # 4. Battery Rate Limits (SPLIT - NO TUPLES ALLOWED)
        def rate_limit_charge(m, t):
            return m.bat_charge[t] <= self.config['battery_power_kw']
        model.RateLimitCharge = pyo.Constraint(model.T, rule=rate_limit_charge)
        
        def rate_limit_discharge(m, t):
            return m.bat_discharge[t] <= self.config['battery_power_kw']
        model.RateLimitDischarge = pyo.Constraint(model.T, rule=rate_limit_discharge)
        
        # 5. Solar Limit
        def solar_limit(m, t): 
            return m.solar_curtailed[t] <= available_solar[t]
        model.SolarLimit = pyo.Constraint(model.T, rule=solar_limit)

        # 6. Sustainability
        def final_soc(m): 
            return m.bat_soc[T-1] >= initial_soc
        model.FinalSOC = pyo.Constraint(rule=final_soc)
        
        # OBJECTIVE: Cost + Carbon
        base_price = self.config['fuel_price_per_L']
        carbon_adder = 0.00268 * self.config.get('carbon_tax_per_ton', 0)
        effective_price = base_price + carbon_adder
        
        intercept_cost = self.config['diesel_intercept_L_hr'] * effective_price
        slope_cost = self.config['diesel_slope_L_kwh'] * effective_price
        
        total_cost = sum((model.gen_status[t] * intercept_cost) + (model.gen_power[t] * slope_cost) for t in model.T)
        penalty = sum(0.01 * model.solar_curtailed[t] for t in model.T)
        
        model.Objective = pyo.Objective(expr=total_cost + penalty, sense=pyo.minimize)
        
        # SOLVER CONFIG
        solver = pyo.SolverFactory('highs')
        solver.options['time_limit'] = 30.0
        solver.options['mip_rel_gap'] = 0.05
        result = solver.solve(model)
        
        # EXPORT
        res = pd.DataFrame(index=df_horizon.index)
        res['gen_power'] = [pyo.value(model.gen_power[t]) for t in model.T]
        res['gen_status'] = [pyo.value(model.gen_status[t]) for t in model.T]
        res['bat_soc'] = [pyo.value(model.bat_soc[t]) for t in model.T]
        res['bat_discharge'] = [pyo.value(model.bat_discharge[t]) for t in model.T]
        res['bat_charge'] = [pyo.value(model.bat_charge[t]) for t in model.T]
        res['solar_used'] = available_solar - [pyo.value(model.solar_curtailed[t]) for t in model.T]
        res['load'] = load_demand
        return res