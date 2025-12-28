from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QApplication, QGroupBox,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from xml.etree import ElementTree as ET
import sys, os

from string_field import StringField
from integer_spinbox_field import IntegerSpinBoxField
from string_options_field import StringOptionsField
from directory_path_field import DirectoryPathField


class GeneralSettings(QWidget):
    """
    Composite widget for general study settings.

    Single source of truth for:
      - problem_type

    Emits:
      - changed(): any field changed
      - problemTypeChanged(str): problem type changed
    """

    changed = pyqtSignal()
    problemTypeChanged = pyqtSignal(str)

    def __init__(
        self,
        *,
        label_width: int = 200,
        text_field_width: int = 600,
        int_field_width: int = 120,
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

        # === Layout ===
        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(16, 16, 16, 16)
        inner_layout.setSpacing(10)

        for w in (
            self.problem_name_field,
            self.problem_type_field,
            self.num_params_field,
            self.num_samples_field,
            self.sampling_field,
            self.batch_size_field,
            self.working_dir_field,
        ):
            inner_layout.addWidget(w, alignment=Qt.AlignmentFlag.AlignLeft)

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

    # ------------------------------------------------------------------
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

        return data

    # ------------------------------------------------------------------
    def to_xml(self, *, root_tag: str = "general_settings") -> ET.Element:
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

        return root

    def from_xml(self, element: ET.Element | None) -> None:
        if element is None:
            return

        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        if (ptype := get("problem_type")):
            self.problem_type_field.value = ptype

        if (name := get("name")):
            self.problem_name_field.text = name

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

        self._update_visibility_for_problem_type()

    def _on_problem_name_changed(self, text: str) -> None:
        """
        Validate problem name:
          - no whitespace
          - only letters, digits, underscore
        """
        import re

        name = text.strip()
        is_valid = bool(name and re.fullmatch(r"[A-Za-z0-9_]+", name))

        self._set_problem_name_valid(is_valid)

        # preserve existing changed() behavior
        self.changed.emit()

    def _set_problem_name_valid(self, valid: bool) -> None:
        if self._problem_name_valid == valid:
            return
        self._problem_name_valid = valid

        # access underlying QLineEdit from StringField
        # adjust attribute if your StringField exposes it differently
        edit = self.problem_name_field._edit

        if valid:
            edit.setStyleSheet("")
            edit.setToolTip("")
        else:
            edit.setStyleSheet(self._invalid_name_style)
            edit.setToolTip(
                "Invalid name. Use only letters, digits, and underscore; "
                "no spaces or special characters."
            )
