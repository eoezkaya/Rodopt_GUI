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
from PyQt6.QtGui import QPixmap, QTransform, QIcon, QTextCursor, QColor, QPainter  # UPDATED
from csv_table_updater import CSVTableUpdater
from config_store import load_executable
from config_store import save_executable
from plot_history_2d import plot_history_2d  # NEW
from plot_pareto_front import plot_pareto_front  # NEW
import subprocess  # NEW
import platform  # NEW
from log_display_window import LogDisplayWindow  # NEW

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
    QPushButton,  # NEW
)

from PyQt6.QtCore import Qt, QSize, QProcess, QTimer

from file_path_field import FilePathField


class RunDoE(QWidget):
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

        self.last_exec_path = load_executable()

        self._caffeinate_proc: subprocess.Popen | None = None  # NEW

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
        self.btn_run.setToolTip("Run the study")
        self.btn_run.clicked.connect(self._on_run_clicked)

        self.btn_pause = QToolButton()
        self.btn_pause.setIcon(QIcon(str(self.ICON_DIR / "pause.svg")))
        self.btn_pause.setIconSize(icon_size)
        self.btn_pause.setAutoRaise(True)
        self.btn_pause.setFixedSize(button_size + 6, button_size + 6)
        self.btn_pause.setToolTip("Pause the study")
        self.btn_pause.clicked.connect(self._on_pause_clicked)

        self.btn_stop = QToolButton()
        self.btn_stop.setIcon(QIcon(str(self.ICON_DIR / "stop.svg")))
        self.btn_stop.setIconSize(icon_size)
        self.btn_stop.setAutoRaise(True)
        self.btn_stop.setFixedSize(button_size + 6, button_size + 6)
        self.btn_stop.setToolTip("Stop the study")
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
        self.btn_plot.setToolTip("Plot Pareto front")
        self.btn_plot.clicked.connect(self._on_plot_pareto_clicked)
        self.btn_plot.setEnabled(False)  # initially disabled
        
        # === NEW: Process Status button ===
        self.btn_status = QToolButton()
        self.btn_status.setIcon(QIcon(str(self.ICON_DIR / "status.svg")))  # <-- add a small icon (create status.svg)
        self.btn_status.setIconSize(icon_size)
        self.btn_status.setAutoRaise(True)
        self.btn_status.setFixedSize(button_size + 6, button_size + 6)
        self.btn_status.setToolTip("Show process status")
        self.btn_status.clicked.connect(self._on_show_process_status_clicked)
        self.btn_status.setEnabled(True)  # always active

        self.btn_plot_2d = QToolButton()
        self.btn_plot_2d.setIcon(QIcon(str(self.ICON_DIR / "chart.svg")))
        self.btn_plot_2d.setIconSize(icon_size)
        self.btn_plot_2d.setAutoRaise(True)
        self.btn_plot_2d.setFixedSize(button_size + 6, button_size + 6)
        self.btn_plot_2d.setToolTip("Plot optimization history")
        self.btn_plot_2d.clicked.connect(self._on_plot_history_2d_clicked)
        self.btn_plot_2d.setEnabled(True)  # match Pareto button initial state

        self.show_main_log_btn = QToolButton(self)
        self.show_main_log_btn.setIcon(QIcon(str(self.ICON_DIR / "log.svg")))
        self.show_main_log_btn.setIconSize(icon_size)  # match other header icons
        self.show_main_log_btn.setAutoRaise(True)
        self.show_main_log_btn.setFixedSize(button_size + 6, button_size + 6)
        self.show_main_log_btn.setToolTip("Show run log")
        self.show_main_log_btn.clicked.connect(self._on_show_main_log_clicked)

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
        header_layout.addWidget(self.btn_plot_2d)  # NEW: next to Pareto
        header_layout.addWidget(self.btn_status)
        header_layout.addWidget(self.show_main_log_btn)


        # ==========================================================
        # === Main group box ===
        # ==========================================================
        self.group_box = QGroupBox("", self)
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
        self.exec_field.pathChanged.connect(save_executable)

        self.exec_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.xml_field = FilePathField(
            name="XML file",
            path="",
            label_width=label_width,
            field_width=field_width,
            select_mode="open_file",   # irrelevant now
            parent=self.group_box,
        )

        # 🔒 make it display-only
        self.xml_field.setEnabled(False)

        self._xml_path: Optional[str] = None


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
        # === Table to display history.csv ===
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
        
        
        self._csv_updater = CSVTableUpdater(self.table)

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
    
    def set_xml_path(self, path: str) -> None:
        self._xml_path = os.path.abspath(path)
        self.xml_field.path = self._xml_path   # display only
        self._update_run_directory()
        self._update_plot_buttons_enabled()  # NEW

    # NEW: macOS keep-awake helpers
    def _keep_awake_start(self) -> None:
        if platform.system() != "Darwin":
            return
        if self._caffeinate_proc is not None and self._caffeinate_proc.poll() is None:
            return
        try:
            # -dimsu: prevent display sleep, idle sleep, and system sleep while this runs
            self._caffeinate_proc = subprocess.Popen(
                ["caffeinate", "-dimsu"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self._caffeinate_proc = None

    def _keep_awake_stop(self) -> None:
        p = self._caffeinate_proc
        self._caffeinate_proc = None
        if p is None:
            return
        try:
            p.terminate()
        except Exception:
            pass

    def _on_run_clicked(self):
        # Determine whether this is a resume or a fresh start
        was_paused = (getattr(self, "state", "") == "paused")

        # If process is stopped (fresh start), clear the table
        if not was_paused:
            try:
                self.table.setRowCount(0)
                self.table.clearContents()
            except Exception:
                pass
            # also reset CSV updater cache so new run's CSV is picked up immediately
            try:
                if hasattr(self, "_csv_updater") and self._csv_updater is not None:
                    self._csv_updater._last_mtime = 0.0
            except Exception:
                pass

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
        xml_path = self._xml_path



        if not exec_path or not os.path.isfile(exec_path):
            QMessageBox.critical(self, "Executable not found", "Please select a valid executable.")
            return

        save_executable(exec_path)

        
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_process_finished)

        self._keep_awake_start()  # NEW

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
                self._keep_awake_stop()  # NEW
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
                self.paused_duration = 0.0
                self._update_status_indicator("red", "Stopped")
                self.btn_run.setEnabled(True)
                self.btn_pause.setEnabled(False)
                self._keep_awake_stop()  # NEW
        elif state == QProcess.ProcessState.Running and self.start_time:
            elapsed = int(time.time() - self.start_time - getattr(self, "paused_duration", 0.0))
            self._update_status_indicator("green", f"Running ({self._format_elapsed(elapsed)})")
    
    


    def _on_stop_clicked(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.state = "stopped"
        self.btn_run.setEnabled(True)
        self._update_status_indicator("red", "Stopped")
        self._update_run_directory()
        self._keep_awake_stop()  # NEW
                
    def _on_process_finished(self, exit_code, exit_status):
        self.state = "stopped"
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
    # === Run directory tracking ===
    # ==========================================================
    def _update_run_directory(self):
        """Detect latest valid run directory created after pressing 'Run'."""
       
       
        xml_path = self._xml_path
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
                if self._xml_path and os.path.isfile(self._xml_path):
                    tree = ET.parse(self._xml_path)
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
        try:
            run_dir = self.run_dir_field.path.strip()
            if not run_dir or not os.path.isdir(run_dir):
                QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
                return

            csv_path = os.path.join(run_dir, "history.csv")
            if not os.path.isfile(csv_path):
                alt = os.path.join(run_dir, "history.csv")
                csv_path = alt if os.path.isfile(alt) else ""
            if not csv_path:
                QMessageBox.warning(self, "Missing File", "history.csv not found.")
                return

            if not getattr(self, "_xml_path", None):
                QMessageBox.warning(self, "Missing XML", "Study XML path is not set.")
                return

            plot_pareto_front(csv_path, xml_path=self._xml_path, title="Pareto Front")
        except Exception as e:
            QMessageBox.critical(self, "Plot Error", f"Failed to plot Pareto front:\n{e}")

    def _on_show_process_status_clicked(self):
        """Open a dialog showing the contents of the latest process.log file in the run directory."""
        run_dir = self.run_dir_field.path.strip()
        if not run_dir or not os.path.isdir(run_dir):
            QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
            return

        # Find latest process.log file
        log_files = [f for f in os.listdir(run_dir) if f.endswith("process.log")]
        if not log_files:
            QMessageBox.information(self, "No Log File", "No process.log file found in the run directory.")
            return

        # Pick the most recently modified one
        log_files_full = [os.path.join(run_dir, f) for f in log_files]
        latest_log = max(log_files_full, key=os.path.getmtime)

        dlg = LogDisplayWindow(
            file_path=latest_log,
            title=f"Process Status — {os.path.basename(latest_log)}",
            icon_dir=self.ICON_DIR,
            parent=self,
            min_size=(1100, 700),
        )

#        # Make it wider (before exec)
#        screen = QApplication.primaryScreen().availableGeometry()
#        dlg.setMinimumWidth(1500)
#        dlg.resize(max(1500, int(screen.width() * 0.85)), int(screen.height() * 0.7))

        dlg.exec()

    def _on_show_main_log_clicked(self) -> None:
        try:
            run_dir = self.run_dir_field.path.strip()
            if not run_dir or not os.path.isdir(run_dir):
                QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
                return

            doe_log = os.path.join(run_dir, "doe.log")
            opt_log = os.path.join(run_dir, "optimization.log")

            log_path = doe_log if os.path.isfile(doe_log) else (opt_log if os.path.isfile(opt_log) else "")
            if not log_path:
                QMessageBox.information(
                    self,
                    "Missing Log",
                    "Neither doe.log nor optimization.log was found in the run directory.",
                )
                return

            self._show_text_file_dialog(os.path.basename(log_path), log_path)
        except Exception as e:
            QMessageBox.critical(self, "Log Error", f"Failed to show log:\n{e}")

    def _show_text_file_dialog(self, title: str, file_path: str) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumSize(900, 600)

        editor = QTextEdit(dlg)
        editor.setReadOnly(True)

        def _load_file(scroll_to_end: bool = True) -> None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    editor.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Open Error", f"Failed to open log file:\n{e}")
                return

            if scroll_to_end:
                editor.moveCursor(QTextCursor.MoveOperation.End)
                QTimer.singleShot(
                    0,
                    lambda: editor.verticalScrollBar().setValue(editor.verticalScrollBar().maximum()),
                )

        # Top bar with reload button on the right
        reload_btn = QToolButton(dlg)
        reload_btn.setAutoRaise(True)
        reload_btn.setToolTip("Reload")
        reload_btn.setIcon(QIcon(str(self.ICON_DIR / "reload.svg")))
        reload_btn.clicked.connect(lambda: _load_file(scroll_to_end=True))

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch(1)
        top_bar.addWidget(reload_btn)

        layout = QVBoxLayout(dlg)
        layout.addLayout(top_bar)
        layout.addWidget(editor)

        dlg.setLayout(layout)

        # initial load
        _load_file(scroll_to_end=True)

        dlg.exec()

    # ==========================================================
    # === CSV monitoring ===
    # ==========================================================#
    
    def _update_csv_table(self):
        run_dir = self.run_dir_field.path.strip()
        if not run_dir:
            return

        self._csv_updater.update(
            csv_path=os.path.join(run_dir, "history.csv"),
            xml_path=self._xml_path,
            start_time=self.start_time,
            dimension=self._dimension,
            state=self.state,
        )

    
    def _is_float(self, s: str) -> bool:
        try:
            float(s)
            return True
        except Exception:
            return False
    
  
    def _on_table_row_clicked(self, row: int, col: int) -> None:
        try:
            # Determine run directory and CSV
            run_dir = self.run_dir_field.path.strip()
            if not run_dir or not os.path.isdir(run_dir):
                QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
                return
    
            csv_path = os.path.join(run_dir, "history.csv")
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
    
            constraints = self._read_constraints_from_xml()
            by_name = {c["name"]: c for c in constraints}

            feas_names = {"feasible", "feasibility", "is_feasible", "feas", "feas_flag"}

            html_lines: list[str] = []
            for h, v in zip(headers, data_row):
                h_clean = h.strip()
                v_clean = v.strip()

                # do not display Improvement rows
                if h_clean.lower() == "improvement":
                    continue

                # feasibility as YES/NO
                if h_clean.lower() in feas_names:
                    try:
                        feas_val = float(v_clean)
                    except Exception:
                        feas_val = 0.0
                    v_html = (
                        '<span style="color:#008000; font-weight:600;">YES</span>'
                        if feas_val > 0.5
                        else '<span style="color:#cc0000; font-weight:600;">NO</span>'
                    )
                    html_lines.append(f"{h_clean}: {v_html}")
                    continue

                # constraints: match ONLY by name
                c = by_name.get(h_clean.lower())
                if c is not None:
                    try:
                        x = float(v_clean)
                    except Exception:
                        x = None

                    if x is None:
                        v_esc = (
                            v_clean.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html_lines.append(f"{h_clean}: {v_esc}")
                    else:
                        op = c["op"]  # "<" or ">"
                        val = float(c["val"])
                        ok = (x < val) if op == "<" else (x > val)
                        color = "#008000" if ok else "#cc0000"
                        v_html = f'<span style="color:{color}; font-weight:600;">{x:g}</span>'
                        html_lines.append(f"{h_clean}: {v_html}")
                    continue

                # default: escape
                v_esc = (
                    v_clean.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                h_esc = (
                    h_clean.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                html_lines.append(f"{h_esc}: {v_esc}")

            text_edit.setHtml("<br/>".join(html_lines))

            layout = QVBoxLayout(dlg)
            layout.addWidget(text_edit)
            dlg.setLayout(layout)
            dlg.exec()
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show design details:\n{e}")
        
    def _read_constraints_from_xml(self) -> list[dict[str, object]]:
        """
        Returns constraints with keys:
          - name: str (lowercased)
          - op: str ("<" or ">")
          - val: float
        """
        xml_path = getattr(self, "_xml_path", None)
        if not xml_path:
            return []
        try:
            root = ET.parse(xml_path).getroot()
        except Exception:
            return []

        out: list[dict[str, object]] = []
        for c in root.findall(".//constraint_function"):
            name = (c.findtext("name") or "").strip()
            if not name:
                continue

            ctype = (c.findtext("constraint_type") or "").strip()
            cval = (c.findtext("constraint_value") or "").strip()

            # accept only literal operators; tolerate legacy
            if ctype.lower() == "lt":
                op = "<"
            elif ctype.lower() == "gt":
                op = ">"
            else:
                op = ctype

            try:
                val = float(cval)
            except Exception:
                continue

            if op not in ("<", ">"):
                continue

            out.append({"name": name.lower(), "op": op, "val": val})
        return out

    def _on_plot_history_2d_clicked(self) -> None:  # UPDATED
        run_dir = self.run_dir_field.path.strip()
        if not run_dir or not os.path.isdir(run_dir):
            QMessageBox.warning(self, "No Run Directory", "Run directory not found.")
            return

        csv_path = os.path.join(run_dir, "history.csv")
        if not os.path.isfile(csv_path):
            # fallback to DoE_history.csv if that’s what exists in this run folder
            alt = os.path.join(run_dir, "DoE_history.csv")
            if os.path.isfile(alt):
                csv_path = alt
            else:
                QMessageBox.warning(self, "Missing File", "history.csv / DoE_history.csv not found.")
                return

        try:
            # NEW: determine d from study XML <dimension>
            if not getattr(self, "_xml_path", None) or not os.path.isfile(self._xml_path):
                raise ValueError("Study XML path not set.")

            tree = ET.parse(self._xml_path)
            root = tree.getroot()
            dim_el = root.find(".//dimension")
            if dim_el is None or not (dim_el.text or "").strip():
                raise ValueError("Could not find <dimension> in the study XML.")
            d = int(float(dim_el.text.strip()))
            if d <= 0:
                raise ValueError("<dimension> must be a positive integer.")

            plot_history_2d(csv_path, d, title="Best feasible objective vs Sample ID")
        except Exception as e:
            QMessageBox.critical(self, "Plot Error", f"Failed to plot optimization history:\n{e}")


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
    def _is_multi_objective(self) -> bool:
        """Return True if study XML defines more than one objective_function."""
        try:
            xml_path = getattr(self, "_xml_path", None)
            if not xml_path or not os.path.isfile(xml_path):
                return False
            root = ET.parse(xml_path).getroot()
            return len(root.findall("objective_function")) > 1
        except Exception:
            return False

    def _update_plot_buttons_enabled(self) -> None:
        """
        Pareto vs history-2D are mutually exclusive:
          - Multi-objective: enable Pareto, disable history-2D
          - Single-objective: disable Pareto, enable history-2D
        """
        mo = self._is_multi_objective()

        if hasattr(self, "btn_plot"):      # Pareto
            self.btn_plot.setEnabled(mo)
        if hasattr(self, "btn_plot_2d"):   # history plot
            self.btn_plot_2d.setEnabled(not mo)

