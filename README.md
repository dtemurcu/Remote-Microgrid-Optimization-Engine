# Remote Microgrid Optimization Engine

**Northern Ontario Microgrid Planner**

A decision-support tool designed to optimize the design and dispatch of hybrid microgrids in remote Northern Ontario communities. This engine uses Mixed-Integer Linear Programming (MILP) to minimize fuel consumption and carbon costs while ensuring reliable power delivery.

## 🔋 Project Overview

Remote communities often rely heavily on expensive and carbon-intensive diesel generators. This project provides a simulation and optimization engine that helps planners:

* **Size Assets:** Evaluate the economic impact of different Battery Energy Storage System (BESS) and Solar PV capacities.
* **Optimize Dispatch:** Determine the optimal hourly operation of diesel generators, batteries, and solar arrays to minimize costs.
* **Analyze Economics:** Calculate CAPEX, annual fuel savings, carbon tax reductions, and payback periods.

## ✨ Key Features

* **Interactive Dashboard:** A Streamlit-based UI to adjust economic parameters (Diesel Price, Carbon Tax) and system sizing in real-time.
* **Advanced Optimization:** Uses `Pyomo` and the `HiGHS` solver to perform rigorous operational optimization, respecting generator constraints (minimum stable loads) and battery physics.
* **Northern Context:** Pre-configured with defaults relevant to Northern Ontario (e.g., seasonal solar profiles, specific fuel pricing, and carbon taxation).
* **Visual Analytics:** Interactive Plotly charts showing hourly dispatch strategies, load balancing, and renewable curtailment.

## 🛠️ Installation

### Prerequisites

* Python 3.10+
* A MILP Solver (Recommended: **HiGHS**)

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/Remote-Microgrid-Optimization-Engine.git](https://github.com/your-username/Remote-Microgrid-Optimization-Engine.git)
cd Remote-Microgrid-Optimization-Engine
```

### 2. Install Dependencies

```bash
pip install pandas plotly pyomo streamlit highs-python numpy
```

## 🚀 Usage

### 1. Generate Baseline Data

Before running the dashboard, generate the synthetic microgrid load and solar data (scaled to a 450kW peak load).

```bash
python run_microgrid.py
```

*This script uses `src/data_gen.py` to create `data/raw/microgrid_data.csv`.*

### 2. Launch the Dashboard

Run the interactive application to simulate different scenarios.

```bash
streamlit run app_microgrid.py
```

## ⚙️ Technical Methodology

The core optimization logic resides in `src/optimization.py`. It formulates the microgrid dispatch problem as a Mixed-Integer Linear Program (MILP).

**Objective Function:**
$$ \text{Minimize} \quad (\text{Fuel Cost} + \text{Carbon Tax} + \text{Solar Curtailment Penalty}) $$

**Key Constraints:**

* **Energy Balance:** Supply (Diesel + Battery Discharge + Solar) must equal Demand (Load + Battery Charge).
* **Diesel Generator:** Enforces Minimum Stable Load (e.g., 150kW minimum output) and maximum capacity.
* **Battery Physics:** Tracks State of Charge (SoC), efficiency losses (round-trip), and charge/discharge rate limits.
* **Sustainability:** Ensures the battery SoC at the end of the horizon is at least equal to the initial SoC.

## 📂 Project Structure

```text
├── app_microgrid.py        # Main Streamlit dashboard application
├── run_microgrid.py        # Script to generate/refresh input data
├── src/
│   ├── optimization.py     # Pyomo MILP model definition
│   └── data_gen.py         # Data loading and processing utilities
├── data/
│   └── raw/                # Input CSV files (Load profiles, Solar data)
└── outputs/                # Generated figures and reports
```

## 📝 License

[MIT License](LICENSE)
