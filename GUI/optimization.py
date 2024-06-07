import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def read_file(input='input_gui.xlsx'):
    data = pd.read_excel(input, None)
    return data

def setData(data, d_off=4, d_on=1, ch_eff = 0.90, E_0 = 0.2, E_min = 0.2, E_max = 1, E_end = 0.2):
    T_start = data['Dataset']['Trip (Begin)'].tolist()
    T_start = [x for x in T_start if str(x) != 'nan']
    T_start = [int(x) for x in T_start]
    T_end = data['Dataset']['Trip (End)'].tolist()
    T_end = [x for x in T_end if str(x) != 'nan']
    T_end = [int(x) for x in T_end]
    alpha = data['Dataset']['Charger'].tolist()
    alpha = [x for x in alpha if str(x) != 'nan']
    gama = data['Dataset']['Energy consumption'].tolist()
    gama = gama[0]
    Price = data['Dataset']['Energy price'].tolist()
    C_bat = data['Dataset']['Buses'].tolist()
    C_bat = [x for x in C_bat if str(x) != 'nan']
    t = len(Price)
    k = len(C_bat)
    n = len(alpha)
    T = len(Price)
    i = len(T_start)
    return T_start, T_end, alpha, ch_eff, gama, Price, E_0, E_min, E_max, E_end, C_bat, d_off, d_on, t, k, n, T, i

def solveModel(data,time_limit=60,mipgap=0.01,solver='gurobi',status=False):

    T_start, T_end, alpha, ch_eff, gama, P, E_0, E_min, E_max, E_end, C_bat, d_off, d_on, t, k, n, T, i = setData(data)
    
    model = pyo.ConcreteModel()
    
    #ranges
    model.I = pyo.RangeSet(i) # set of trips
    model.T = pyo.RangeSet(t) # set of timesteps
    model.K = pyo.RangeSet(k) # set of buses
    model.N = pyo.RangeSet(n) # set of chargers
    
    #parameters
    model.T_start = pyo.Param(model.I, initialize=lambda model, i: T_start[i-1]) # start time of trip i
    model.T_end = pyo.Param(model.I, initialize=lambda model, i: T_end[i-1]) # end time of trip i
    model.alpha = pyo.Param(model.N, initialize=lambda model, n: alpha[n-1]) # charging power of charger n
    model.ch_eff = pyo.Param(initialize=ch_eff) # charging efficiency of charger n
    model.gama = pyo.Param(initialize=gama) # energy consumption
    model.P = pyo.Param(model.T, initialize=lambda model, t: P[t-1]) # electricity purchasing price in time t
    model.E_0 = pyo.Param(initialize=E_0) # initial energy level of bus k
    model.E_min = pyo.Param(initialize=E_min) # minimum energy level allowed for bus k
    model.E_max = pyo.Param(initialize=E_max) # maximum energy level allowed for bus k
    model.E_end = pyo.Param(initialize=E_end) # minimum energy after an operation day for bus k
    model.C_bat = pyo.Param(model.K, initialize=lambda model, k: C_bat[k-1]) # total capacity of the bus k battery

    #binary variables
    model.b = pyo.Var(model.K,model.I, model.T, within=pyo.Binary) # binary variable indicating if bus k is serving trip i at time t
    model.x = pyo.Var(model.K, model.N, model.T, domain=pyo.Binary) # binary variable indicating if bus k is occupying a charger n at time t to charge
    model.c = pyo.Var(model.K, model.T, domain=pyo.Binary) # binary variable indicating if bus k is charging/discharging at time t
    
    #non-negative variables
    model.e = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals) # energy level of bus k at time t
    model.w_buy = pyo.Var(model.T, within=pyo.NonNegativeReals) # electricity purchased from the grid at time t

    #objective function
    def rule_obj(mod):
        return sum(mod.P[t]*mod.w_buy[t] for t in mod.T)
    model.obj = pyo.Objective(rule=rule_obj, sense=pyo.minimize)

    #constraints
    model.constraints = pyo.ConstraintList()  # Create a set of constraints
    #constraint 1
    for k in model.K:
        for t in model.T:
            model.constraints.add(sum(model.b[k,i,t] for i in model.I) + model.c[k,t] <=1)
            model.constraints.add(sum(model.x[k,n,t] for n in model.N) <= model.c[k,t])
    #constraint 2
    for n in model.N:
        for t in model.T:
            model.constraints.add(sum(model.x[k,n,t] for k in model.K) <= 1)
    #constraint 3
    for i in model.I: 
        for t in range(model.T_start[i],model.T_end[i]):
            model.constraints.add(sum(model.b[k,i,t] for k in model.K) == 1)
    
        for t in range(1,model.T_start[i]):
            model.constraints.add(sum(model.b[k,i,t] for k in model.K) == 0)
    
        for t in range(model.T_end[i],T+1):
            model.constraints.add(sum(model.b[k,i,t] for k in model.K) == 0)
    #constraint 4
    for i in model.I:
        for k in model.K:
            for t in range(model.T_start[i],model.T_end[i]-1):
                model.constraints.add(model.b[k,i,t+1] >= model.b[k,i,t])
    #constraint 5
    for k in model.K:
        for t in range(2,T+1):
            model.constraints.add(model.e[k,t] == model.e[k,t-1] + sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N) - sum(model.gama * model.b[k,i,t] for i in model.I))
    #constraint 6
    for t in model.T:
        model.constraints.add(sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) == model.w_buy[t])
    #constraint 7
    for k in model.K:
        for n in model.N:
            for t in range(2,T-d_off):
                model.constraints.add(1 - model.x[k,n,t] + model.x[k,n,t-1]  + ((1/d_off)*sum(model.x[k,n,j] for j in range(t,t+d_off))) <= 2) # 33
    #constraint 8
    for k in model.K:
        for n in model.N:
            for t in range(T-d_off+1,T):
                model.constraints.add(1 - model.x[k,n,t] + model.x[k,n,t-1] + ((1/(T-t+1))*sum(model.x[k,n,j] for j in range(t,T))) <= 2) # 35
    #constraint 9
    for k in model.K:
        for n in model.N:
            for t in range(2,T-d_on):
                model.constraints.add(1 - model.x[k,n,t] + model.x[k,n,t-1] + ((1/d_on)*sum(model.x[k,n,j] for j in range(t,t+d_on))) >= 1) # 34
    #constraint 10
    for k in model.K:
        for n in model.N:
            for t in range(T-d_on+1,T):
                model.constraints.add(1 - model.x[k,n,t] + model.x[k,n,t-1] + ((1/(T-t+1))*sum(model.x[k,n,j] for j in range(t,T))) >= 1) # 36
    #constraint 11
    for k in model.K:
        for t in model.T:
            model.constraints.add(model.e[k,t] >= model.C_bat[k] * model.E_min)
    #constraint 12
    for k in model.K:
        for t in model.T:
            model.constraints.add(E_max * model.C_bat[k] >= model.e[k,t])          
    #constraint 13
    for k in model.K:
        model.constraints.add(model.e[k,1] == model.E_0*model.C_bat[k])
    #constraint 14
    for k in model.K:
        model.constraints.add(model.e[k,T] >= model.E_end*model.C_bat[k])   
    
    # solving routine
    opt = pyo.SolverFactory(solver)
    if time_limit:
        opt.options['timelimit'] = time_limit
    if mipgap:
        opt.options['mipgap'] = mipgap
    opt.solve(model,tee=status)
    print('The objective function values is:', model.obj())

    return model

def energy_bus(K,T,e,C_bat):
    bus_list = []
    energy_list = []
    for k in K:
        bus_number = 'bus' + ' ' + str(k)
        bus_list.append(bus_number)
    for t in T:
        for  k in K:
            energy_list.append(pyo.value(e[k,t]))
    energy_array = np.reshape(energy_list, (len(T), len(bus_list)))
    Energy = pd.DataFrame(energy_array,index=T, columns=bus_list)
    for k in K:
        Energy_perc = (Energy*100)/C_bat[k]
    return Energy, Energy_perc

def power(T,w):
    transac_list = []
    for t in T:
        value = pyo.value(w[t])
        transac_list.append(value)
    W = pd.DataFrame(transac_list, index=T, columns=['Power'])
    return W

def save_results(model):
    #Calculate energy
    Energy,Energy_perc = energy_bus(model.K, model.T, model.e, model.C_bat)
    #Calculate power buy
    Power = power(model.T, model.w_buy) * 4
    #Calculate objective function value
    Obj = pd.DataFrame({'Objective Value': [model.obj()]})
    #Save data to Excel with the name of t_start
    with pd.ExcelWriter('/Users/natomanzolli/Documents/GitHub/Electric Bus Smart Charging/Results/output.xlsx') as writer:  
        Energy.to_excel(writer, sheet_name='Energy')
        Energy_perc.to_excel(writer, sheet_name='SOC')
        Power.to_excel(writer, sheet_name='Power')
        Obj.to_excel(writer, sheet_name='Optimal value')
    print('The outputs are saved')

def plot(model):
    # Generate energy data
    Energy, Energy_perc = energy_bus(model.K, model.T, model.e, model.C_bat)
    # Generate power data
    Power = power(model.T, model.w_buy) * 4
    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
    # Plot Energy (SOC) on the first subplot
    Energy_perc.plot(ax=ax1)
    ax1.set_xlabel('Time')
    ax1.set_ylabel('State of Charge [%]')
    ax1.set_title('Energy (SOC) Over Time')
    # Plot charging Power on the second subplot
    Power.plot(ax=ax2)
    ax2.set_xlabel('Time [min]')
    ax2.set_ylabel('Power [kW]')
    ax2.set_title('Charging Power Over Time')
    # Adjust layout to prevent overlap
    plt.tight_layout()
    # Show the figure
    plt.show()