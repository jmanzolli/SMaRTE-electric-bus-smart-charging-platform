# CONSTRAINTS DEFINED

#constraint 2
def constraint2(model,k,t):
    return sum(model.b[k,i,t] for i in model.I) + model.c[k,t] <=1 
model.constraint2 = pyo.Constraint(model.K,model.T,rule=constraint2)

#constraint 3
def constraint3(model,i,t):
    for t in range(model.T_start[i],model.T_end[i]):
        return sum(model.b[k,i,t] for k in model.K) == 1
model.constraint3 = pyo.Constraint(model.I, model.T, rule=constraint3)

#constraint 4
def constraint4(model,i,k,t):
    for t in range(model.T_start[i],model.T_end[i]-1):
        return model.b[k,i,t+1] >= model.b[k,i,t]
model.constraint4 = pyo.Constraint(model.I,model.K, model.T, rule=constraint4)

#constraint 5
def constraint5(model,n,t):
    return sum(model.x[k,n,t] for k in model.K) + sum(model.y[k,n,t] for k in model.K) <= 1
model.constraint5 = pyo.Constraint(model.N,model.T,rule=constraint5)

#constraint 6
def constraint6(model,k,t):
    return sum(model.x[k,n,t] for n in model.N) + sum(model.y[k,n,t] for n in model.N) <= model.c[k,t]
model.constraint6 = pyo.Constraint(model.K,model.T,rule=constraint6)

#constraint 7
def constraint7(model,k,t):
    for t in range(2,T+1):
            return model.e[k,t] == model.e[k,t-1] + sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N) - sum(model.gama[i]*model.b[k,i,t] for i in model.I) - sum(model.dch_eff*model.beta[n]*model.y[k,n,t] for n in model.N)
model.constraint7 = pyo.Constraint(model.K,model.T,rule=constraint7)

#constraint 8.1
def constraint8_1(model,t):
    return sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) == model.w_buy[t]
model.constraint8_1 = pyo.Constraint(model.T,rule=constraint8_1)

#constraint 8.2
def constraint8_2(model,t):
    return sum(model.dch_eff*model.beta[n]*model.y[k,n,t] for n in model.N for k in model.K) == model.w_sell[t]
model.constraint8_2 = pyo.Constraint(model.T,rule=constraint8_2)

#constraint 9
def constraint9(model,l):
    return sum(model.u[l] for l in model.L)==1
model.constraint9 = pyo.Constraint(model.L,rule=constraint9)

#constraint 10
def constraint10(model,t):
    return sum(model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) <= sum(model.U_pow[l]*model.u[l] for l in model.L)
model.constraint10 = pyo.Constraint(model.T,rule=constraint10)
    
#constraint 11
def constraint11(model,t):
    return sum(model.alpha[n]*model.x[k,n,t] for n in model.N for k in model.K) + sum(model.beta[n]*model.y[k,n,t] for n in model.N for k in model.K) <= model.U_max
model.constraint11 = pyo.Constraint(model.T,rule=constraint11)

#constraint 12
def constraint12(model,k,t):
    return model.e[k,t] >= model.C_bat[k] * model.E_min
model.constraint12 = pyo.Constraint(model.K,model.T,rule=constraint12)

#constrait 13
def constraint13(model,k,t):
    return (model.E_max * model.C_bat[k]) >= model.e[k,t] + sum(model.ch_eff*model.alpha[n]*model.x[k,n,t] for n in model.N)
model.constraint13 = pyo.Constraint(model.K,model.T,rule=constraint13)         

#constraint 14.1
def constraint14_1(model,k):
    return model.e[k,1] == model.E_0*model.C_bat[k]
model.constraint14_1 = pyo.Constraint(model.K,rule=constraint14_1)

#constraint 14.2
def constraint14_2(model,k):
    return model.e[k,T]  >= model.E_end*model.C_bat[k]
model.constraint14_2 = pyo.Constraint(model.K,rule=constraint14_2) 

#constraint 15
def constraint15(model,k,t):
    return model.d[k,t] == ((model.R*model.C_bat[1]*1000)/(model.Ah*model.V))* sum(model.beta[n]*model.y[k,n,t] for n in model.N)
model.constraint15 = pyo.Constraint(model.K,model.T,rule=constraint15)