import pyomo.environ as pyo
from pyomo.solvers.plugins.solvers.cplex_persistent import CPLEXPersistent
from pyomo.opt import SolverFactory
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

data = pd.read_excel('Instances/input_small.xlsx', None)
EXEC_PATH = '/Applications/CPLEX_Studio221/cplex/bin/x86-64_osx/cplex'

def createModel(data,gama):

    model = pyo.ConcreteModel() # create model
    
    #DATA
    i = len(data['Trip time']['Time begin (min)'])
    t = len(data['Energy price']['Energy buying price (per minute)'])
    k = len(data['Buses']['Bus (kWh)'])
    n = len(data['Chargers']['Charger (kWh/min)'])
    l = len(data['Power price']['Power'])
    T_start = data['Trip time']['Time begin (min)'].tolist()
    T_start = [int(x) for x in T_start]
    T_end = data['Trip time']['Time finish (min)'].tolist()
    T_end = [int(x) for x in T_end]
    alpha = data['Chargers']['Charger (kWh/min)'].tolist()
    beta = data['Chargers']['Charger (kWh/min)'].tolist()
    ch_eff = 0.90
    dch_eff = 1/0.9
    P = data['Energy price']['Energy buying price (per minute)'].tolist()
    S = data['Energy price']['Energy selling price (per minute)'].tolist()
    E_0 = 0.2
    E_min = 0.2
    E_max = 1
    E_end = 0.2
    C_bat = data['Buses']['Bus (kWh)'].tolist()
    U_pow = data['Power price']['Power'].tolist()
    U_price = data['Power price']['Price'].tolist()
    U_max = data['Chargers']['Max Power (kW)'].tolist()
    R = 130
    Ah = 905452
    V = 512
    T = t

    ## SETS
    model.I = pyo.RangeSet(i) # set of trips
    model.T = pyo.RangeSet(t) # set of timesteps
    model.K = pyo.RangeSet(k) # set of buses
    model.N = pyo.RangeSet(n) # set of chargers
    model.L = pyo.RangeSet(l) # set of peak power levels

    ## PARAMETERS
    model.T_start = pyo.Param(model.I, initialize=lambda model, i: T_start[i-1]) # start time of trip i
    model.T_end = pyo.Param(model.I, initialize=lambda model, i: T_end[i-1]) # end time of trip i
    model.alpha = pyo.Param(model.N, initialize=lambda model, n: alpha[n-1]) # charging power of charger n
    model.beta = pyo.Param(model.N, initialize=lambda model, n: beta[n-1]) # discharging power of charger n
    model.ch_eff = pyo.Param(initialize=ch_eff) # charging efficiency of charger n
    model.dch_eff = pyo.Param(initialize=dch_eff) # discharging efficiency of charger n
    model.P = pyo.Param(model.T, initialize=lambda model, t: P[t-1]) # electricity purchasing price in time t
    model.S = pyo.Param(model.T, initialize=lambda model, t: S[t-1]) # electricity selling price in time t
    model.gama = pyo.Param(model.I, initialize=lambda model, i: gama[i-1],mutable=True) # energy consumption
    model.E_0 = pyo.Param(initialize=E_0) # initial energy level of bus k
    model.E_min = pyo.Param(initialize=E_min) # minimum energy level allowed for bus k
    model.E_max = pyo.Param(initialize=E_max) # maximum energy level allowed for bus k
    model.E_end = pyo.Param(initialize=E_end) # minimum energy after an operation day for bus k
    model.C_bat = pyo.Param(model.K, initialize=lambda model, k: C_bat[k-1]) # total capacity of the bus k battery
    model.U_pow = pyo.Param(model.L, initialize=lambda model, l: U_pow[l-1]) # power level l
    model.U_price = pyo.Param(model.L, initialize=lambda model, l: U_price[l-1]) # purchasing price for power level l
    model.U_max = pyo.Param(initialize=U_max[0]) # contracted power
    model.R = pyo.Param(initialize=R) # battery replacement costs of the bus k
    model.Ah = pyo.Param(initialize=Ah) # energy consumed until EOL of bus k
    model.V = pyo.Param(initialize=V) # operational voltage of charger n

    # BINARY VARIABLES
    model.b = pyo.Var(model.K,model.I, model.T, within=pyo.Binary) # binary variable indicating if bus k is serving trip i at time t
    model.x = pyo.Var(model.K, model.N, model.T, domain=pyo.Binary) # binary variable indicating if bus k is occupying a charger n at time t to charge
    model.y = pyo.Var(model.K, model.N, model.T, domain=pyo.Binary) # binary variable indicating if bus k is occupying a charger n at time t to discharge
    model.c = pyo.Var(model.K, model.T, domain=pyo.Binary)  # binary variable indicating if bus k is charging/discharging at time t
    model.u = pyo.Var(model.L, domain=pyo.Binary)  # binary variable indicating the peak power level l

    # NON-NEGATIVE VARIABLES
    model.e = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals) # energy level of bus k at time t
    model.w_buy = pyo.Var(model.T, within=pyo.NonNegativeReals) # electricity purchased from the grid at time t
    model.w_sell = pyo.Var(model.T, within=pyo.NonNegativeReals) # electricity sold to the grid at time t
    model.d = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals) # total degradation cost of the bus k battery at time t

    # CONSTRAINTS
    model.constraints = pyo.ConstraintList()

    #constraint 2
    for k in model.K:
        for t in model.T:
            model.constraints.add(sum(model.b[k,i,t] for i in model.I) + model.c[k,t] <=1)
    #constraint 3
    for i in model.I: 
        for t in range(model.T_start[i],model.T_end[i]):
            model.constraints.add(sum(model.b[k,i,t] for k in model.K) == 1)
    #constraint 4
    for i in model.I:
        for k in model.K:
            for t in range(model.T_start[i],model.T_end[i]-1):
                model.constraints.add(model.b[k,i,t+1] >= model.b[k,i,t])
    #constraint 5
    for n in model.N:
        for t in model.T:
            model.constraints.add(sum(model.x[k,n,t] for k in model.K) + sum(model.y[k,n,t] for k in model.K) <= 1)
    #constraint 6
    for k in model.K:
        for t in model.T:
            model.constraints.add(sum(model.x[k,n,t] for n in model.N) + sum(model.y[k,n,t] for n in model.N) <= model.c[k,t])
    #constraint 7
    for k in model.K:
        for t in range(2,1441):
            model.constraints.add(model.e[k,t] == model.e[k,t-1] + sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N) - sum(model.gama[i]*model.b[k,i,t] for i in model.I) - sum(model.dch_eff*model.beta[n]*model.y[k,n,t] for n in model.N))
    #constraint 8.1
    for t in model.T:
        model.constraints.add(sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) == model.w_buy[t])
    #constraint 8.2
    for t in model.T:
            model.constraints.add(sum(model.dch_eff*model.beta[n]*model.y[k,n,t] for n in model.N for k in model.K) == model.w_sell[t])
    #constraint 9
    model.constraints.add(sum(model.u[l] for l in model.L)==1)
    #constraint 10
    for t in model.T:
        model.constraints.add(sum(model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) <= sum(model.U_pow[l]*model.u[l] for l in model.L))  
    #constraint 11
    for t in model.T:
        model.constraints.add(sum(model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) + sum(model.beta[n]*model.y[k,n,t] for n in model.N for k in model.K) <= model.U_max)
    #constraint 12
    for k in model.K:
        for t in model.T:
            model.constraints.add(model.e[k,t] >= model.C_bat[k] * model.E_min)
    #constrait 13
    for k in model.K:
        for t in model.T:
            model.constraints.add(model.E_max * model.C_bat[k] >= model.e[k,t] + sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N))          
    #constraint 14.1
    for k in model.K:
        model.constraints.add(model.e[k,1] == model.E_0*model.C_bat[k])
    #constraint 14.2
    for k in model.K:
        model.constraints.add(model.e[k,1440]  >= model.E_end*model.C_bat[k])   
    #constraint 15
    for k in model.K:
        for t in model.T:
            model.constraints.add(model.d[k,t] == ((model.R*model.C_bat[1]*1000)/(model.Ah*model.V))* sum(model.beta[n]*model.y[k,n,t] for n in model.N))

    # OBJECTIVE FUNCTION
    def rule_obj(mod):
        return sum(mod.P[t]*mod.w_buy[t] for t in mod.T) - sum(mod.S[t]*mod.w_sell[t] for t in mod.T) + sum(mod.d[k,t] for k in mod.K for t in mod.T) + sum(mod.U_price[l]*mod.u[l] for l in mod.L)
    model.obj = pyo.Objective(rule=rule_obj, sense=pyo.minimize)

    return model

def energy_consumption(data,dev,conserv):
    max_deviation = data['Energy consumption']['Maximum deviation (kWh/km*min)']
    max_deviation = max_deviation * dev * conserv
    gama = data['Energy consumption']['Uncertain energy (kWh/km*min)'] + max_deviation
    gama = gama.tolist()
    return gama

gama = energy_consumption(data,0,0)
model = createModel(data,gama)

## SOLVING LOCALY

#opt = pyo.SolverFactory('cplex_persistent',executable=EXEC_PATH)
#opt.set_instance(model)
#opt.solve()
#opt.set_instance(model)

# save the objective function values
#objective = []
#objective.append(model.obj())

## SOLVING IN NEOS SERVER

opt = pyo.SolverFactory('cplex',executable=EXEC_PATH)
instance = model.create_instance()
solver_manager = pyo.SolverManagerFactory('neos')  # Solve in neos server
solver_manager.solve(model, opt=opt, tee=True)

# save the objective function values
objective = []
objective.append(model.obj())

# iterate to vary the energy consumption
devs = [0.25,0.5,0.75,1]

for count, d in enumerate(devs):
    print ("\n===== iteration",count+1)
    print("deviation:",d*100,'%')
    conserv =[1] ## RESOLVER ISSO ##
    gama = energy_consumption(data,d,conserv)
    print(gama)
    model = createModel(data,gama)
    #opt.set_instance(model) # to solve using the local machine
    #opt.solve() # to solve using the local machine
    instance = model.create_instance() # to solve in NEOS server
    solver_manager.solve(model, opt=opt, tee=True) # to solve in NEOS server
    print("objective function:",model.obj())
    objective.append(model.obj())
