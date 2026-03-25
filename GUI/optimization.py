import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import time
from pathlib import Path

# Results directory relative to this file (GUI/ -> project root / Results/)
_RESULTS_DIR = Path(__file__).parent.parent / "Results"


def read_file(input_path):
    data = pd.read_excel(input_path, None)
    return data


def get_fleet_summary(data):
    """Return a dict with fleet stats from the loaded Dataset sheet."""
    try:
        T_start = [x for x in data['Dataset']['Trip (Begin)'].tolist() if str(x) != 'nan']
        C_bat   = [x for x in data['Dataset']['Buses'].tolist()         if str(x) != 'nan']
        alpha   = [x for x in data['Dataset']['Charger'].tolist()       if str(x) != 'nan']
        Price   = [x for x in data['Dataset']['Energy price'].tolist()  if str(x) != 'nan']
        return {
            'trips':      len(T_start),
            'buses':      len(C_bat),
            'chargers':   len(alpha),
            'timesteps':  len(Price),
        }
    except Exception:
        return {}


def check_solver(solver_name):
    """Return True if the named solver is available on this system."""
    return pyo.SolverFactory(solver_name).available()


def setData(data, d_off=4, d_on=1, ch_eff=0.90, E_0=0.2, E_min=0.2, E_max=1, E_end=0.2):
    T_start = [x for x in data['Dataset']['Trip (Begin)'].tolist() if str(x) != 'nan']
    T_start = [int(x) for x in T_start]
    T_end   = [x for x in data['Dataset']['Trip (End)'].tolist()   if str(x) != 'nan']
    T_end   = [int(x) for x in T_end]
    alpha   = [x for x in data['Dataset']['Charger'].tolist()      if str(x) != 'nan']
    gama    = data['Dataset']['Energy consumption'].tolist()[0]
    Price   = data['Dataset']['Energy price'].tolist()
    C_bat   = [x for x in data['Dataset']['Buses'].tolist()        if str(x) != 'nan']
    t = len(Price)
    k = len(C_bat)
    n = len(alpha)
    T = len(Price)
    i = len(T_start)
    return T_start, T_end, alpha, ch_eff, gama, Price, E_0, E_min, E_max, E_end, C_bat, d_off, d_on, t, k, n, T, i


def solveModel(data, time_limit=60, mipgap=0.01, solver='gurobi',
               log_callback=None, status=False):
    """
    Build and solve the charging optimisation model.

    Parameters
    ----------
    data         : dict of DataFrames from read_file()
    time_limit   : solver wall-clock time limit in seconds
    mipgap       : relative MIP optimality gap tolerance
    solver       : 'gurobi' or 'cplex'
    log_callback : callable(str) invoked with progress messages
    status       : if True, pipe full solver log to stdout

    Returns
    -------
    Solved Pyomo ConcreteModel with extra attributes:
        _solve_time       – elapsed seconds
        _termination      – solver termination condition string
        _total_energy_kwh – total energy purchased (kWh)
    """

    def _log(msg):
        if log_callback:
            log_callback(msg)

    T_start, T_end, alpha, ch_eff, gama, P, E_0, E_min, E_max, E_end, \
        C_bat, d_off, d_on, t, k, n, T, i = setData(data)

    opt = pyo.SolverFactory(solver)
    if not opt.available():
        raise RuntimeError(
            f"Solver '{solver}' is not available on this system.\n"
            "Install Gurobi (gurobipy) or IBM CPLEX and ensure a valid licence."
        )

    _log(f"Building model: {k} bus(es), {n} charger(s), {i} trip(s), {T} timesteps")

    model = pyo.ConcreteModel()

    model.I = pyo.RangeSet(i)
    model.T = pyo.RangeSet(t)
    model.K = pyo.RangeSet(k)
    model.N = pyo.RangeSet(n)

    model.T_start = pyo.Param(model.I, initialize=lambda m, i: T_start[i - 1])
    model.T_end   = pyo.Param(model.I, initialize=lambda m, i: T_end[i - 1])
    model.alpha   = pyo.Param(model.N, initialize=lambda m, n: alpha[n - 1])
    model.ch_eff  = pyo.Param(initialize=ch_eff)
    model.gama    = pyo.Param(initialize=gama)
    model.P       = pyo.Param(model.T, initialize=lambda m, t: P[t - 1])
    model.E_0     = pyo.Param(initialize=E_0)
    model.E_min   = pyo.Param(initialize=E_min)
    model.E_max   = pyo.Param(initialize=E_max)
    model.E_end   = pyo.Param(initialize=E_end)
    model.C_bat   = pyo.Param(model.K, initialize=lambda m, k: C_bat[k - 1])

    model.b     = pyo.Var(model.K, model.I, model.T, within=pyo.Binary)
    model.x     = pyo.Var(model.K, model.N, model.T, domain=pyo.Binary)
    model.c     = pyo.Var(model.K, model.T, domain=pyo.Binary)
    model.e     = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals)
    model.w_buy = pyo.Var(model.T, within=pyo.NonNegativeReals)

    def rule_obj(mod):
        return sum(mod.P[t] * mod.w_buy[t] for t in mod.T)
    model.obj = pyo.Objective(rule=rule_obj, sense=pyo.minimize)

    model.constraints = pyo.ConstraintList()

    for kk in model.K:
        for tt in model.T:
            model.constraints.add(
                sum(model.b[kk, ii, tt] for ii in model.I) + model.c[kk, tt] <= 1)
            model.constraints.add(
                sum(model.x[kk, nn, tt] for nn in model.N) <= model.c[kk, tt])

    for nn in model.N:
        for tt in model.T:
            model.constraints.add(sum(model.x[kk, nn, tt] for kk in model.K) <= 1)

    for ii in model.I:
        for tt in range(model.T_start[ii], model.T_end[ii]):
            model.constraints.add(sum(model.b[kk, ii, tt] for kk in model.K) == 1)
        for tt in range(1, model.T_start[ii]):
            model.constraints.add(sum(model.b[kk, ii, tt] for kk in model.K) == 0)
        for tt in range(model.T_end[ii], T + 1):
            model.constraints.add(sum(model.b[kk, ii, tt] for kk in model.K) == 0)

    for ii in model.I:
        for kk in model.K:
            for tt in range(model.T_start[ii], model.T_end[ii] - 1):
                model.constraints.add(model.b[kk, ii, tt + 1] >= model.b[kk, ii, tt])

    for kk in model.K:
        for tt in range(2, T + 1):
            model.constraints.add(
                model.e[kk, tt] == model.e[kk, tt - 1]
                + sum(model.ch_eff * model.alpha[nn] * model.x[kk, nn, tt] for nn in model.N)
                - sum(model.gama * model.b[kk, ii, tt] for ii in model.I))

    for tt in model.T:
        model.constraints.add(
            sum(model.ch_eff * model.alpha[nn] * model.x[kk, nn, tt]
                for nn in model.N for kk in model.K) == model.w_buy[tt])

    for kk in model.K:
        for nn in model.N:
            for tt in range(2, T - d_off):
                model.constraints.add(
                    1 - model.x[kk, nn, tt] + model.x[kk, nn, tt - 1]
                    + ((1 / d_off) * sum(model.x[kk, nn, j] for j in range(tt, tt + d_off))) <= 2)
            for tt in range(T - d_off + 1, T):
                model.constraints.add(
                    1 - model.x[kk, nn, tt] + model.x[kk, nn, tt - 1]
                    + ((1 / (T - tt + 1)) * sum(model.x[kk, nn, j] for j in range(tt, T))) <= 2)
            for tt in range(2, T - d_on):
                model.constraints.add(
                    1 - model.x[kk, nn, tt] + model.x[kk, nn, tt - 1]
                    + ((1 / d_on) * sum(model.x[kk, nn, j] for j in range(tt, tt + d_on))) >= 1)
            for tt in range(T - d_on + 1, T):
                model.constraints.add(
                    1 - model.x[kk, nn, tt] + model.x[kk, nn, tt - 1]
                    + ((1 / (T - tt + 1)) * sum(model.x[kk, nn, j] for j in range(tt, T))) >= 1)

    for kk in model.K:
        for tt in model.T:
            model.constraints.add(model.e[kk, tt] >= model.C_bat[kk] * model.E_min)
            model.constraints.add(E_max * model.C_bat[kk] >= model.e[kk, tt])
        model.constraints.add(model.e[kk, 1] == model.E_0 * model.C_bat[kk])
        model.constraints.add(model.e[kk, T] >= model.E_end * model.C_bat[kk])

    if time_limit:
        opt.options['timelimit'] = time_limit
    if mipgap:
        opt.options['mipgap'] = mipgap

    _log(f"Solving with {solver} (time limit: {time_limit}s, MIP gap: {mipgap*100:.0f}%)...")
    t0 = time.time()
    results_obj = opt.solve(model, tee=status)
    solve_time = time.time() - t0

    termination = str(results_obj.solver.termination_condition)
    total_energy = sum(pyo.value(model.w_buy[tt]) * 4 for tt in model.T)  # convert to kWh (×4 for 15-min slots)

    model._solve_time       = solve_time
    model._termination      = termination
    model._total_energy_kwh = total_energy

    _log(f"Done in {solve_time:.1f}s — Termination: {termination} — Obj: {model.obj():.4f}")
    return model


def energy_bus(K, T, e, C_bat):
    """
    Return (Energy [kWh], Energy_perc [%]) DataFrames.

    Fixes the original bug where every column was divided by the last
    bus's capacity instead of its own.
    """
    bus_labels = [f'Bus {k}' for k in K]
    energy_vals = [[pyo.value(e[k, t]) for k in K] for t in T]
    Energy = pd.DataFrame(energy_vals, index=list(T), columns=bus_labels)
    cap    = {k: pyo.value(C_bat[k]) for k in K}
    Energy_perc = pd.DataFrame(
        {f'Bus {k}': Energy[f'Bus {k}'] * 100.0 / cap[k] for k in K}
    )
    return Energy, Energy_perc


def power(T, w):
    W = pd.DataFrame(
        [pyo.value(w[t]) for t in T],
        index=list(T),
        columns=['Power']
    )
    return W


def save_results(model, output_path=None):
    """
    Save optimisation results to an Excel workbook.

    If output_path is None the file is written to <project_root>/Results/output.xlsx.
    Returns the Path that was written.
    """
    if output_path is None:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _RESULTS_DIR / "output.xlsx"

    Energy, Energy_perc = energy_bus(model.K, model.T, model.e, model.C_bat)
    Power = power(model.T, model.w_buy) * 4
    Obj   = pd.DataFrame({'Objective Value': [model.obj()]})

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        Energy.to_excel(writer,      sheet_name='Energy')
        Energy_perc.to_excel(writer, sheet_name='SOC')
        Power.to_excel(writer,       sheet_name='Power')
        Obj.to_excel(writer,         sheet_name='Optimal value')

    return Path(output_path)


def plot(model):
    """Plot bus SOC profiles and grid power demand in a styled figure."""
    Energy, Energy_perc = energy_bus(model.K, model.T, model.e, model.C_bat)
    Power = power(model.T, model.w_buy) * 4

    BG_DARK = '#2D2E32'
    BG_MID  = '#3C3D41'
    FG      = '#E8E9EB'
    GRID_C  = '#555659'

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 10), facecolor=BG_DARK)
    fig.suptitle('SMaRTE — Optimised Charging Schedule', color=FG,
                 fontsize=14, fontweight='bold', y=0.98)

    for ax in (ax1, ax2):
        ax.set_facecolor(BG_MID)
        ax.tick_params(colors=FG, labelsize=9)
        ax.xaxis.label.set_color(FG)
        ax.yaxis.label.set_color(FG)
        ax.title.set_color(FG)
        ax.grid(True, color=GRID_C, linewidth=0.5, linestyle='--')
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_C)

    Energy_perc.plot(ax=ax1, linewidth=1.8)
    ax1.axhline(y=20, color='#EF5350', linestyle='--', linewidth=1.0, label='SOC min (20%)')
    ax1.set_xlabel('Timestep [min]')
    ax1.set_ylabel('State of Charge [%]')
    ax1.set_title('Bus State of Charge Over Time')
    ax1.set_ylim(0, 105)
    leg1 = ax1.legend(facecolor='#4A4B50', labelcolor=FG, fontsize=8)

    Power.plot(ax=ax2, color='#4FC3F7', linewidth=1.8, legend=False)
    ax2.fill_between(Power.index, Power['Power'], alpha=0.15, color='#4FC3F7')
    ax2.set_xlabel('Timestep [min]')
    ax2.set_ylabel('Power [kW]')
    ax2.set_title('Grid Charging Power Over Time')

    plt.tight_layout(pad=2.5)
    plt.show()