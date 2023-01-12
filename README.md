<h1>Documentation for EBSCM (Electric Bus Smart Charging Model)</h1>

<h2>Introduction</h2>
This code is an implementation of an energy management model for buses using the Pyomo library in Python. The model is designed to optimize the use of energy by charging and discharging the buses' batteries at the right time in order to minimize the overall cost of energy consumption. The model takes into account various parameters such as the trip time, energy prices, bus and charger characteristics, and power prices. The code uses the CPLEX solver to find the optimal solution.

<h2>Data Input</h2>
The code reads the input data from an Excel file using the Pandas library. The input data includes the following sheets:
- Trip time: contains the start and end times of each trip
- Energy price: contains the buying and selling prices of energy at each time step
- Buses: contains the characteristics of each bus, such as the battery capacity
- Chargers: contains the characteristics of each charger, such as the charging and discharging power
- Power price: contains the power and prices of peak power levels

<h2>Model Construction</h2>
The model is created using the Pyomo library and is defined as a concrete model. The following sets are defined in the model:
- I: set of trips
- T: set of timesteps
- K: set of buses
- N: set of chargers
- L: set of peak power levels
The following parameters are defined in the model:

T_start: start time of each trip
T_end: end time of each trip
alpha: charging power of each charger
beta: discharging power of each charger
ch_eff: charging efficiency of charger
dch_eff: discharging efficiency of charger
P: electricity purchasing price at each time step
S: electricity selling price at each time step
gama: energy consumption for each trip
E_0: initial energy level of each bus
E_min: minimum energy level of each bus
E_max: maximum energy level of each bus
E_end: final energy level of each bus
d_off: duration of switch off of the charger
d_on: duration of switch on of the charger
C_bat: battery capacity of each bus
U_pow: peak power level
U_price: price of peak power level
U_max: maximum power of each charger
R: resistance of the bus
Ah: ampere hour of the bus
V: voltage of the bus
T: number of timesteps

<h2>Optimization</h2>
The code uses the CPLEX solver to find the optimal solution for the model. The solver is called using the SolverFactory from the Pyomo library. The optimal solution is returned as an instance of the model.

<h2>Results</h2>
The code also includes a function to plot the results of the optimization. The function uses the Matplotlib library to plot the energy level of the buses and the power consumption of the chargers over time.

<h2>Conclusion</h2>
In conclusion, the above code is a Pyomo implementation of a mathematical optimization model for managing energy consumption in a fleet of buses. It takes in a data file in Excel format and a list of energy consumption values (gama) as input, and creates a Pyomo ConcreteModel object that represents the model. The model includes sets for trips, timesteps, buses, chargers, and peak power levels, as well as parameters for various data such as trip start and end times, charging and discharging power of chargers, electricity prices, and energy consumption values. The code can be extended with additional constraints and objectives as needed, and can be solved using a variety of optimization solvers, including the CPLEX solver which is called in this code using the SolverFactory. Overall, this code provides a flexible and powerful framework for managing energy consumption in a fleet of buses.
