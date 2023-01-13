<h1>🚍 SMaRTE - System for the Management and Robustness of Transportation Electrification 🔋</h1>
<h2>🚀 Introduction</h2>
This code is an implementation of an energy management model for buses using the Pyomo library in Python. The model is designed to optimize the use of energy by charging and discharging the buses' batteries at the right time in order to minimize the overall cost of energy consumption. The model takes into account various parameters such as the trip time, energy prices, bus and charger characteristics, and power prices. The code uses the CPLEX solver to find the optimal solution.

<h2>📊 Data Input</h2>

The code reads the input data from an Excel file using the Pandas library. The input data includes the following sheets:

<ul>
  <li>Trip time: contains the start and end times of each trip</li>
  <li>Energy price: contains the buying and selling prices of energy at each time step</li>
  <li>Buses: contains the characteristics of each bus, such as the battery capacity</li>
  <li>Chargers: contains the characteristics of each charger, such as the charging and discharging power</li>
  <li>Power price: contains the power and prices of peak power levels</li>
</ul>

<h2>🔧 Model Construction</h2>

The model is created using the Pyomo library and is defined as a concrete model. The following sets are defined in the model:

<table>
  <tr>
    <th>Set Name</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>I</td>
    <td>Set of trips</td>
  </tr>
  <tr>
    <td>T</td>
    <td>Set of timesteps</td>
  </tr>
  <tr>
    <td>K</td>
    <td>Set of buses</td>
  </tr>
  <tr>
    <td>N</td>
    <td>Set of chargers</td>
  </tr>
  <tr>
    <td>L</td>
    <td>Set of peak power levels</td>
  </tr>
</table>

The following parameters are defined in the model:


<table>
  <tr>
    <th>Parameter</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>T_start</td>
    <td>Start time of each trip</td>
  </tr>
  <tr>
    <td>T_end</td>
    <td>End time of each trip</td>
  </tr>
  <tr>
    <td>alpha</td>
    <td>Charging power of each charger</td>
  </tr>
  <tr>
    <td>beta</td>
    <td>Discharging power of each charger</td>
  </tr>
  <tr>
    <td>ch_eff</td>
    <td>Charging efficiency of charger</td>
  </tr>
  <tr>
    <td>dch_eff</td>
    <td>Discharging efficiency of charger</td>
  </tr>
  <tr>
    <td>P</td>
    <td>Electricity purchasing price at each time step</td>
  </tr>
  <tr>
    <td>S</td>
    <td>Electricity selling price at each time step</td>
  </tr>
  <tr>
    <td>gama</td>
    <td>Energy consumption for each trip</td>
  </tr>
  <tr>
    <td>E_0</td>
    <td>Initial energy level of each bus</td>
  </tr>
  <tr>
    <td>E_min</td>
    <td>Minimum energy level of each bus</td>
  </tr>
  <tr>
    <td>E_max</td>
    <td>Maximum energy level of each bus</td>
  </tr>
  <tr>
    <td>E_end</td>
    <td>Final energy level of each bus</td>
  </tr>
  <tr>
    <td>d_off</td>
    <td>Duration of switch off of the charger</td>
  </tr>
  <tr>
    <td>d_on</td>
    <td>Duration of switch on of the charger</td>
  </tr>
  <tr>
    <td>C_bat</td>
    <td>Battery capacity of each bus</td>
  </tr>
  <tr>
    <td>U_pow</td>
    <td>Peak power level</td>
  </tr>
  <tr>
    <td>U_price</td>
    <td>Price of peak power level</td>
  </tr>
  <tr>
    <td>U_max</td>
    <td>Maximum power of each charger</td>
  </tr>
  <tr>
    <td>R</td>
    <td>Battery replacement costs</td>
  </tr>
  <tr>
    <td>Ah</td>
    <td>Ampere hour of the bus</td>
  </tr>
  <tr>
    <td>V</td>
    <td> Voltage of the bus</td>
   </tr>
  <tr>
    <td>T</td>
    <td> Number of timesteps</td>
   </tr>
</table>

<h2>🔍 Optimization</h2>

The code uses the CPLEX solver, which is a powerful optimization solver, to find the optimal solution for the energy management model. The CPLEX solver is able to handle large and complex optimization problems, making it well-suited for the energy management model. The solver is called using the SolverFactory from the Pyomo library, which allows for easy integration with the Pyomo model. Once the solver is called, it runs the optimization algorithm to find the optimal solution for the model. The optimal solution is returned as an instance of the model, which can be used to access the optimized values of the decision variables and other model parameters. This allows for easy analysis of the results and can be used to make decisions on how to best manage the energy consumption of the fleet of buses.

<h2>📈 Data Visualization</h2>

The code also includes a function to plot the results of the optimization. The function uses the Matplotlib library to plot the energy level of the buses and the power consumption of the chargers over time.

Example:

<figure>
  <img src="https://user-images.githubusercontent.com/18650693/212105656-78435c87-6558-455f-a2fb-056bdab6e490.png" alt="Chart illustrating the State-of-charge of eight buses" width="600" height="300">
  <figcaption>Figure 1: Electric bus fleet State-of-Charge variation.</figcaption>
</figure>

<figure>
  <img src="https://user-images.githubusercontent.com/18650693/212105914-fb23d1cb-d962-49e9-a740-cd24f8bf8c93.png" alt="Chart illustrating the power requirements of eight buses" width="600" height="300">
  <figcaption>Figure 2: Electric bus fleet charging power variation</figcaption>
</figure>

<h2>🏁 Conclusion</h2>

In conclusion, the above code is a Pyomo implementation of a mathematical optimization model for managing energy consumption in a fleet of buses. It takes in a data file in Excel format and a list of energy consumption values (gama) as input, and creates a Pyomo ConcreteModel object that represents the model. The model includes sets for trips, timesteps, buses, chargers, and peak power levels, as well as parameters for various data such as trip start and end times, charging and discharging power of chargers, electricity prices, and energy consumption values. The code can be extended with additional constraints and objectives as needed, and can be solved using a variety of optimization solvers, including the CPLEX solver which is called in this code using the SolverFactory. Overall, this code provides a flexible and powerful framework for managing energy consumption in a fleet of buses.
