import logging
from src.data_gen import RealMicrogridData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    # Generate Ground Truth Data
    gen = RealMicrogridData(raw_path="data/raw")
    # Scale to 450kW Peak (Remote Community Size)
    df = gen.load_and_process(target_peak_load_kw=450.0)
    df.to_csv("data/raw/microgrid_data.csv")
    logging.info("Microgrid data generated successfully.")

if __name__ == "__main__":
    main()