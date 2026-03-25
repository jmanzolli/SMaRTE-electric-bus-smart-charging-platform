"""SMaRTE - DRIVE-TECH Electric Bus Smart Charging Platform (PyQt6 GUI)."""

from pathlib import Path
import datetime
import os
import sys

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

from optimization import (
    check_solver,
    get_fleet_summary,
    plot,
    read_file,
    save_results,
    solveModel,
)

# Force Qt to use the plugin folder bundled with pip-installed PyQt6.
_QT_PLUGINS_DIR = Path(PyQt6.__file__).resolve().parent / "Qt6" / "plugins"
if _QT_PLUGINS_DIR.exists():
    os.environ["QT_PLUGIN_PATH"] = str(_QT_PLUGINS_DIR)
    _platform_dir = _QT_PLUGINS_DIR / "platforms"
    if _platform_dir.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(_platform_dir)


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


class SolverWorker(QObject):
    """Run model optimization on a background Qt thread."""

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, data, solver, time_limit, mip_gap):
        super().__init__()
        self._data = data
        self._solver = solver
        self._time_limit = time_limit
        self._mip_gap = mip_gap

    def run(self):
        try:
            model = solveModel(
                self._data,
                time_limit=self._time_limit,
                mipgap=self._mip_gap,
                solver=self._solver,
                log_callback=self.log.emit,
            )
            self.finished.emit(model)
        except Exception as exc:
            self.failed.emit(str(exc))


class SMaRTEWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._data = None
        self._model = None
        self._solving = False
        self._worker_thread = None
        self._worker = None

        self.setWindowTitle("DRIVE-TECH - SMaRTE Electric Bus Smart Charging")
        self.resize(980, 820)
        self.setMinimumSize(860, 700)

        self._build_ui()
        self._apply_styles()
        self._set_button_states(file_loaded=False, solved=False)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        header = self._build_header()
        main_layout.addWidget(header)

        main_layout.addWidget(self._build_file_section())
        main_layout.addWidget(self._build_settings_section())
        main_layout.addWidget(self._build_actions_section())
        main_layout.addWidget(self._build_results_section())
        main_layout.addWidget(self._build_log_section(), 1)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        stripe = QFrame()
        stripe.setObjectName("accentStripe")
        stripe.setFixedWidth(6)
        layout.addWidget(stripe)

        text_wrap = QWidget()
        text_layout = QVBoxLayout(text_wrap)
        text_layout.setContentsMargins(14, 10, 10, 10)
        text_layout.setSpacing(2)

        title = QLabel("SMaRTE")
        title.setObjectName("titleLabel")
        subtitle = QLabel("DRIVE-TECH  |  Electric Bus Smart Charging Platform")
        subtitle.setObjectName("subtitleLabel")
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addWidget(text_wrap, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_label)

        return frame

    def _build_file_section(self):
        group = QGroupBox("Input File")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        top = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        top.addWidget(self.file_path, 1)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_file)
        top.addWidget(self.btn_browse)
        layout.addLayout(top)

        self.summary_label = QLabel("No file loaded.")
        self.summary_label.setObjectName("summaryLabel")
        layout.addWidget(self.summary_label)

        return group

    def _build_settings_section(self):
        group = QGroupBox("Solver Settings")
        group.setObjectName("card")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(12)

        layout.addWidget(QLabel("Solver:"), 0, 0)
        self.solver_box = QComboBox()
        self.solver_box.addItems(["gurobi", "cplex"])
        layout.addWidget(self.solver_box, 0, 1)

        layout.addWidget(QLabel("Time limit (s):"), 0, 2)
        self.time_limit = QSpinBox()
        self.time_limit.setRange(5, 86400)
        self.time_limit.setSingleStep(30)
        self.time_limit.setValue(60)
        layout.addWidget(self.time_limit, 0, 3)

        layout.addWidget(QLabel("MIP gap (%):"), 0, 4)
        self.mip_gap = QDoubleSpinBox()
        self.mip_gap.setRange(0.01, 10.0)
        self.mip_gap.setSingleStep(0.5)
        self.mip_gap.setDecimals(2)
        self.mip_gap.setValue(1.0)
        layout.addWidget(self.mip_gap, 0, 5)

        layout.setColumnStretch(6, 1)
        return group

    def _build_actions_section(self):
        box = QFrame()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_solve = QPushButton("Solve")
        self.btn_solve.setObjectName("primaryButton")
        self.btn_solve.clicked.connect(self._on_solve)
        layout.addWidget(self.btn_solve)

        self.btn_plot = QPushButton("Plot")
        self.btn_plot.clicked.connect(self._on_plot)
        layout.addWidget(self.btn_plot)

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("successButton")
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("dangerButton")
        self.btn_reset.clicked.connect(self._on_reset)
        layout.addWidget(self.btn_reset)

        layout.addSpacing(20)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("warnLabel")
        layout.addWidget(self.progress_label)

        layout.addStretch(1)
        return box

    def _build_results_section(self):
        group = QGroupBox("Results")
        group.setObjectName("card")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(24)

        self.result_labels = {}
        fields = ["Total Cost", "Energy Bought", "Solve Time", "Status"]

        for idx, name in enumerate(fields):
            label_title = QLabel(name)
            label_title.setObjectName("dimLabel")
            layout.addWidget(label_title, 0, idx)

            value = QLabel("-")
            value.setObjectName("valueLabel")
            layout.addWidget(value, 1, idx)
            self.result_labels[name] = value

        layout.setColumnStretch(4, 1)
        return group

    def _build_log_section(self):
        group = QGroupBox("Terminal")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_box.setFont(QFont("Menlo", 10))
        layout.addWidget(self.log_box)

        return group

    def _apply_styles(self):
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {BG_DARK};
                color: {FG};
                font-family: "Helvetica Neue", "Segoe UI", sans-serif;
                font-size: 12px;
            }}
            #headerFrame {{
                background-color: {BG_HEADER};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
            #accentStripe {{
                background-color: {ACCENT};
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }}
            #titleLabel {{
                font-size: 22px;
                font-weight: 700;
                color: {FG};
            }}
            #subtitleLabel {{
                color: {FG_DIM};
                font-size: 11px;
            }}
            #statusLabel {{
                color: {FG_DIM};
                font-size: 11px;
                padding-right: 14px;
            }}
            QGroupBox#card {{
                background-color: {BG_MID};
                border: 1px solid {BORDER};
                border-radius: 8px;
                margin-top: 8px;
                font-weight: 600;
                color: {FG_DIM};
            }}
            QGroupBox#card::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
                background-color: {BG_LIGHT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {FG};
                padding: 6px;
                selection-background-color: {ACCENT};
            }}
            QPushButton {{
                background-color: {BG_LIGHT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #5A5B60;
            }}
            QPushButton:disabled {{
                color: {BORDER};
            }}
            QPushButton#primaryButton {{
                background-color: {ACCENT};
                color: #1A1B1E;
                border-color: {ACCENT};
            }}
            QPushButton#successButton {{
                background-color: {SUCCESS};
                color: #1A1B1E;
                border-color: {SUCCESS};
            }}
            QPushButton#dangerButton {{
                background-color: {ERROR};
                color: {FG};
                border-color: {ERROR};
            }}
            #summaryLabel {{
                color: {ACCENT};
                font-size: 11px;
            }}
            #dimLabel {{
                color: {FG_DIM};
            }}
            #valueLabel {{
                color: {SUCCESS};
                font-weight: 700;
                font-size: 13px;
            }}
            #warnLabel {{
                color: {WARNING};
            }}
            QProgressBar {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                background-color: {BG_LIGHT};
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
            }}
            """
        )

    def _set_status(self, text, color=FG_DIM):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def _log_line(self, message, level="info"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{timestamp}] {message}")

    def _set_button_states(self, file_loaded, solved):
        self.btn_solve.setEnabled(file_loaded and not self._solving)
        self.btn_plot.setEnabled(solved)
        self.btn_save.setEnabled(solved)
        self.btn_reset.setEnabled(not self._solving)

    def _clear_results(self):
        for value in self.result_labels.values():
            value.setText("-")

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select input workbook",
            "",
            "Excel files (*.xlsx *.xls);;All files (*.*)",
        )
        if not path:
            return

        self.file_path.setText(path)
        self._log_line(f"Loading: {Path(path).name}", "accent")

        try:
            self._data = read_file(path)
            summary = get_fleet_summary(self._data)
            if summary:
                text = (
                    f"{summary['buses']} bus(es)  |  {summary['chargers']} charger(s)  |  "
                    f"{summary['trips']} trip(s)  |  {summary['timesteps']} timesteps"
                )
                self.summary_label.setText(text)
                self._log_line(f"Fleet summary: {text}", "success")
                self._set_status("File loaded", SUCCESS)
            else:
                self.summary_label.setText("File loaded - could not parse fleet summary.")
                self._log_line("File loaded (summary unavailable).", "warning")
                self._set_status("File loaded", WARNING)
        except Exception as exc:
            self._data = None
            self.summary_label.setText("Error reading file - see terminal.")
            self._log_line(f"Error reading file: {exc}", "error")
            self._set_status("Error", ERROR)

        self._model = None
        self._clear_results()
        self._set_button_states(file_loaded=self._data is not None, solved=False)

    def _on_solve(self):
        if self._data is None:
            QMessageBox.warning(self, "No file", "Please browse and load an input file first.")
            return

        solver = self.solver_box.currentText()
        time_limit = int(self.time_limit.value())
        mip_gap = float(self.mip_gap.value()) / 100.0

        if not check_solver(solver):
            self._log_line(
                f"Solver '{solver}' not found. Install it or switch solver.",
                "error",
            )
            QMessageBox.critical(
                self,
                "Solver unavailable",
                (
                    f"'{solver}' is not available on this system.\n"
                    "Install Gurobi (gurobipy) or IBM CPLEX, or select a different solver."
                ),
            )
            return

        self._model = None
        self._solving = True
        self._clear_results()
        self._set_status("Solving...", WARNING)
        self.progress.setRange(0, 0)
        self.progress_label.setText("Solving...")
        self._set_button_states(file_loaded=True, solved=False)
        self._log_line(
            f"Starting solver: {solver} | time limit: {time_limit}s | MIP gap: {mip_gap*100:.1f}%",
            "accent",
        )

        self._worker_thread = QThread(self)
        self._worker = SolverWorker(self._data, solver, time_limit, mip_gap)
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

    def _on_solve_done(self, model):
        self._model = model
        self._solving = False
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")

        obj = model.obj()
        solve_time = getattr(model, "_solve_time", 0)
        term = getattr(model, "_termination", "unknown")
        energy = getattr(model, "_total_energy_kwh", 0)

        is_ok = ("optimal" in term.lower()) or ("feasible" in term.lower())
        self._set_status(f"Solved ({term})", SUCCESS if is_ok else WARNING)
        self._set_button_states(file_loaded=True, solved=True)

        self.result_labels["Total Cost"].setText(f"{obj:.4f}")
        self.result_labels["Energy Bought"].setText(f"{energy:.1f} kWh")
        self.result_labels["Solve Time"].setText(f"{solve_time:.1f} s")
        self.result_labels["Status"].setText(term.capitalize())

        self._log_line(
            (
                f"Solution: cost = {obj:.4f} | energy = {energy:.1f} kWh | "
                f"time = {solve_time:.1f}s | {term}"
            ),
            "success" if is_ok else "warning",
        )

    def _on_solve_error(self, message):
        self._solving = False
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")
        self._set_status("Error", ERROR)
        self._set_button_states(file_loaded=self._data is not None, solved=False)
        self._log_line(f"Solver error: {message}", "error")
        QMessageBox.critical(self, "Solver error", message)

    def _on_plot(self):
        if self._model is None:
            return
        self._log_line("Opening plot window...", "accent")
        try:
            plot(self._model)
        except Exception as exc:
            self._log_line(f"Plot error: {exc}", "error")

    def _on_save(self):
        if self._model is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save results",
            "output.xlsx",
            "Excel workbook (*.xlsx)",
        )
        if not path:
            return

        try:
            out = save_results(self._model, output_path=path)
            self._log_line(f"Results saved -> {out}", "success")
        except Exception as exc:
            self._log_line(f"Save error: {exc}", "error")
            QMessageBox.critical(self, "Save error", str(exc))

    def _on_reset(self):
        self._data = None
        self._model = None
        self._solving = False
        self.file_path.clear()
        self.summary_label.setText("No file loaded.")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress_label.setText("")
        self._set_status("Ready", FG_DIM)
        self._clear_results()
        self._set_button_states(file_loaded=False, solved=False)
        self._log_line("Reset.", "warning")


def main():
    app = QApplication(sys.argv)
    window = SMaRTEWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

