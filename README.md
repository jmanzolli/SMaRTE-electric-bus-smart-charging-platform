# SMaRTE — System for the Management and Robustness of Transportation Electrification

> **Mixed-Integer Linear Programming platform for the optimal smart charging of electric bus fleets**, with support for deterministic, robust, sensitivity, and bi-level market formulations, plus a standalone desktop GUI.

---

## Table of Contents

1. [Overview](#overview)
2. [Repository Structure](#repository-structure)
3. [Optimisation Models](#optimisation-models)
   - [Deterministic Model](#1-deterministic-model)
   - [Robust Model](#2-robust-model)
   - [Sensitivity Analysis](#3-sensitivity-analysis)
   - [Bi-level Aggregator Model](#4-bi-level-aggregator-model)
4. [Mathematical Formulation](#mathematical-formulation)
5. [Input Data Format](#input-data-format)
6. [Output Data](#output-data)
7. [Desktop GUI](#desktop-gui)
8. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Running the Models](#running-the-models)
   - [Running the GUI](#running-the-gui)
9. [Key Parameters](#key-parameters)
10. [Contributing](#contributing)
11. [License](#license)
12. [Acknowledgements](#acknowledgements)

---

## Overview

**SMaRTE** is a research-grade optimisation platform designed to schedule the smart charging and Vehicle-to-Grid (V2G) discharging of electric bus fleets. Given a set of pre-defined bus trips, a fleet of buses with heterogeneous battery capacities, a set of chargers, and time-varying electricity prices, SMaRTE finds the charging/discharging schedule that minimises total operational costs — composed of:

- **Grid energy purchasing costs** (buying electricity at time-varying prices)
- **V2G selling revenues** (selling energy back to the grid)
- **Battery degradation costs** (wear from V2G discharging cycles)
- **Contracted peak power costs** (demand charge tier selection)

The platform covers four modelling paradigms and includes a desktop application for practitioners who do not require coding experience.

---

## Repository Structure

```
SMaRTE-electric-bus-smart-charging-platform/
│
├── Deterministic/              # Single-level deterministic MILP
│   ├── model_deterministic.py  # Standalone script
│   └── model_deterministic.ipynb
│
├── Robust/                     # Robust optimisation under energy consumption uncertainty
│   ├── model_robust.py         # Robust counterpart (worst-case energy)
│   ├── model_robust.ipynb
│   └── model_counterpart_robust.ipynb
│
├── Sensitivity/                # Parametric / sensitivity analysis
│   ├── model_sensitivity.py    # Sweeps fleet size, battery capacity, charger rating
│   └── model_sensitivity.ipynb
│
├── Bi-level approach/          # Bi-level aggregator ↔ fleet operator model
│   ├── Bi-level codes/
│   │   ├── BiLevelAggregator.ipynb          # Main bi-level model
│   │   ├── BiLevelAggregatorScenarios.ipynb # Scenario analysis variant
│   │   ├── BiLevelAggregatorSensitivity.ipynb
│   │   ├── build/
│   │   │   ├── BiLevelBus.py   # Lozano-Smith decomposition algorithm
│   │   │   └── gui.py          # Bi-level GUI
│   │   └── tests/              # Small-scale test notebooks (L&S, DBP)
│   ├── Instances/              # Bi-level input files (8–10 buses, various resolutions)
│   └── Robust/                 # Robust extensions of the bi-level model
│
├── GUI/                        # Standalone Tkinter desktop application
│   ├── gui.py                  # Application entry point
│   ├── optimization.py         # Simplified single-level model (Gurobi)
│   └── assets/frame0/          # UI image assets
│
├── Instances/                  # Input Excel files
│   ├── input_deterministic.xlsx
│   ├── input_robust.xlsx
│   └── input_gui.xlsx
│
├── Results/                    # Generated output Excel files (gitignored)
│   ├── output_deterministic.xlsx
│   ├── output_robust.xlsx
│   ├── output_robustcounterpart.xlsx
│   ├── output_sensitivity.xlsx
│   └── output.xlsx             # GUI output
│
├── requirements.txt
├── .gitignore
└── LICENSE
```

---

## Optimisation Models

### 1. Deterministic Model

**Location:** `Deterministic/`

A full Mixed-Integer Linear Program (MILP) solved over a planning horizon discretised into one-minute timesteps. All input data (energy consumption, prices) is treated as known with certainty.

**Key features:**
- Bi-directional charging: supports both grid-to-vehicle (G2V) charging and vehicle-to-grid (V2G) discharging
- Charger minimum on/off time constraints (prevents rapid switching)
- Contracted peak power tier selection via binary variable `u[l]`
- Battery degradation cost based on depth of discharge and battery chemistry parameters
- State-of-Charge (SOC) tracking with initial, minimum, maximum, and terminal bounds

### 2. Robust Model

**Location:** `Robust/`

Extends the deterministic model to handle **uncertainty in energy consumption** (e.g., due to variable route distances, traffic, and weather). Two approaches are provided:

- **Conservative robust counterpart** (`model_robust.py`): The uncertain energy consumption parameter `γ` is inflated to its worst-case value using a configurable deviation factor and conservatism level:

  ```python
  γ_robust = γ_nominal + max_deviation × dev_factor × conservatism_factor
  ```

- **Robust counterpart notebook** (`model_counterpart_robust.ipynb`): Implements a formal robust counterpart formulation consistent with the Bertsimas & Sim uncertainty set framework.

### 3. Sensitivity Analysis

**Location:** `Sensitivity/`

Systematically varies key fleet and infrastructure parameters to evaluate their impact on total operational cost. The `model_sensitivity.py` script exposes `createModel()` with configurable keyword arguments, enabling programmatic sweeps over:

- **Number of buses** (`numberBuses()`)
- **Battery capacity** per bus (kWh)
- **Charger rating** (kWh/min)
- **Battery replacement cost** `R` ($/kWh)

Results for each scenario are appended as new sheets in `Results/output_sensitivity.xlsx`.

### 4. Bi-level Aggregator Model

**Location:** `Bi-level approach/`

A **bi-level optimisation** that captures the strategic interaction between an **energy market aggregator** (upper level) and the **electric bus fleet operator** (lower level):

| Level | Agent | Decision | Objective |
|-------|-------|----------|-----------|
| **Upper** | Grid aggregator | Sets energy buying price `ρ⁺[p]`, selling price `ρ⁻[p]`, and capacity price `μ[p]` per period | Maximise aggregator profit |
| **Lower** | Fleet operator | Schedules charging `x[k,n,t]` and discharging `y[k,n,t]` given announced prices | Minimise fleet operational cost |

The lower-level problem is the same MILP as the deterministic model. The upper-level prices are bounded by market price corridors `[X_low, X_up]` and `[Mi_low, Mi_up]` and an average price cap.

The **Lozano-Smith decomposition** algorithm (`BiLevelBus.py`) is used to solve this problem iteratively. Variant notebooks cover:
- `BiLevelAggregatorScenarios.ipynb` — multiple energy price scenarios
- `BiLevelAggregatorSensitivity.ipynb` — sensitivity of bi-level solution to fleet parameters
- `Robust/BiLevelRobust.ipynb` — robust bi-level under demand uncertainty

---

## Mathematical Formulation

### Sets

| Symbol | Description |
|--------|-------------|
| $\mathcal{I}$ | Set of trips |
| $\mathcal{T}$ | Set of timesteps |
| $\mathcal{K}$ | Set of buses |
| $\mathcal{N}$ | Set of chargers |
| $\mathcal{L}$ | Set of contracted power levels |

### Decision Variables

| Variable | Type | Description |
|----------|------|-------------|
| $b_{k,i,t}$ | Binary | Bus $k$ serves trip $i$ at time $t$ |
| $x_{k,n,t}$ | Binary | Bus $k$ charges at charger $n$ at time $t$ |
| $y_{k,n,t}$ | Binary | Bus $k$ discharges (V2G) via charger $n$ at time $t$ |
| $c_{k,t}$ | Binary | Bus $k$ is available for charging/discharging at time $t$ |
| $u_l$ | Binary | Contracted power tier $l$ is selected |
| $e_{k,t}$ | Continuous ≥ 0 | Energy (SOC) of bus $k$ at time $t$ (kWh) |
| $w^+_t$ | Continuous ≥ 0 | Power purchased from grid at time $t$ (kWh/min) |
| $w^-_t$ | Continuous ≥ 0 | Power sold to grid at time $t$ (kWh/min) |
| $d_{k,t}$ | Continuous ≥ 0 | Battery degradation cost for bus $k$ at time $t$ |

### Objective Function

$$\min \sum_{t} P_t w^+_t - \sum_{t} S_t w^-_t + \sum_{k,t} d_{k,t} + \sum_{l} U^{\text{price}}_l u_l$$

where $P_t$ is the electricity buying price, $S_t$ the selling price, and $U^{\text{price}}_l$ the demand charge for power tier $l$.

### Key Constraints

- **Mutual exclusion**: A bus cannot serve a trip and charge simultaneously
- **Trip coverage**: Each trip must be assigned to exactly one bus throughout its duration
- **Charger exclusivity**: At most one bus per charger per timestep
- **SOC dynamics**: $e_{k,t} = e_{k,t-1} + \eta^+ \alpha_n x_{k,n,t} - \gamma_i b_{k,i,t} - \eta^- \beta_n y_{k,n,t}$
- **SOC bounds**: $E_{\min} C^{\text{bat}}_k \leq e_{k,t} \leq E_{\max} C^{\text{bat}}_k$
- **Initial / terminal SOC**: $e_{k,1} = E_0 C^{\text{bat}}_k$, $e_{k,T} \geq E_{\text{end}} C^{\text{bat}}_k$
- **Charger min on/off time**: Prevents rapid cycling of chargers (configurable $d_{\text{on}}$, $d_{\text{off}}$)
- **Peak power tier**: Exactly one tier $l$ selected; total charging power ≤ contracted tier power

---

## Input Data Format

All models read input from **Excel workbooks** (`.xlsx`) with the following sheets:

| Sheet | Columns | Description |
|-------|---------|-------------|
| `Trip time` | `Time begin (min)`, `Time finish (min)` | Start and end time of each trip (integer minutes from midnight) |
| `Energy price` | `Energy buying price (per minute)`, `Energy selling price (per minute)` | Time-varying electricity prices |
| `Buses` | `Bus (kWh)` | Battery capacity of each bus |
| `Chargers` | `Charger (kWh/min)`, `Max Power (kW)` | Charging/discharging rate and maximum grid power per charger |
| `Power price` | `Power`, `Price` | Power tier levels and associated demand charges |
| `Energy consumption` | `Uncertain energy (kWh/km*min)`, `Maximum deviation (kWh/km*min)` | Nominal energy consumption and uncertainty bound per trip |

Sample input files are provided in `Instances/`:
- `input_deterministic.xlsx` — base case
- `input_robust.xlsx` — includes uncertainty columns
- `input_gui.xlsx` — simplified single-sheet format for the GUI (`Dataset` sheet)

The **Bi-level** instances in `Bi-level approach/Instances/` additionally include:
- `Prices` sheet: spot market and capacity market prices per timestep
- `Average prices` sheet: price corridor bounds per aggregation period
- `Periods` sheet: period start/end times and lengths

---

## Output Data

Results are written to Excel files in `Results/`:

| File | Contents |
|------|----------|
| `output_deterministic.xlsx` | Bus SOC profiles, power transactions, degradation, objective value |
| `output_robust.xlsx` | Robust charging schedule outputs |
| `output_robustcounterpart.xlsx` | Formal robust counterpart results |
| `output_sensitivity.xlsx` | Multi-sheet results per parameter sweep scenario |
| `output.xlsx` | GUI run output — SOC, power, and optimal cost |

Each output workbook typically contains sheets for:
- **Energy** — SOC (kWh) of each bus over time
- **SOC (%)** — State of charge as a percentage of battery capacity
- **Power** — Grid power transaction profile (kW)
- **Optimal value** — Total minimised operational cost

---

## Desktop GUI

**Location:** `GUI/`

A Tkinter-based desktop application titled **"DRIVE-TECH — Moving Sustainability Further"** that provides a no-code interface to the simplified charging optimisation model.

**Features:**
- Browse and load any compatible Excel input file
- Run the MILP optimisation in a background thread (Gurobi solver)
- Display results in real time: total operational cost reported in the log panel
- Interactive plots of bus SOC (%) and grid power demand over the planning horizon
- Save results to `output.xlsx`

**Workflow:**

```
Browse input file → Run (Optimise) → View plots → Save results
```

> The GUI uses a simplified model variant (`optimization.py`) with a shorter set of constraints suitable for interactive use — no V2G, no peak power tiers — focused on demonstrating core charging schedule optimality.

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | |
| Pyomo | 6.1.2 | Modelling layer |
| gurobipy | 9.5.2 | Required for GUI and some notebooks |
| CPLEX | 22.1+ | Required for `model_*.py` scripts (path set via `EXEC_PATH`) |
| pandas | 1.3.5 | Data I/O |
| matplotlib | 3.5.1 | Visualisation |
| openpyxl | 3.0.9 | Excel read/write |

> Either **Gurobi** or **CPLEX** is required depending on the model being run. Academic licences are available from both vendors. The GUI uses Gurobi; the standalone `.py` scripts use CPLEX.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jmanzolli/SMaRTE-electric-bus-smart-charging-platform.git
   cd SMaRTE-electric-bus-smart-charging-platform
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your solver path. In `model_deterministic.py`, `model_robust.py`, and `model_sensitivity.py`, update:
   ```python
   EXEC_PATH = '/path/to/your/cplex/bin/cplex'
   ```
   For Gurobi users, `gurobipy` is registered automatically once a valid licence is present.

### Running the Models

**Deterministic model (script):**
```bash
cd Deterministic
python model_deterministic.py
```

**Robust model (script):**
```bash
cd Robust
python model_robust.py
```

**Sensitivity analysis (script):**
```bash
cd Sensitivity
python model_sensitivity.py
```

**Jupyter notebooks:** open any `.ipynb` file directly in JupyterLab or VS Code and execute cells sequentially. Instance paths are configured in the first cell of each notebook.

### Running the GUI

```bash
cd GUI
python gui.py
```

> **Note:** The GUI requires `tkinter` (included in the standard CPython distribution on Windows/Linux; on macOS install via `brew install python-tk`).

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ch_eff` | 0.90 | Charger charging efficiency (η⁺) |
| `dch_eff` | 1/0.90 ≈ 1.11 | Charger discharging efficiency factor (η⁻) |
| `E_0` | 0.20 | Initial SOC (fraction of battery capacity) |
| `E_min` | 0.20 | Minimum allowed SOC (fraction) |
| `E_max` | 1.00 | Maximum allowed SOC (fraction) |
| `E_end` | 0.20 | Minimum required SOC at end of day (fraction) |
| `R` | 130 $/kWh | Battery replacement cost |
| `Ah` | 905,452 Ah | Total amp-hours until battery end-of-life |
| `V` | 512 V | Bus battery operational voltage |
| `d_on` | 40 min | Minimum charger on-time per session |
| `d_off` | 20 min | Minimum charger off-time between sessions |
| MIP gap | 1% | Solver optimality tolerance |
| Time limit | 3,600 s | Solver wall-clock time limit |

---

## Contributing

Contributions are welcome. Please fork the repository, create a feature branch, and open a pull request with a clear description of the changes.

For significant changes — new model formulations, new solver interfaces, or extensions to the GUI — please open an issue first to discuss the approach.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- **Pyomo** — open-source algebraic modelling language for Python
- **Gurobi** and **IBM CPLEX** — commercial MILP solvers used for solving the optimisation models
- **Lozano & Smith** decomposition algorithm implemented in the bi-level formulation
- All contributors and the operations research / sustainable transport communities whose foundational work informed this platform

---

*For more details, visit the [GitHub repository](https://github.com/jmanzolli/SMaRTE-electric-bus-smart-charging-platform).*
