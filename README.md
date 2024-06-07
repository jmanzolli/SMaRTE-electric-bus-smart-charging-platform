# SMaRTE - System for the Management and Robustness of Transportation Electrification

## Overview

Welcome to the SMaRTE (System for the Management and Robustness of Transportation Electrification) platform! This project aims to optimise the charging schedules for electric bus fleets, minimising energy costs and maximising efficiency using advanced optimisation techniques.

## Features

- **Optimised Charging Schedules**: Utilises Pyomo and the Gurobi solver to find cost-effective charging times.
- **Data-Driven Decisions**: Incorporates real-world data on trip schedules, energy prices, bus characteristics, and charger capabilities.
- **Scalable and Flexible**: Can be adapted to various fleet sizes and energy market conditions.

## Getting Started

### Prerequisites

- Python 3.x
- Pyomo
- Gurobi
- Pandas
- OpenPyXL

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jmanzolli/SMaRTE-electric-bus-smart-charging-platform.git
   cd SMaRTE-electric-bus-smart-charging-platform
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure Gurobi is installed and properly configured. Refer to the [Gurobi installation guide](https://www.gurobi.com/documentation/9.1/quickstart_linux/software_installation_guid.html).

### Running the Model

1. Prepare your input data in an Excel file, structured as follows:
   - **Trip time**: Start and end times of each trip.
   - **Energy price**: Buying and selling prices at each timestep.
   - **Buses**: Battery capacity and other characteristics of each bus.
   - **Chargers**: Charging and discharging power for each charger.
   - **Power price**: Power prices at different peak levels.

2. Update the `config.yaml` file with the path to your input data and other configuration parameters.

3. Run the optimisation script:
   ```bash
   python optimise_charging.py
   ```

### Output

The results will be saved in the `results` directory, including:
- Optimised charging schedules
- Energy cost breakdowns
- Visualisations of energy and charging patterns

## Contributing

We welcome contributions to enhance the platform! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project utilises the Pyomo library for optimisation modelling and the Gurobi solver for finding optimal solutions. Special thanks to all contributors and the open-source community.

---

For more details, visit our [GitHub page](https://github.com/jmanzolli/SMaRTE-electric-bus-smart-charging-platform).
