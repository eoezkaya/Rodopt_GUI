from __future__ import annotations
from typing import Optional
import shutil
import os
import json
import time
import signal
import csv
from pathlib import Path
import matplotlib.pyplot as plt 
import xml.etree.ElementTree as ET
from PyQt6.QtGui import QPixmap, QTransform, QIcon

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QToolButton,
    QSizePolicy,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QDialog,
    QScrollArea,
    QApplication,
)

from PyQt6.QtCore import Qt, QSize, QProcess, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter

from file_path_field import FilePathField


class RunDoE(QWidget):
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rodop_run_config.json")
    ICON_DIR = Path(__file__).resolve().parent / "images"

    def __init__(
        self,
        *,
        label_width: int = 180,
        field_width: int = 800,
        button_size: int = 28,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.state = "stopped"
        self.process: Optional[QProcess] = None
        self.start_time: Optional[float] = None
        self.pause_start_time: Optional[float] = None
        self.paused_duration: float = 0.0
        
        
        self._last_csv_mtime = 0.0
        self._dimension: Optional[int] = None

        self.last_exec_path = self._load_last_executable()

        # ==========================================================
        # === Header ===
        # ==========================================================
        self.status_circle = QLabel(self)
        self.status_circle.setFixedSize(14, 14)

        self.status_label = QLabel("Stopped", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("font-weight: 500; color: #444;")
        self.status_label.setFixedWidth(140)
        self._update_status_indicator("red", "Stopped")

        icon_size = QSize(button_size, button_size)
        self.btn_run = QToolButton()
        self.btn_run.setIcon(QIcon(str(self.ICON_DIR / "play.svg")))
        self.btn_run.setIconSize(icon_size)
        self.btn_run.setAutoRaise(True)
        self.btn_run.setFixedSize(button_size + 6, button_size + 6)
        self.btn_run.setToolTip("Run the DoE")
        self.btn_run.clicked.connect(self._on_run_clicked)

        self.btn_pause = QToolButton()
        self.btn_pause.setIcon(QIcon(str(self.ICON_DIR / "pause.svg")))
        self.btn_pause.setIconSize(icon_size)
        self.btn_pause.setAutoRaise(True)
        self.btn_pause.setFixedSize(button_size + 6, button_size + 6)
        self.btn_pause.setToolTip("Pause the DoE")
        self.btn_pause.clicked.connect(self._on_pause_clicked)

        self.btn_stop = QToolButton()
        self.btn_stop.setIcon(QIcon(str(self.ICON_DIR / "stop.svg")))
        self.btn_stop.setIconSize(icon_size)
        self.btn_stop.setAutoRaise(True)
        self.btn_stop.setFixedSize(button_size + 6, button_size + 6)
        self.btn_stop.setToolTip("Stop the DoE")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        
        self.btn_plot = QToolButton()  # NEW

# Load SVG into a pixmap
        pixmap = QPixmap(str(self.ICON_DIR / "draw.svg"))

# Create a transform and rotate 90 degrees
        transform = QTransform().rotate(180)   # 90, 180, 270
        rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)

# Use the rotated image as an icon
        self.btn_plot.setIcon(QIcon(rotated_pixmap))
        self.btn_plot.setIconSize(icon_size)
        self.btn_plot.setAutoRaise(True)
        self.btn_plot.setFixedSize(button_size + 6, button_size + 6)
        self.btn_plot.setToolTip("Plot Pareto Front")
        self.btn_plot.clicked.connect(self._on_plot_pareto_clicked)
        self.btn_plot.setEnabled(False)  # initially disabled
        
        # === NEW: Process Status button ===
        self.btn_status = QToolButton()
        self.btn_status.setIcon(QIcon(str(self.ICON_DIR / "status.svg")))  # <-- add a small icon (create status.svg)
        self.btn_status.setIconSize(icon_size)
        self.btn_status.setAutoRaise(True)
        self.btn_status.setFixedSize(button_size + 6, button_size + 6)
        self.btn_status.setToolTip("Show process status (from *_process_pool.log)")
        self.btn_status.clicked.connect(self._on_show_process_status_clicked)
        self.btn_status.setEnabled(True)  # always active

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.addWidget(self.status_circle)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_run)
        header_layout.addWidget(self.btn_pause)
        header_layout.addWidget(self.btn_stop)
        header_layout.addWidget(self.btn_plot)
        header_layout.addWidget(self.btn_status)


        # ==========================================================
        # === Main group box ===
        # ==========================================================
        self.group_box = QGroupBox("Design of Experiment", self)
        self.group_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.group_box.setMinimumWidth(900)
        self.group_box.setMaximumWidth(2000)

        detected_path = shutil.which("rodeo") or ""
        exec_path = self.last_exec_path or detected_path

        self.exec_field = FilePathField(
            name="Optimizer",
            path=exec_path,
            label_width=label_width,
            field_width=field_width,
            select_mode="open_file",
            dialog_title="Select the Optimizer",
            filters="Executable files (*)",
            parent=self.group_box,
        )
        self.exec_field.pathChanged.connect(self._save_current_executable)
        self.exec_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.xml_field = FilePathField(
            name="XML file",
            path="",
            label_width=label_width,
            field_width=field_width,
            select_mode="open_file",
            dialog_title="Select XML configuration file",
            filters="XML files (*.xml);;All files (*)",
            parent=self.group_box,
        )
        self.xml_field.pathChanged.connect(self._update_run_directory)
        self.xml_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.run_dir_field = FilePathField(
            name="Run directory",
            path="(none found)",
            label_width=label_width,
            field_width=field_width,
            select_mode="open_directory",
            dialog_title="Select Run Directory",
            parent=self.group_box,
        )
        self.run_dir_field.setEnabled(False)
        self.run_dir_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(8, 16, 8, 8)
        inner_layout.setSpacing(6)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for w in (self.exec_field, self.xml_field, self.run_dir_field):
            if hasattr(w, "layout"):
                w.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
            inner_layout.addWidget(w)

        # ==========================================================
        # === Table to display DoE_history.csv ===
        # ==========================================================
        self.table = QTableWidget(self)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(250)
        self.table.cellClicked.connect(self._on_table_row_clicked)
        self.table.verticalHeader().setVisible(False)
        
        
                # ==========================================================
        # === Auto-load last XML path from ~/.rodop_run_config.json ===
        # ==========================================================
        try:
            if os.path.isfile(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_xml = data.get("last_loaded_xml", "").strip()
                    if last_xml and os.path.isfile(last_xml):
                        self.xml_field.path = last_xml
                        print(f"[RunDoE] Auto-loaded last XML: {last_xml}")
        except Exception as e:
            print(f"[RunDoE] Warning: failed to auto-load last XML: {e}")


        # ==========================================================
        # === Main layout ===
        # ==========================================================
        outer_layout = QVBoxLayout(self)
        outer_layout.addLayout(header_layout)
        outer_layout.addWidget(self.group_box)
        outer_layout.addWidget(self.table)
        self.setLayout(outer_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # ==========================================================
        # === Timers ===
        # ==========================================================
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._check_process_status)
        self._status_timer.start()

        self._run_dir_timer = QTimer(self)
        self._run_dir_timer.setInterval(5000)
        self._run_dir_timer.timeout.connect(self._update_run_directory)
        self._run_dir_timer.start()

        self._csv_timer = QTimer(self)
        self._csv_timer.setInterval(3000)
        self._csv_timer.timeout.connect(self._update_csv_table)
        self._csv_timer.start()

    # ==========================================================
    # === Process handling ===
    # ==========================================================
    
    def _on_run_clicked(self):
        """Start or resume the DoE process."""
        # --- Resume case ---
        if self.state == "paused" and self.process:
            try:
                pid = self.process.processId()
                if pid:
                    os.kill(pid, signal.SIGCONT)
                    self.state = "running"
                    self._status_timer.start()
                    if self.pause_start_time:
                        self.paused_duration += time.time() - self.pause_start_time
                        self.pause_start_time = None
                    self._update_status_indicator("green", "Running (resumed)")
                    self.btn_pause.setEnabled(True)
                    self.btn_run.setEnabled(False)
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to resume process:\n{e}")
                return

        # --- Already running? ---
        if self.state == "running" and self.process and \
           self.process.state() == QProcess.ProcessState.Running:
            QMessageBox.information(self, "Already Running", "The DoE process is already running.")
            return

        # --- Normal start case ---
        exec_path = self.exec_field.path.strip()
        xml_path = self.xml_field.path.strip()

        if not exec_path or not os.path.isfile(exec_path):
            QMessageBox.critical(self, "Executable not found", "Please select a valid executable.")
            return

        if not xml_path or not os.path.isfile(xml_path):
            QMessageBox.critical(self, "XML file not found", "Please select a valid XML configuration file.")
            return

        self._save_current_executable(exec_path)
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_process_finished)

        self.process.start(exec_path, [xml_path])
        if not self.process.waitForStarted(2000):
            QMessageBox.critical(self, "Error", "Failed to start the executable.")
            return

        self.start_time = time.time()
        self.paused_duration = 0.0
        self.pause_start_time = None
        self.state = "running"
        self.btn_run.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self._status_timer.start()
        self._update_status_indicator("green", "Running (0s)")
        QTimer.singleShot(1500, self._update_run_directory)


    def _on_pause_clicked(self):
        """Pause the currently running DoE process."""
        if not self.process or self.process.state() != QProcess.ProcessState.Running:
            QMessageBox.information(self, "Not Running", "No active DoE process to pause.")
            return

        try:
            pid = self.process.processId()
            if pid:
                os.kill(pid, signal.SIGSTOP)  # Pause the process
                self.state = "paused"
                self.pause_start_time = time.time()
                self._status_timer.stop()
                self._update_status_indicator("yellow", "Paused")
                self.btn_pause.setEnabled(False)
                self.btn_run.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pause process:\n{e}")


    def _check_process_status(self):
        """Periodically check process state and update UI accordingly."""
        if not self.process:
            if self.state != "stopped":
                self.state = "stopped"
                self.btn_run.setEnabled(True)
                self._update_status_indicator("red", "Stopped")
            return

        # --- do not override manually paused state ---
        if self.state == "paused":
            return

        state = self.process.state()
        if state == QProcess.ProcessState.NotRunning:
            if self.state != "stopped":
                self.state = "stopped"
                self.start_time = None
                self.paused_duration = 0.0
                self._update_status_indicator("red", "Stopped")
                self.btn_run.setEnabled(True)
                self.btn_pause.setEnabled(False)
        elif state == QProcess.ProcessState.Running and self.start_time:
            elapsed = int(time.time() - self.start_time - getattr(self, "paused_duration", 0.0))
            self._update_status_indicator("green", f"Running ({self._format_elapsed(elapsed)})")
    
    


    def _on_stop_clicked(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.state = "stopped"
        self.start_time = None
        self.btn_run.setEnabled(True)
        self._update_status_indicator("red", "Stopped")
        self._update_run_directory()
                
    def _on_process_finished(self, exit_code, exit_status):
        self.state = "stopped"
        self.start_time = None
        self.btn_run.setEnabled(True)
        self._update_status_indicator("red", "Stopped")
        self._update_run_directory()

    def _on_stdout(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        print("[RunDoE][stdout]", text.strip())

    def _on_stderr(self):
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="ignore")
        print("[RunDoE][stderr]", text.strip())

    # ==========================================================
    # === Config persistence ===
    # ==========================================================
    def _load_last_executable(self) -> str:
        try:
            if os.path.isfile(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    path = data.get("rodeo_executable", "")
                    if path and os.path.isfile(path):
                        return path
        except Exception as e:
            print(f"[RunDoE] Failed to load config: {e}")
        return ""

    def _save_current_executable(self, path: str):
        try:
            if path.strip():
                data = {"rodeo_executable": path.strip()}
                with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[RunDoE] Failed to save config: {e}")

    # ==========================================================
    # === Run directory tracking ===
    # ==========================================================
    def _update_run_directory(self):
        """Detect latest valid run directory created after pressing 'Run'."""
        xml_path = self.xml_field.path.strip()
        if not (xml_path and os.path.isfile(xml_path)):
            self.run_dir_field.path = "(none found)"
            self._dimension = None
            return

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            general = root.find("general_settings") or root.find("GeneralSettings")
            if general is None:
                self.run_dir_field.path = "(none found)"
                self._dimension = None
                return

            name = self._find_text(general, ["name", "Name"]).strip()
            working_dir = self._find_text(general, ["working_directory", "Working_directory"]).strip()
            dim_text = self._find_text(general, ["dimension", "Dimension"]).strip()
            self._dimension = int(dim_text) if dim_text.isdigit() else None
            
            try:
                num_objectives = 0
                if xml_path := self.xml_field.path.strip():
                    if os.path.isfile(xml_path):
                        tree = ET.parse(xml_path)
                        root = tree.getroot()
                        num_objectives = len(root.findall("objective_function"))
                self.btn_plot.setEnabled(num_objectives == 2)
            except Exception as e:
                print(f"[RunDoE] Could not determine number of objectives: {e}")
                self.btn_plot.setEnabled(False)
            
            if not name or not working_dir or not os.path.isdir(working_dir):
                self.run_dir_field.path = "(none found)"
                return

            latest = self._find_latest_run_dir(working_dir, name)

            # --- Filter: accept only directories created AFTER pressing Run ---
            if latest and self.start_time:
                try:
                    dir_mtime = os.path.getmtime(latest)
                    if dir_mtime < self.start_time:
                        # too old, created before this run
                        latest = None
                except Exception as e:
                    print(f"[RunDoE] Warning: failed to check run dir time: {e}")
                    latest = None

            self.run_dir_field.path = latest if latest else "(none found)"

        except Exception as e:
            print(f"[RunDoE] Failed to parse XML for run dir: {e}")
            self.run_dir_field.path = "(none found)"
            self._dimension = None
    
   

    @staticmethod
    def _find_text(parent: ET.Element, tags: list[str]) -> str:
        for t in tags:
            el = parent.find(t)
            if el is not None and el.text:
                return el.text
        return ""

    @staticmethod
    def _find_latest_run_dir(working_dir: str, problem_name: str) -> Optional[str]:
        prefix = f"run-{problem_name}"
        latest_path = None
        latest_mtime = -1.0
        try:
            with os.scandir(working_dir) as it:
                for entry in it:
                    if entry.is_dir() and entry.name.startswith(prefix):
                        mtime = entry.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_path = os.path.abspath(entry.path)
        except FileNotFoundError:
            return None
        return latest_path

    def _on_plot_pareto_clicked(self):  # UPDATED
        """Read CSV and plot Pareto front with feasible/unfeasible separation."""
        run_dir = self.run_dir_field.path.strip()
        if not run_dir or not os.path.isdir(run_dir):
            QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
            return
    
        csv_path = os.path.join(run_dir, "DoE_history.csv")
        if not os.path.isfile(csv_path):
            QMessageBox.warning(self, "Missing File", "DoE_history.csv not found.")
            return
    
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            if len(rows) < 2:
                QMessageBox.information(self, "No Data", "No valid data in CSV file.")
                return
    
            headers = rows[0]
            data = rows[1:]
    
            # determine objective columns from XML
            xml_path = self.xml_field.path.strip()
            tree = ET.parse(xml_path)
            root = tree.getroot()
            num_objectives = len(root.findall("objective_function"))
            if num_objectives != 2:
                QMessageBox.information(self, "Invalid", "Pareto plot requires exactly two objectives.")
                return
    
            # find dimensionality and columns
            general = root.find("general_settings") or root.find("GeneralSettings")
            dim_text = self._find_text(general, ["dimension", "Dimension"]).strip()
            dim = int(dim_text) if dim_text.isdigit() else 0
            feas_col = len(headers) - 1
            obj_cols = [dim, dim + 1]
    
            # --- collect all points ---
            feasible_points = []
            infeasible_points = []
    
            for row in data:
                try:
                    x = float(row[obj_cols[0]])
                    y = float(row[obj_cols[1]])
                    feas = float(row[feas_col]) if self._is_float(row[feas_col]) else 0.0
                    if feas == 1.0:
                        feasible_points.append((x, y))
                    else:
                        infeasible_points.append((x, y))
                except Exception:
                    continue
    
            if not feasible_points and not infeasible_points:
                QMessageBox.information(self, "No Data", "No valid points found in CSV.")
                return
    
            # --- compute Pareto front among feasible points ---
            def dominates(a, b):
                """Return True if a dominates b (assuming minimization)."""
                return (a[0] <= b[0] and a[1] <= b[1]) and (a[0] < b[0] or a[1] < b[1])
    
            pareto_points = []
            for p in feasible_points:
                if not any(dominates(q, p) for q in feasible_points if q != p):
                    pareto_points.append(p)
    
            # sort Pareto points for line
            pareto_points.sort(key=lambda p: p[0])
    
            # --- plot ---
            plt.figure(figsize=(6, 5))
            if infeasible_points:
                x_infeas, y_infeas = zip(*infeasible_points)
                plt.scatter(x_infeas, y_infeas, color="red", label="Unfeasible Samples", marker="x")
            if feasible_points:
                x_feas, y_feas = zip(*feasible_points)
                plt.scatter(x_feas, y_feas, color="blue", label="Feasible Samples", marker="o")
            if pareto_points:
                px, py = zip(*pareto_points)
                plt.plot(px, py, color="green", marker="o", linewidth=2.5, label="Pareto Front")
    
            plt.xlabel(headers[obj_cols[0]])
            plt.ylabel(headers[obj_cols[1]])
            plt.title("Pareto Front")
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.show()
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot Pareto front:\n{e}")
    

    def _on_show_process_status_clicked(self):
        """Open a dialog showing the contents of the latest *_process_pool.log file in the run directory."""
        run_dir = self.run_dir_field.path.strip()
        if not run_dir or not os.path.isdir(run_dir):
            QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
            return

        # Find latest *_process_pool.log file
        log_files = [f for f in os.listdir(run_dir) if f.endswith("_process_pool.log")]
        if not log_files:
            QMessageBox.information(self, "No Log File", "No *_process_pool.log file found in the run directory.")
            return

        # Pick the most recently modified one
        log_files_full = [os.path.join(run_dir, f) for f in log_files]
        latest_log = max(log_files_full, key=os.path.getmtime)

        try:
            with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read().strip()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read log file:\n{e}")
            return

        # Create dialog to show contents
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Process Status — {os.path.basename(latest_log)}")
        
        screen = QApplication.primaryScreen().availableGeometry()
        dlg.resize(int(screen.width() * 0.7), int(screen.height() * 0.7))

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        text_edit.setPlainText(log_content)

        layout = QVBoxLayout(dlg)
        layout.addWidget(text_edit)
        dlg.setLayout(layout)
        dlg.exec()


    # ==========================================================
    # === CSV monitoring ===
    # ==========================================================#
    
    def _update_csv_table(self):
        """Load DoE_history.csv periodically and update table view."""
        if not self.start_time or self.state != "running":
            return
    
        run_dir = self.run_dir_field.path.strip()
        if not run_dir or not os.path.isdir(run_dir):
            return
    
        csv_path = os.path.join(run_dir, "DoE_history.csv")
        if not os.path.isfile(csv_path):
            return
    
        try:
            mtime = os.path.getmtime(csv_path)
            if mtime == self._last_csv_mtime or (self.start_time and mtime < self.start_time):
                return
    
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            if len(rows) < 2:
                return
    
            headers = rows[0]
            data = rows[1:]
            n_cols = len(headers)
            if n_cols == 0:
                return
    
            dim = self._dimension or 0  # number of input variables from XML
            if dim >= n_cols:
                return
    
            # ----------------------------------------------------------
            # --- Determine number of objective functions from XML ---
            # ----------------------------------------------------------
            num_objectives = 1
            xml_path = self.xml_field.path.strip()
            try:
                if xml_path and os.path.isfile(xml_path):
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    num_objectives = len(root.findall("objective_function")) or 1
            except Exception as e:
                print(f"[RunDoE] Could not count objective functions: {e}")
                num_objectives = 1
    
            feas_col = n_cols - 1  # last column = feasibility
            obj_cols = list(range(dim, min(dim + num_objectives, n_cols)))
    
            # improvement column if present
            improvement_col = None
            for i, h in enumerate(headers):
                if h.strip().lower() == "improvement":
                    improvement_col = i
                    break
    
            # ----------------------------------------------------------
            # --- Pareto detection helper ---
            # ----------------------------------------------------------
            def _find_pareto_front(values):
                """Return indices of Pareto-optimal points (minimize objectives)."""
                pareto = set()
                for i, vi in enumerate(values):
                    dominated = False
                    for j, vj in enumerate(values):
                        if j == i:
                            continue
                        if all(a <= b for a, b in zip(vj, vi)) and any(a < b for a, b in zip(vj, vi)):
                            dominated = True
                            break
                    if not dominated:
                        pareto.add(i)
                return pareto
    
            # ----------------------------------------------------------
            # --- Identify special points ---
            # ----------------------------------------------------------
            pareto_indices = set()
            best_idx = None
    
            if num_objectives == 1:
                obj_col = obj_cols[0]
                feasible = [
                    (i, float(r[obj_col]))
                    for i, r in enumerate(data)
                    if feas_col < len(r) and self._is_float(r[feas_col]) and float(r[feas_col]) == 1.0
                ]
                if feasible:
                    best_idx, _ = min(feasible, key=lambda x: x[1])
            elif num_objectives == 2:
                feasible_points = []
                for i, row in enumerate(data):
                    try:
                        if feas_col < len(row) and float(row[feas_col]) == 1.0:
                            values = [float(row[c]) for c in obj_cols]
                            feasible_points.append((i, values))
                    except Exception:
                        continue
                if feasible_points:
                    pareto_local = _find_pareto_front([v for _, v in feasible_points])
                    pareto_indices = {feasible_points[k][0] for k in pareto_local}
    
            # ----------------------------------------------------------
            # --- Populate table ---
            # ----------------------------------------------------------
            self.table.clear()
            self.table.setColumnCount(len(headers) + 1)
            self.table.setRowCount(len(data))
            self.table.setHorizontalHeaderLabels(["ID"] + headers)
    
            for i, row in enumerate(data):
                id_val = str(i + 1)
                if i == best_idx or i in pareto_indices:
                    id_val = f"★ {id_val}"
                id_item = QTableWidgetItem(id_val)
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, 0, id_item)
    
                for j, val in enumerate(row):
                    table_col = j + 1
                    if j == feas_col:
                        try:
                            feas = float(val)
                            if feas == 1.0:
                                val = "Yes"
                                color = QColor("#2ECC71")
                            else:
                                val = "No"
                                color = QColor("#E74C3C")
                        except ValueError:
                            color = QColor("#000000")
                        item = QTableWidgetItem(val)
                        item.setForeground(color)
                    else:
                        item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, table_col, item)
    
                if i in pareto_indices or i == best_idx:
                    for j in range(len(headers) + 1):
                        cell = self.table.item(i, j)
                        if cell:
                            cell.setBackground(QColor("#fff9d6"))
    
            # ----------------------------------------------------------
            # --- Hide irrelevant columns ---
            # ----------------------------------------------------------
            keep_cols = {0}  # always keep ID
    
            # Count constraints from XML
            num_constraints = 0
            try:
                if xml_path and os.path.isfile(xml_path):
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    num_constraints = len(root.findall("constraint_function"))
            except Exception as e:
                print(f"[RunDoE] Could not count constraints: {e}")
                num_constraints = 0
    
            # Determine visible columns
            if num_objectives == 1:
                keep_cols.add(obj_cols[0] + 1)
                if num_constraints > 0:
                    keep_cols.add(feas_col + 1)
            elif num_objectives == 2:
                keep_cols.update({obj_cols[0] + 1, obj_cols[1] + 1})
                if num_constraints > 0:
                    keep_cols.add(feas_col + 1)
    
            if improvement_col is not None:
                keep_cols.discard(improvement_col + 1)
    
            for j in range(len(headers) + 1):
                self.table.setColumnHidden(j, j not in keep_cols)
    
            self._last_csv_mtime = mtime
            self.table.scrollToBottom()
    
        except Exception as e:
            print(f"[RunDoE] Failed to load DoE_history.csv: {e}")
        

    
    def _is_float(self, s: str) -> bool:
        try:
            float(s)
            return True
        except Exception:
            return False
    
  
    def _on_table_row_clicked(self, row: int, column: int):
        """Open a new dialog showing all values for the selected design (copyable)."""
        try:
            # Determine run directory and CSV
            run_dir = self.run_dir_field.path.strip()
            if not run_dir or not os.path.isdir(run_dir):
                QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
                return
    
            csv_path = os.path.join(run_dir, "DoE_history.csv")
            if not os.path.isfile(csv_path):
                QMessageBox.warning(self, "Missing File", "DoE_history.csv not found.")
                return
    
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
    
            if len(rows) < 2:
                return
    
            headers = rows[0]
            # Map current visible row back to correct CSV data row
            data_row = rows[row + 1] if row + 1 < len(rows) else None
            if not data_row:
                return
    
            # --- Create Dialog ---
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Design Details (Sample {row + 1})")
            dlg.resize(650, 800)
    
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
    
            # Build a clear, copyable textual representation
            lines = []
            for h, v in zip(headers, data_row):
                lines.append(f"{h.strip()}: {v.strip()}")
            text_edit.setPlainText("\n".join(lines))
    
            layout = QVBoxLayout(dlg)
            layout.addWidget(text_edit)
            dlg.setLayout(layout)
            dlg.exec()
            
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show design details:\n{e}")
        


    # ==========================================================
    # === Helpers ===
    # ==========================================================
    @staticmethod
    def _format_elapsed(seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def _update_status_indicator(self, color: str, text: str):
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 14, 14)
        p.end()
        self.status_circle.setPixmap(pixmap)
        self.status_label.setText(text)

    def closeEvent(self, event):
        for timer in (getattr(self, "_status_timer", None),
                      getattr(self, "_run_dir_timer", None),
                      getattr(self, "_csv_timer", None)):
            if timer and timer.isActive():
                timer.stop()
        super().closeEvent(event)

    # ==========================================================
    # === Periodic status checking ===
    # ==========================================================

