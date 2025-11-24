import pandas as pd
import numpy as np
import logging
from pathlib import Path
import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class RealMicrogridData:
    def __init__(self, raw_path="data/raw"):
        self.raw_path = Path(raw_path)

    def load_and_process(self, target_peak_load_kw=450.0):
        """
        Ingests IESO Load + Env Canada Weather.
        Returns DataFrame with: ['load_kw', 'solar_pu', 'temp_c']
        """
        logging.info("Loading REAL data from Project 1 files...")
        
        # 1. LOAD DEMAND
        load_files = list(self.raw_path.glob("PUB_Demand*.csv"))
        if not load_files: raise FileNotFoundError("No PUB_Demand csv found!")
        
        df_load = pd.read_csv(load_files[0], header=3)
        df_load.columns = [c.strip().lower().replace(' ', '_') for c in df_load.columns]
        if 'hour' in df_load.columns: df_load['hour'] -= 1
        
        df_load['timestamp'] = pd.to_datetime(df_load['date']) + pd.to_timedelta(df_load['hour'], unit='h')
        df_load = df_load.set_index('timestamp').sort_index()
        
        # Scale Load
        target_col = 'ontario_demand' if 'ontario_demand' in df_load.columns else 'market_demand'
        scaling_factor = target_peak_load_kw / df_load[target_col].max()
        
        df_final = pd.DataFrame()
        df_final['load_kw'] = df_load[target_col] * scaling_factor

        # 2. LOAD WEATHER
        weather_files = list(self.raw_path.glob("en_climate_hourly_*.csv"))
        if not weather_files: raise FileNotFoundError("No weather CSVs found!")
        
        df_list = []
        for f in weather_files:
            try:
                temp = pd.read_csv(f)
                df_list.append(temp)
            except: pass
            
        df_w = pd.concat(df_list, ignore_index=True)
        df_w['timestamp'] = pd.to_datetime(df_w['Date/Time (LST)'])
        df_w = df_w.set_index('timestamp').sort_index()
        df_w = df_w[~df_w.index.duplicated(keep='first')]

        # 3. GENERATE SOLAR
        df_final = df_final.join(df_w, how='inner')
        
        # Physics: Clear Sky Model (Lat 50)
        lat_rad = 50 * (np.pi / 180)
        day_of_year = df_final.index.dayofyear
        hour = df_final.index.hour + df_final.index.minute / 60.0
        
        declination = 0.409 * np.sin(2 * np.pi * (284 + day_of_year) / 365)
        w = (hour - 12) * 15 * (np.pi / 180)
        sin_elev = np.sin(lat_rad) * np.sin(declination) + np.cos(lat_rad) * np.cos(declination) * np.cos(w)
        sin_elev = np.maximum(0, sin_elev)
        
        # NLP: Cloud Factor
        def get_cloud_factor(text):
            t = str(text).lower()
            if 'clear' in t or 'sunny' in t: return 1.0
            if 'main' in t: return 0.8
            if 'cloud' in t or 'overcast' in t: return 0.4
            if 'rain' in t or 'snow' in t: return 0.2
            return 0.5
            
        cloud_factor = df_final['Weather'].apply(get_cloud_factor)
        
        solar_pu = sin_elev * cloud_factor
        solar_pu = solar_pu / solar_pu.max() # Normalize peak to 1.0
        
        df_final['solar_pu'] = np.clip(solar_pu, 0.0, 1.0)
        df_final['temp_c'] = df_final['Temp (°C)'].fillna(0)

        return df_final[['load_kw', 'solar_pu', 'temp_c']]