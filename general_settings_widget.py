from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QApplication, QGroupBox,
    QSizePolicy, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from xml.etree import ElementTree as ET
import sys, os
import re

from string_field import StringField
from integer_spinbox_field import IntegerSpinBoxField
from string_options_field import StringOptionsField
from directory_path_field import DirectoryPathField
from PyQt6.QtWidgets import QSpacerItem


class GeneralSettings(QWidget):
    """
    Composite widget for general study settings.

    Single source of truth for:
      - problem_type

    Emits:
      - changed(): any field changed
      - problemTypeChanged(str): problem type changed
    """

    _ALLOWED_PROBLEM_TYPES = {
        "Optimization",
        "Design of Experiment",
        "Uncertainty Quantification",
    }

    changed = pyqtSignal()
    problemTypeChanged = pyqtSignal(str)

    def __init__(
        self,
        *,
        label_width: int = 180,
        text_field_width: int = 360,
        int_field_width: int = 100,
        default_problem_name: str = "MyStudy",
        default_problem_type: str = "Optimization",
        default_num_params: int = 3,
        default_num_samples: int = 100,
        default_batch_size: int = 1,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # --- name validation state/style (NEW) ---
        self._problem_name_valid = True
        self._invalid_name_style = """
        QLineEdit {
            border: 2px solid red;
            border-radius: 3px;
        }
        """

        # Style for invalid numeric entries (red border)
        self._invalid_numeric_style = getattr(
            self,
            "_invalid_name_style",
            "QLineEdit { border: 2px solid red; border-radius: 3px; }",
        )

        self._num_objectives: int = 1  # NEW: set by Study

        # NEW: track last auto-filled value so we don't overwrite user edits
        self._last_inner_iter_autofill: Optional[str] = None

        # === Main GroupBox ===
        self.group_box = QGroupBox("General Settings", self)
        self.group_box.setMinimumWidth(700)
        self.group_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # === Fields ===
        self.problem_name_field = StringField(
            "Problem name",
            default=default_problem_name,
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )
        # NEW: validate on change
        self.problem_name_field.textChanged.connect(self._on_problem_name_changed)

        self.problem_type_field = StringOptionsField(
            "Problem type",
            value=default_problem_type,
            options=[
                "Optimization",
                "Design of Experiment",
                "Uncertainty Quantification",
            ],
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )

        self.num_params_field = IntegerSpinBoxField(
            "Number of parameters",
            value=default_num_params,
            minimum=1,
            maximum=9_999_999,
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )

        self.num_samples_field = IntegerSpinBoxField(
            "Number of samples",
            value=default_num_samples,
            minimum=1,
            maximum=100_000_000,
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )

        self.sampling_field = StringOptionsField(
            "Sampling method",
            value="Latin Hypercube",
            options=["Latin Hypercube", "Random", "Sobol", "Full Factorial"],
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )

        self.batch_size_field = IntegerSpinBoxField(
            "Batch size",
            value=default_batch_size,
            minimum=1,
            maximum=1_000_000,
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )

        self.working_dir_field = DirectoryPathField(
            "Working directory",
            path=os.getcwd(),
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )

        # NEW: Smart Scheduling (Optimization only)
        self.smart_scheduling_field = StringOptionsField(
            "Smart Scheduling",
            value="Off",
            options=["Off", "On"],
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )
        self.smart_scheduling_field.valueChanged.connect(lambda _v: self.changed.emit())

        # ==============================================================
        # NEW: f1/f2 bounds (shown only for Optimization + 2 objectives)
        # ==============================================================
        self.f1_min_field = StringField(
            "f1 min",
            default="",
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )
        self.f1_max_field = StringField(
            "f1 max",
            default="",
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )
        self.f2_min_field = StringField(
            "f2 min",
            default="",
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )
        self.f2_max_field = StringField(
            "f2 max",
            default="",
            label_width=label_width,
            field_width=int_field_width,
            parent=self.group_box,
        )

        for f in (self.f1_min_field, self.f1_max_field, self.f2_min_field, self.f2_max_field):
            f.textChanged.connect(self.changed)

        # NEW: validate numeric input live and show red border on invalid
        self.f1_min_field.textChanged.connect(lambda: self._validate_numeric_field(self.f1_min_field))
        self.f1_max_field.textChanged.connect(lambda: self._validate_numeric_field(self.f1_max_field))
        self.f2_min_field.textChanged.connect(lambda: self._validate_numeric_field(self.f2_min_field))
        self.f2_max_field.textChanged.connect(lambda: self._validate_numeric_field(self.f2_max_field))

        # create side-by-side rows
        self._f1_row = QWidget(self.group_box)
        self._f1_row.setContentsMargins(0, 0, 0, 0)  # NEW: no extra indent from the row widget

        # --- f1 row ---
        f1_lay = QHBoxLayout(self._f1_row)
        f1_lay.setContentsMargins(0, 0, 0, 0)
        f1_lay.setSpacing(12)
        f1_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)  # NEW

        f1_lay.addWidget(self.f1_min_field)
        f1_lay.addWidget(self.f1_max_field)
        f1_lay.addStretch(1)  # NEW: keep items pinned left

        self._f2_row = QWidget(self.group_box)
        self._f2_row.setContentsMargins(0, 0, 0, 0)  # NEW

        # --- f2 row ---
        f2_lay = QHBoxLayout(self._f2_row)
        f2_lay.setContentsMargins(0, 0, 0, 0)
        f2_lay.setSpacing(12)
        f2_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)  # NEW

        f2_lay.addWidget(self.f2_min_field)
        f2_lay.addWidget(self.f2_max_field)
        f2_lay.addStretch(1)  # NEW

        # NEW: Number of inner iterations
        self.num_inner_iterations_field = StringField(
            "Number of inner iterations",
            default="",
            label_width=label_width,
            field_width=text_field_width,
            parent=self.group_box,
        )
        self.num_inner_iterations_field.textChanged.connect(lambda _t: self.changed.emit())
        # validate numeric like other numeric string fields (if you use this helper elsewhere)
        try:
            self.num_inner_iterations_field.textChanged.connect(
                lambda _t: self._validate_numeric_field(self.num_inner_iterations_field)
            )
        except Exception:
            pass

        # === Layout ===
        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(16, 16, 16, 16)
        inner_layout.setSpacing(10)

        for w in (
            self.problem_name_field,
            self.problem_type_field,
            self.num_params_field,
            self.num_samples_field,
            self.num_inner_iterations_field,  # NEW: place right after number_of_samples_field
            self.sampling_field,
            self.batch_size_field,
            self.working_dir_field,
            self.smart_scheduling_field,
        ):
            inner_layout.addWidget(w, alignment=Qt.AlignmentFlag.AlignLeft)

        inner_layout.addWidget(self._f1_row)
        inner_layout.addWidget(self._f2_row)

        inner_layout.addStretch(1)
        self.group_box.setLayout(inner_layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.group_box)
        self.setLayout(outer)

        # === Signals ===
        self.problem_name_field.textChanged.connect(self._emit_changed)
        self.problem_type_field.valueChanged.connect(self._on_problem_type_changed)
        self.num_params_field.valueChanged.connect(self._emit_changed)
        self.num_samples_field.valueChanged.connect(self._emit_changed)
        self.sampling_field.valueChanged.connect(self._emit_changed)
        self.batch_size_field.valueChanged.connect(self._emit_changed)

        # === Directory checking ===
        self._last_working_dir = self.working_dir_field.path
        self._pending_path: str | None = None

        self._dir_check_timer = QTimer(self)
        self._dir_check_timer.setSingleShot(True)
        self._dir_check_timer.setInterval(800)
        self._dir_check_timer.timeout.connect(self._run_directory_check)

        self.working_dir_field.pathChanged.connect(self._schedule_directory_check)
        self.working_dir_field.pathChanged.connect(self._emit_changed)

        self._update_visibility_for_problem_type()

        # store defaults for reset
        self._default_problem_type = default_problem_type
        self._default_problem_name = default_problem_name
        self._default_num_params = default_num_params
        self._default_num_samples = default_num_samples

    # ------------------------------------------------------------------
    @property
    def problem_type(self) -> str:
        return self.problem_type_field.value

    # ------------------------------------------------------------------
    def _emit_changed(self, *args):
        self.changed.emit()

    def _on_problem_type_changed(self, value: str):
        self._update_visibility_for_problem_type()
        self.problemTypeChanged.emit(value)
        self.changed.emit()

    def _update_visibility_for_problem_type(self):
        if self.problem_type_field.value == "Optimization":
            self.sampling_field.hide()
        else:
            self.sampling_field.show()

        is_opt = (self.problem_type_field.value == "Optimization")
        self.smart_scheduling_field.setVisible(is_opt)
        self.smart_scheduling_field.setEnabled(is_opt)

        show_bounds = is_opt and (self._num_objectives == 2)
        self._f1_row.setVisible(show_bounds)
        self._f1_row.setEnabled(show_bounds)
        self._f2_row.setVisible(show_bounds)
        self._f2_row.setEnabled(show_bounds)

    # ------------------------------------------------------------------
    def set_num_objectives(self, n: int) -> None:
        self._num_objectives = max(0, int(n))
        self._update_visibility_for_problem_type()

    def set_num_parameters(self, num_params: int) -> None:
        """Auto-fill inner iterations as 10000 * number of parameters (unless user changed it)."""
        try:
            n = max(0, int(num_params))
        except Exception:
            n = 0

        auto = str(10000 * n)

        cur = (getattr(self.num_inner_iterations_field, "text", "") or "").strip()
        if (not cur) or (self._last_inner_iter_autofill is not None and cur == self._last_inner_iter_autofill):
            # IMPORTANT: don't mark study dirty when we auto-fill defaults
            le = None
            try:
                le = self.num_inner_iterations_field._edit  # StringField convention in this project
            except Exception:
                le = None

            if le is not None:
                le.blockSignals(True)
            try:
                self.num_inner_iterations_field.text = auto
                self._last_inner_iter_autofill = auto
            finally:
                if le is not None:
                    le.blockSignals(False)

    def _schedule_directory_check(self, path: str):
        self._pending_path = path
        self._dir_check_timer.start()

    def _run_directory_check(self):
        new_path = (self._pending_path or "").strip()
        if not new_path:
            return

        if not os.path.isdir(new_path):
            resp = QMessageBox.question(
                self,
                "Create Directory?",
                f"The directory does not exist. Shall we create: \n{new_path}?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(new_path, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    self.working_dir_field.blockSignals(True)
                    self.working_dir_field.path = self._last_working_dir
                    self.working_dir_field.blockSignals(False)
                    return
            else:
                self.working_dir_field.blockSignals(True)
                self.working_dir_field.path = self._last_working_dir
                self.working_dir_field.blockSignals(False)
                return

        self._last_working_dir = new_path

    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, str | int]:
        data = {
            "problem_name": self.problem_name_field.text,
            "problem_type": self.problem_type,
            "number_of_parameters": int(self.num_params_field.value),
            "number_of_samples": int(self.num_samples_field.value),
            "batch_size": int(self.batch_size_field.value),
            "working_directory": self.working_dir_field.path,
        }

        if self.problem_type != "Optimization":
            data["sampling_method"] = self.sampling_field.value

        if self.problem_type == "Optimization":
            data["smart_scheduling"] = self.smart_scheduling_field.value

        if self.problem_type == "Optimization" and self._num_objectives == 2:
            data["f1_min"] = self.f1_min_field.text
            data["f1_max"] = self.f1_max_field.text
            data["f2_min"] = self.f2_min_field.text
            data["f2_max"] = self.f2_max_field.text

        return data

    # ------------------------------------------------------------------
    def to_xml(self, *, root_tag: str = "general_settings", include_empty: bool = False) -> ET.Element:
        root = ET.Element(root_tag)

        ET.SubElement(root, "problem_type").text = self.problem_type
        ET.SubElement(root, "name").text = self.problem_name_field.text.strip()
        ET.SubElement(root, "dimension").text = str(int(self.num_params_field.value))
        ET.SubElement(
            root,
            "number_of_function_evaluations"
        ).text = str(int(self.num_samples_field.value))

        if self.problem_type != "Optimization":
            ET.SubElement(root, "sampling_method").text = self.sampling_field.value

        ET.SubElement(root, "working_directory").text = self.working_dir_field.path
        ET.SubElement(root, "batch_size").text = str(int(self.batch_size_field.value))

        if self.problem_type == "Optimization":
            ET.SubElement(root, "smart_scheduling").text = self.smart_scheduling_field.value

        is_opt = (self.problem_type_field.value == "Optimization")
        if is_opt and self._num_objectives == 2:
            # CHANGED: write only non-empty bounds
            f1_min = self.f1_min_field.text.strip()
            f1_max = self.f1_max_field.text.strip()
            f2_min = self.f2_min_field.text.strip()
            f2_max = self.f2_max_field.text.strip()

            if f1_min:
                ET.SubElement(root, "f1_min").text = f1_min
            if f1_max:
                ET.SubElement(root, "f1_max").text = f1_max
            if f2_min:
                ET.SubElement(root, "f2_min").text = f2_min
            if f2_max:
                ET.SubElement(root, "f2_max").text = f2_max

        # NEW
        iters = (self.num_inner_iterations_field.text or "").strip()
        if iters or include_empty:
            ET.SubElement(root, "number_of_inner_iterations").text = iters

        return root

    def from_xml(self, element: ET.Element | None) -> None:
        if element is None:
            return

        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        # Validate problem_type first; if invalid, warn + reset + abort loading
        ptype = get("problem_type")
        if ptype and ptype not in self._ALLOWED_PROBLEM_TYPES:
            QMessageBox.warning(
                self,
                "Invalid XML",
                "Invalid 'problem_type' in the XML file:\n"
                f"  {ptype}\n\n"
                "Allowed values are:\n"
                "  - Optimization\n"
                "  - Design of Experiment\n"
                "  - Uncertainty Quantification\n\n"
                "The XML file was not loaded; default settings were restored.",
            )
            self._reset_to_defaults()
            return

        # NEW: validate smart_scheduling if present (only On/Off)
        ss = get("smart_scheduling")
        if ss and ss not in ("On", "Off"):
            QMessageBox.warning(
                self,
                "Invalid XML",
                "Invalid 'smart_scheduling' in the XML file:\n"
                f"  {ss}\n\n"
                "Allowed values are:\n"
                "  - On\n"
                "  - Off\n\n"
                "The XML file was not loaded; default settings were restored.",
            )
            self._reset_to_defaults()
            return

        if ptype:
            self.problem_type_field.value = ptype

        try:
            self.num_params_field.value = int(get("dimension"))
            self.num_samples_field.value = int(get("number_of_function_evaluations"))
            self.batch_size_field.value = int(get("batch_size"))
        except Exception:
            pass

        if (sm := get("sampling_method")):
            self.sampling_field.value = sm

        if (wd := get("working_directory")):
            self.working_dir_field.path = wd

        # If Optimization: apply smart scheduling (default Off otherwise)
        if self.problem_type_field.value == "Optimization":
            self.smart_scheduling_field.value = ss or "Off"
        else:
            self.smart_scheduling_field.value = "Off"

        # NEW: load bounds (even if currently hidden)
        self.f1_min_field.text = get("f1_min")
        self.f1_max_field.text = get("f1_max")
        self.f2_min_field.text = get("f2_min")
        self.f2_max_field.text = get("f2_max")

        # NEW
        el = element.find("number_of_inner_iterations")
        self.num_inner_iterations_field.text = el.text.strip() if el is not None and el.text else ""

        self._update_visibility_for_problem_type()

    def _reset_to_defaults(self) -> None:
        """Reset UI fields to defaults."""
        self.problem_type_field.value = self._default_problem_type
        self.problem_name_field.text = self._default_problem_name
        self.num_params_field.value = self._default_num_params
        self.num_samples_field.value = self._default_num_samples
        self.batch_size_field.value = 1
        self.sampling_field.value = "Latin Hypercube"
        self.smart_scheduling_field.value = "Off"
        self.working_dir_field.path = ""
        self.f1_min_field.text = ""
        self.f1_max_field.text = ""
        self.f2_min_field.text = ""
        self.f2_max_field.text = ""
        self.num_inner_iterations_field.text = ""
        self._update_visibility_for_problem_type()

    def _on_problem_name_changed(self, text: str) -> None:
        """
        Validate problem name:
          - must not be empty
          - must not contain ANY whitespace (spaces, tabs, etc.)
          - only letters, digits, underscore allowed
        """
        import re

        # do NOT strip; we want to catch trailing/leading spaces as invalid
        name = text

        # reject if any whitespace character present
        if not name or any(ch.isspace() for ch in name):
            is_valid = False
        else:
            is_valid = bool(re.fullmatch(r"[A-Za-z0-9_]+", name))

        self._set_problem_name_valid(is_valid)

        self.changed.emit()

    def _set_problem_name_valid(self, valid: bool) -> None:
        if self._problem_name_valid == valid:
            return
        self._problem_name_valid = valid

        # access underlying QLineEdit from StringField
        edit = self.problem_name_field._edit  # adjust if you expose it differently

        if valid:
            edit.setStyleSheet("")
            edit.setToolTip("")
        else:
            edit.setStyleSheet(self._invalid_name_style)
            edit.setToolTip(
                "Invalid name. Use only letters, digits, and underscore; "
                "no spaces or special characters."
            )

    def _is_numeric_text(self, s: str) -> bool:
        """Return True if s is a valid number representation."""
        s = (s or "").strip()
        if s == "":
            return True  # allow empty (no value)
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _validate_numeric_field(self, field) -> None:
        """Apply/remove red border based on numeric validity of the field."""
        text = field.text() if callable(getattr(field, "text", None)) else getattr(field, "text", "")
        text = text if isinstance(text, str) else str(text)

        valid = self._is_numeric_text(text)

        # access underlying QLineEdit from StringField
        edit = field._edit  # consistent with your problem_name_field usage

        if valid:
            edit.setStyleSheet("")
            edit.setToolTip("")
        else:
            edit.setStyleSheet(self._invalid_numeric_style)
            edit.setToolTip("Invalid value. Please enter a numeric value (e.g. -1, 0.5, 1e-3).")
