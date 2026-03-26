"""SMaRTE desktop GUI with file and manual dataset modes."""

from pathlib import Path
import datetime
import importlib.util
import os
import shutil
import sys

import pandas as pd
import PyQt6

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from optimization import check_solver, get_fleet_summary, plot, read_file, save_results, solveModel

_pyqt6_file = getattr(PyQt6, "__file__", None)
_QT_PLUGINS_DIR = Path(_pyqt6_file).resolve().parent / "Qt6" / "plugins" if _pyqt6_file else Path()
if _QT_PLUGINS_DIR.exists():
    os.environ["QT_PLUGIN_PATH"] = str(_QT_PLUGINS_DIR)
    platform_dir = _QT_PLUGINS_DIR / "platforms"
    if platform_dir.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_dir)


BG_DARK = "#2D2E32"
BG_MID = "#3C3D41"
BG_LIGHT = "#4A4B50"
BG_HEADER = "#1A1B1E"
FG = "#E8E9EB"
FG_DIM = "#9A9B9E"
ACCENT = "#4FC3F7"
SUCCESS = "#81C784"
WARNING = "#FFB74D"
ERROR = "#EF5350"
BORDER = "#555659"


def _parse_csv_numbers(raw, cast=float, field_name="field"):
    text = raw.strip()
    if not text:
        raise ValueError(f"'{field_name}' is required.")
    try:
        return [cast(item.strip()) for item in text.split(",") if item.strip()]
    except Exception as exc:
        raise ValueError(f"Invalid '{field_name}' values: {raw}") from exc


def _expand_or_validate(values, expected_len, field_name):
    if len(values) == expected_len:
        return values
    if len(values) == 1:
        return [values[0]] * expected_len
    raise ValueError(f"'{field_name}' must have 1 or {expected_len} values.")


def _pad_column(values, target_len):
    padded = list(values)
    while len(padded) < target_len:
        padded.append(float("nan"))
    return padded


def build_manual_data_bundle(cfg):
    t_horizon = int(cfg["t_horizon"])
    trip_begin = _parse_csv_numbers(cfg["trip_begin"], int, "Trip begin")
    trip_end = _parse_csv_numbers(cfg["trip_end"], int, "Trip end")
    bus_caps = _parse_csv_numbers(cfg["bus_caps"], float, "Bus capacities")
    chargers = _parse_csv_numbers(cfg["chargers"], float, "Charger powers")
    energy_cons = _parse_csv_numbers(cfg["energy_cons"], float, "Energy consumption")
    prices = _parse_csv_numbers(cfg["prices"], float, "Energy prices")

    if len(trip_begin) != len(trip_end):
        raise ValueError("Trip begin and Trip end must have the same number of values.")

    energy_cons = _expand_or_validate(energy_cons, len(trip_begin), "Energy consumption")
    prices = _expand_or_validate(prices, t_horizon, "Energy prices")

    if cfg["problem"] == "robust":
        robust_mult = 1.0 + float(cfg["robust_dev"]) * float(cfg["robust_conserv"])
        energy_cons = [v * robust_mult for v in energy_cons]

    size = max(
        len(trip_begin),
        len(bus_caps),
        len(chargers),
        len(prices),
        len(energy_cons),
    )
    dataset = pd.DataFrame(
        {
            "Trip (Begin)": _pad_column(trip_begin, size),
            "Trip (End)": _pad_column(trip_end, size),
            "Buses": _pad_column(bus_caps, size),
            "Charger": _pad_column(chargers, size),
            "Energy consumption": _pad_column(energy_cons, size),
            "Energy price": _pad_column(prices, size),
        }
    )

    if cfg["problem"] != "bilevel":
        return {"Dataset": dataset}

    selling_prices = [p * float(cfg["bilevel_sell_ratio"]) for p in prices]
    cap_prices = _expand_or_validate(
        _parse_csv_numbers(cfg["bilevel_cap_prices"], float, "Capacity prices"),
        t_horizon,
        "Capacity prices",
    )
    max_dev = _expand_or_validate(
        _parse_csv_numbers(cfg["bilevel_max_dev"], float, "Maximum deviations"),
        len(trip_begin),
        "Maximum deviations",
    )
    power_levels = _parse_csv_numbers(cfg["power_levels"], float, "Power levels")
    power_prices = _parse_csv_numbers(cfg["power_prices"], float, "Power tier prices")
    if len(power_levels) != len(power_prices):
        raise ValueError("Power levels and Power tier prices must have same length.")

    period_len = int(cfg["period_len"])
    if period_len <= 0:
        raise ValueError("Period length must be > 0.")

    period_rows = []
    start = 1
    p_idx = 1
    while start <= t_horizon:
        end = min(start + period_len, t_horizon + 1)
        period_rows.append({"Period": p_idx, "Begin": start, "End": end, "Len": end - start})
        p_idx += 1
        start = end

    p_count = len(period_rows)
    avg_prices = pd.DataFrame(
        {
            "Max price": [float(cfg["avg_max_price"])] * p_count,
            "Min price": [float(cfg["avg_min_price"])] * p_count,
            "Max cap": [float(cfg["avg_max_cap"])] * p_count,
            "Min cap": [float(cfg["avg_min_cap"])] * p_count,
        }
    )

    u_max = float(cfg["u_max"])
    trip_df = pd.DataFrame(
        {
            "Time begin (min)": trip_begin,
            "Time finish (min)": trip_end,
        }
    )
    chargers_df = pd.DataFrame(
        {
            "Charger (kWh/min)": chargers,
            "Max Power (kW)": [u_max] * len(chargers),
        }
    )
    return {
        "Trip time": trip_df,
        "Energy price": pd.DataFrame(
            {
                "Energy buying price (per minute)": prices,
                "Energy selling price (per minute)": selling_prices,
            }
        ),
        "Buses": pd.DataFrame({"Bus (kWh)": bus_caps}),
        "Chargers": chargers_df,
        "Power price": pd.DataFrame({"Power": power_levels, "Price": power_prices}),
        "Energy consumption": pd.DataFrame(
            {
                "Uncertain energy (kWh/km*min)": energy_cons,
                "Maximum deviation (kWh/km*min)": max_dev,
            }
        ),
        "Prices": pd.DataFrame(
            {
                "Spot Market": prices,
                "Capacity price": cap_prices,
            }
        ),
        "Periods": pd.DataFrame(period_rows),
        "Average prices": avg_prices,
    }


class SolverWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, data, problem, solver, time_limit, mip_gap, bilevel_script):
        super().__init__()
        self._data = data
        self._problem = problem
        self._solver = solver
        self._time_limit = time_limit
        self._mip_gap = mip_gap
        self._bilevel_script = bilevel_script

    def run(self):
        try:
            if self._problem in ("deterministic", "robust"):
                model = solveModel(
                    self._data,
                    time_limit=self._time_limit,
                    mipgap=self._mip_gap,
                    solver=self._solver,
                    log_callback=self.log.emit,
                )
                self.finished.emit({"kind": "single", "model": model})
                return

            self.log.emit("Loading bi-level module...")
            spec = importlib.util.spec_from_file_location("bilevelbus_runtime", str(self._bilevel_script))
            if spec is None or spec.loader is None:
                raise RuntimeError("Could not load BiLevelBus.py module.")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.log.emit("Running bi-level iterative solver...")
            lb, ub, model_ll, model_hrp = module.Solve(self._data)
            self.finished.emit(
                {
                    "kind": "bilevel",
                    "lb": lb,
                    "ub": ub,
                    "model_ll": model_ll,
                    "model_hrp": model_hrp,
                }
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class SMaRTEWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._data = None
        self._solving = False
        self._worker_thread = None
        self._worker = None
        self._result_kind = None
        self._model = None
        self._model_ll = None
        self._model_hrp = None

        self._bilevel_script = (
            Path(__file__).resolve().parent.parent
            / "Bi-level approach"
            / "Bi-level codes"
            / "build"
            / "BiLevelBus.py"
        )

        self.setWindowTitle("DRIVE-TECH - SMaRTE Electric Bus Smart Charging")
        self.resize(1200, 920)
        self.setMinimumSize(980, 760)

        self._build_ui()
        self._apply_styles()
        self._set_button_states(file_ready=False, solved=False)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_problem_section())
        layout.addWidget(self._build_file_section())
        layout.addWidget(self._build_manual_section())
        layout.addWidget(self._build_settings_section())
        layout.addWidget(self._build_actions_section())
        layout.addWidget(self._build_results_section())
        layout.addWidget(self._build_log_section(), 1)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("headerFrame")
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)

        stripe = QFrame()
        stripe.setObjectName("accentStripe")
        stripe.setFixedWidth(6)
        row.addWidget(stripe)

        text = QWidget()
        text_layout = QVBoxLayout(text)
        text_layout.setContentsMargins(14, 10, 10, 10)
        text_layout.setSpacing(2)
        title = QLabel("SMaRTE")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Deterministic, Robust and Bi-level optimization platform")
        subtitle.setObjectName("subtitleLabel")
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        row.addWidget(text, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.status_label)
        return frame

    def _build_problem_section(self):
        group = QGroupBox("Problem Setup")
        group.setObjectName("card")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("Problem:"), 0, 0)
        self.problem_box = QComboBox()
        self.problem_box.addItems(["deterministic", "robust", "bilevel"])
        self.problem_box.currentTextChanged.connect(self._on_problem_changed)
        grid.addWidget(self.problem_box, 0, 1)

        grid.addWidget(QLabel("Data source:"), 0, 2)
        self.source_box = QComboBox()
        self.source_box.addItems(["file", "manual"])
        self.source_box.currentTextChanged.connect(self._on_source_changed)
        grid.addWidget(self.source_box, 0, 3)
        grid.setColumnStretch(4, 1)
        return group

    def _build_file_section(self):
        group = QGroupBox("Input File")
        group.setObjectName("card")
        col = QVBoxLayout(group)
        row = QHBoxLayout()

        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        row.addWidget(self.file_path, 1)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_file)
        row.addWidget(self.btn_browse)
        col.addLayout(row)

        self.summary_label = QLabel("No file loaded.")
        self.summary_label.setObjectName("summaryLabel")
        col.addWidget(self.summary_label)
        return group

    def _build_manual_section(self):
        group = QGroupBox("Manual Dataset")
        group.setObjectName("card")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)

        self.manual_fields = {}

        def add_line(label, key, default, row, col):
            grid.addWidget(QLabel(label), row, col)
            edit = QLineEdit(default)
            self.manual_fields[key] = edit
            grid.addWidget(edit, row, col + 1)

        add_line("Horizon (timesteps)", "t_horizon", "96", 0, 0)
        add_line("Trip begin", "trip_begin", "1,25,49", 0, 2)
        add_line("Trip end", "trip_end", "24,48,72", 1, 0)
        add_line("Bus capacities (kWh)", "bus_caps", "240,240,240", 1, 2)
        add_line("Charger powers (kWh/min)", "chargers", "1.2,1.2", 2, 0)
        add_line("Energy consumption", "energy_cons", "0.8,0.9,0.85", 2, 2)
        add_line("Energy prices", "prices", "0.12", 3, 0)
        add_line("Max power U_max (kW)", "u_max", "250", 3, 2)

        add_line("Robust deviation", "robust_dev", "0.25", 4, 0)
        add_line("Robust conservatism", "robust_conserv", "1.0", 4, 2)

        add_line("Bi-level sell ratio", "bilevel_sell_ratio", "0.8", 5, 0)
        add_line("Bi-level cap prices", "bilevel_cap_prices", "0.02", 5, 2)
        add_line("Bi-level max deviations", "bilevel_max_dev", "0.10", 6, 0)
        add_line("Period length", "period_len", "24", 6, 2)
        add_line("Power tiers", "power_levels", "100,200,300", 7, 0)
        add_line("Power tier prices", "power_prices", "5,10,15", 7, 2)
        add_line("Avg min price", "avg_min_price", "0.05", 8, 0)
        add_line("Avg max price", "avg_max_price", "0.20", 8, 2)
        add_line("Avg min cap", "avg_min_cap", "0.01", 9, 0)
        add_line("Avg max cap", "avg_max_cap", "0.10", 9, 2)

        self.btn_build_manual = QPushButton("Build Manual Dataset")
        self.btn_build_manual.clicked.connect(self._build_manual_dataset)
        self.btn_build_manual.setObjectName("primaryButton")
        grid.addWidget(self.btn_build_manual, 10, 0, 1, 2)
        grid.setColumnStretch(4, 1)
        return group

    def _build_settings_section(self):
        group = QGroupBox("Solver Settings")
        group.setObjectName("card")
        row = QGridLayout(group)
        row.addWidget(QLabel("Solver:"), 0, 0)
        self.solver_box = QComboBox()
        self.solver_box.addItems(["gurobi", "cplex"])
        row.addWidget(self.solver_box, 0, 1)

        row.addWidget(QLabel("Time limit (s):"), 0, 2)
        self.time_limit = QSpinBox()
        self.time_limit.setRange(5, 86400)
        self.time_limit.setSingleStep(30)
        self.time_limit.setValue(60)
        row.addWidget(self.time_limit, 0, 3)

        row.addWidget(QLabel("MIP gap (%):"), 0, 4)
        self.mip_gap = QDoubleSpinBox()
        self.mip_gap.setRange(0.01, 10.0)
        self.mip_gap.setSingleStep(0.5)
        self.mip_gap.setDecimals(2)
        self.mip_gap.setValue(1.0)
        row.addWidget(self.mip_gap, 0, 5)
        row.setColumnStretch(6, 1)
        return group

    def _build_actions_section(self):
        box = QFrame()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)

        self.btn_solve = QPushButton("Solve")
        self.btn_solve.setObjectName("primaryButton")
        self.btn_solve.clicked.connect(self._on_solve)
        row.addWidget(self.btn_solve)

        self.btn_plot = QPushButton("Plot")
        self.btn_plot.clicked.connect(self._on_plot)
        row.addWidget(self.btn_plot)

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("successButton")
        self.btn_save.clicked.connect(self._on_save)
        row.addWidget(self.btn_save)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("dangerButton")
        self.btn_reset.clicked.connect(self._on_reset)
        row.addWidget(self.btn_reset)

        row.addSpacing(20)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        row.addWidget(self.progress)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("warnLabel")
        row.addWidget(self.progress_label)
        row.addStretch(1)
        return box

    def _build_results_section(self):
        group = QGroupBox("Results")
        group.setObjectName("card")
        grid = QGridLayout(group)

        self.result_labels = {}
        labels = ["Total Cost", "Energy Bought", "Solve Time", "Status"]
        for idx, name in enumerate(labels):
            t = QLabel(name)
            t.setObjectName("dimLabel")
            grid.addWidget(t, 0, idx)
            v = QLabel("-")
            v.setObjectName("valueLabel")
            grid.addWidget(v, 1, idx)
            self.result_labels[name] = v
        grid.setColumnStretch(4, 1)
        return group

    def _build_log_section(self):
        group = QGroupBox("Terminal")
        group.setObjectName("card")
        col = QVBoxLayout(group)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_box.setFont(QFont("Menlo", 10))
        col.addWidget(self.log_box)
        return group

    def _apply_styles(self):
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {BG_DARK}; color: {FG};
                font-family: "Helvetica Neue", "Segoe UI", sans-serif;
                font-size: 12px;
            }}
            #headerFrame {{ background-color: {BG_HEADER}; border: 1px solid {BORDER}; border-radius: 8px; }}
            #accentStripe {{ background-color: {ACCENT}; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
            #titleLabel {{ font-size: 22px; font-weight: 700; color: {FG}; }}
            #subtitleLabel {{ color: {FG_DIM}; font-size: 11px; }}
            #statusLabel {{ color: {FG_DIM}; font-size: 11px; padding-right: 14px; }}
            QGroupBox#card {{
                background-color: {BG_MID}; border: 1px solid {BORDER};
                border-radius: 8px; margin-top: 8px; font-weight: 600; color: {FG_DIM};
            }}
            QGroupBox#card::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
                background-color: {BG_LIGHT}; border: 1px solid {BORDER}; border-radius: 6px;
                color: {FG}; padding: 6px; selection-background-color: {ACCENT};
            }}
            QPushButton {{
                background-color: {BG_LIGHT}; border: 1px solid {BORDER}; border-radius: 6px;
                padding: 6px 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #5A5B60; }}
            QPushButton:disabled {{ color: {BORDER}; }}
            QPushButton#primaryButton {{ background-color: {ACCENT}; color: #1A1B1E; border-color: {ACCENT}; }}
            QPushButton#successButton {{ background-color: {SUCCESS}; color: #1A1B1E; border-color: {SUCCESS}; }}
            QPushButton#dangerButton {{ background-color: {ERROR}; color: {FG}; border-color: {ERROR}; }}
            #summaryLabel {{ color: {ACCENT}; font-size: 11px; }}
            #dimLabel {{ color: {FG_DIM}; }}
            #valueLabel {{ color: {SUCCESS}; font-weight: 700; font-size: 13px; }}
            #warnLabel {{ color: {WARNING}; }}
            QProgressBar {{ border: 1px solid {BORDER}; border-radius: 4px; background-color: {BG_LIGHT}; }}
            QProgressBar::chunk {{ background-color: {ACCENT}; }}
            """
        )

    def _set_status(self, text, color=FG_DIM):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def _log_line(self, message):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{ts}] {message}")

    def _clear_results(self):
        for val in self.result_labels.values():
            val.setText("-")

    def _set_button_states(self, file_ready, solved):
        self.btn_solve.setEnabled(file_ready and not self._solving)
        self.btn_plot.setEnabled(solved)
        self.btn_save.setEnabled(solved)
        self.btn_reset.setEnabled(not self._solving)

    def _on_problem_changed(self, _):
        is_bilevel = self.problem_box.currentText() == "bilevel"
        self.solver_box.setEnabled(not is_bilevel)
        if is_bilevel:
            self._log_line("Bi-level selected: internal solver settings from BiLevelBus.py will be used.")

    def _on_source_changed(self, _):
        use_file = self.source_box.currentText() == "file"
        self.btn_browse.setEnabled(use_file)
        self.btn_build_manual.setEnabled(not use_file)
        if use_file:
            self.summary_label.setText("No file loaded.")
            self._data = None
            self._set_button_states(file_ready=False, solved=False)
        else:
            self.summary_label.setText("Manual mode enabled. Click 'Build Manual Dataset'.")
            self._data = None
            self._set_button_states(file_ready=False, solved=False)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select input workbook", "", "Excel files (*.xlsx *.xls)")
        if not path:
            return
        self.file_path.setText(path)
        self._log_line(f"Loading file: {Path(path).name}")
        try:
            self._data = read_file(path)
            summary = get_fleet_summary(self._data)
            if summary:
                txt = (
                    f"{summary['buses']} bus(es) | {summary['chargers']} charger(s) | "
                    f"{summary['trips']} trip(s) | {summary['timesteps']} timesteps"
                )
                self.summary_label.setText(txt)
            else:
                self.summary_label.setText("File loaded. Summary unavailable for this format.")
            self._set_status("File loaded", SUCCESS)
            self._set_button_states(file_ready=True, solved=False)
            self._clear_results()
        except Exception as exc:
            self._data = None
            self.summary_label.setText("Error reading file.")
            self._set_status("Error", ERROR)
            self._log_line(f"File read error: {exc}")

    def _manual_config(self):
        cfg = {k: w.text() for k, w in self.manual_fields.items()}
        cfg["problem"] = self.problem_box.currentText()
        return cfg

    def _build_manual_dataset(self):
        try:
            self._data = build_manual_data_bundle(self._manual_config())
            if "Dataset" in self._data:
                summary = get_fleet_summary(self._data)
                txt = (
                    f"Manual dataset ready: {summary.get('buses', 0)} buses | "
                    f"{summary.get('chargers', 0)} chargers | "
                    f"{summary.get('trips', 0)} trips | {summary.get('timesteps', 0)} timesteps"
                )
            else:
                txt = "Manual bi-level dataset ready."
            self.summary_label.setText(txt)
            self._set_status("Manual data ready", SUCCESS)
            self._log_line(txt)
            self._set_button_states(file_ready=True, solved=False)
            self._clear_results()
        except Exception as exc:
            self._data = None
            self._set_status("Manual data error", ERROR)
            self._log_line(f"Manual data build error: {exc}")
            QMessageBox.critical(self, "Manual data error", str(exc))

    def _on_solve(self):
        if self._data is None:
            QMessageBox.warning(self, "No dataset", "Load a file or build a manual dataset first.")
            return

        problem = self.problem_box.currentText()
        solver = self.solver_box.currentText()
        tlimit = int(self.time_limit.value())
        mgap = float(self.mip_gap.value()) / 100.0

        if problem in ("deterministic", "robust") and not check_solver(solver):
            QMessageBox.critical(self, "Solver unavailable", f"Solver '{solver}' is not available.")
            return

        if problem == "bilevel" and not self._bilevel_script.exists():
            QMessageBox.critical(self, "Missing file", f"Could not find {self._bilevel_script}.")
            return

        self._model = None
        self._model_ll = None
        self._model_hrp = None
        self._result_kind = None
        self._solving = True
        self._clear_results()
        self._set_status("Solving...", WARNING)
        self.progress.setRange(0, 0)
        self.progress_label.setText("Solving...")
        self._set_button_states(file_ready=True, solved=False)
        self._log_line(f"Running {problem} problem...")

        self._worker_thread = QThread(self)
        self._worker = SolverWorker(self._data, problem, solver, tlimit, mgap, self._bilevel_script)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.log.connect(self._log_line)
        self._worker.finished.connect(self._on_solve_done)
        self._worker.failed.connect(self._on_solve_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.failed.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _cleanup_worker(self, *_):
        if self._worker_thread is not None:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread.deleteLater()
            self._worker_thread = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _on_solve_done(self, payload):
        self._solving = False
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")

        if payload["kind"] == "single":
            self._result_kind = "single"
            self._model = payload["model"]
            obj = self._model.obj()
            solve_time = getattr(self._model, "_solve_time", 0.0)
            term = getattr(self._model, "_termination", "unknown")
            energy = getattr(self._model, "_total_energy_kwh", 0.0)
            is_ok = ("optimal" in term.lower()) or ("feasible" in term.lower())
            self._set_status(f"Solved ({term})", SUCCESS if is_ok else WARNING)
            self.result_labels["Total Cost"].setText(f"{obj:.4f}")
            self.result_labels["Energy Bought"].setText(f"{energy:.1f} kWh")
            self.result_labels["Solve Time"].setText(f"{solve_time:.1f} s")
            self.result_labels["Status"].setText(term.capitalize())
            self._log_line(f"Solved. Cost={obj:.4f} Energy={energy:.1f}kWh Time={solve_time:.1f}s")
            self._set_button_states(file_ready=True, solved=True)
            return

        self._result_kind = "bilevel"
        self._model_ll = payload["model_ll"]
        self._model_hrp = payload["model_hrp"]
        lb = float(payload["lb"])
        ub = float(payload["ub"])
        self._set_status("Bi-level solved", SUCCESS)
        self.result_labels["Total Cost"].setText(f"UB {ub:.4f}")
        self.result_labels["Energy Bought"].setText("See plot/save")
        self.result_labels["Solve Time"].setText("n/a")
        self.result_labels["Status"].setText(f"LB {lb:.4f}")
        self._log_line(f"Bi-level solved. LB={lb:.4f} UB={ub:.4f}")
        self._set_button_states(file_ready=True, solved=True)

    def _on_solve_error(self, message):
        self._solving = False
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")
        self._set_status("Error", ERROR)
        self._set_button_states(file_ready=self._data is not None, solved=False)
        self._log_line(f"Solve error: {message}")
        QMessageBox.critical(self, "Solve error", message)

    def _load_bilevel_module(self):
        spec = importlib.util.spec_from_file_location("bilevelbus_ui", str(self._bilevel_script))
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load BiLevelBus.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _on_plot(self):
        try:
            if self._result_kind == "single" and self._model is not None:
                plot(self._model)
                return
            if self._result_kind == "bilevel" and self._model_ll is not None and self._model_hrp is not None:
                module = self._load_bilevel_module()
                module.plot(self._model_ll, self._model_hrp)
                return
            QMessageBox.information(self, "No result", "Run a model first.")
        except Exception as exc:
            self._log_line(f"Plot error: {exc}")
            QMessageBox.critical(self, "Plot error", str(exc))

    def _on_save(self):
        if self._result_kind is None:
            QMessageBox.information(self, "No result", "Run a model first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save results", "output.xlsx", "Excel workbook (*.xlsx)")
        if not path:
            return
        try:
            if self._result_kind == "single":
                out = save_results(self._model, output_path=path)
                self._log_line(f"Results saved -> {out}")
                return

            module = self._load_bilevel_module()
            module.save_output(self._model_ll, self._model_hrp)
            generated = Path.cwd() / "output_data.xlsx"
            if not generated.exists():
                raise RuntimeError("Bi-level output file was not generated.")
            shutil.copy2(generated, path)
            self._log_line(f"Bi-level results saved -> {path}")
        except Exception as exc:
            self._log_line(f"Save error: {exc}")
            QMessageBox.critical(self, "Save error", str(exc))

    def _on_reset(self):
        self._data = None
        self._result_kind = None
        self._model = None
        self._model_ll = None
        self._model_hrp = None
        self._solving = False
        self.file_path.clear()
        self.summary_label.setText("No file loaded.")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")
        self._set_status("Ready", FG_DIM)
        self._clear_results()
        self._set_button_states(file_ready=False, solved=False)
        self._log_line("Reset.")


def main():
    app = QApplication(sys.argv)
    window = SMaRTEWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

