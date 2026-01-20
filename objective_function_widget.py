# objective_function_widget.py
from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QApplication, QSizePolicy, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from xml.etree import ElementTree as ET
import sys
import os
import re
from PyQt6.QtWidgets import QLineEdit



from string_field import StringField
from string_options_field import StringOptionsField
from file_path_field import FilePathField
from directory_path_field import DirectoryPathField
from remote_server_widget import RemoteServerWidget


class ObjectiveFunction(QWidget):
    """
    Composite widget for configuring an Objective Function.

    Rules:
      - Derivative information visible only for Optimization
      - Gradient-enhanced adds two extra file paths
    """

    changed = pyqtSignal()

    def __init__(
        self,
        *,
        label_width: int = 180,
        field_width: int = 360,
        button_size: int = 40,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ------------------------------------------------------------
        # Internal state
        # ------------------------------------------------------------
        self._problem_type: str | None = None
        self._default_derivative_info = "None"

        self._default_name = "ObjectiveFunction"
        self._default_execution_location = "local"
        self._default_workdir = os.getcwd()

        # ------------------------------------------------------------
        # Group box
        # ------------------------------------------------------------
        self.group_box = QGroupBox("Objective Function", self)

        approx_width = label_width + field_width + 200
        self.group_box.setMinimumWidth(approx_width)
        self.group_box.setMaximumWidth(approx_width + 200)
        self.group_box.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )

        # ------------------------------------------------------------
        # Fields
        # ------------------------------------------------------------
        self.name_field = StringField(
            "Name",
            default=self._default_name,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.name_field.textChanged.connect(lambda _t: self.changed.emit())

        self._name_valid = True

        self._invalid_name_style = """
        QLineEdit {
            border: 2px solid red;
            border-radius: 3px;
        }
        """

        # NEW: Alias field
        self.alias_field = StringField(
            "Alias",
            default="",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.alias_field.textChanged.connect(self._on_alias_changed)

        # NEW: tooltip ("balloon") for Alias field
        alias_edit = self.alias_field.findChild(QLineEdit)
        if alias_edit is not None:
            alias_edit.setToolTip(
                "Alias (optional): Delegate evaluation to another process.\n"
                "Enter the name of an existing objective/constraint that will also compute "
                "this objective's value.\n"
                "When set, local executable and design-file inputs are unneccesary and disabled."
            )

        self.execution_location_field = StringOptionsField(
            "Execution location",
            value=self._default_execution_location,
            options=["local", "remote"],
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.derivative_info_field = StringOptionsField(
            "Derivative information",
            value=self._default_derivative_info,
            options=["None", "Gradient-enhanced", "Tangent-enhanced"],
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.derivative_info_field.hide()

        # --- File paths ---
        self.exec_file = FilePathField(
            "Executable file name",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        # NEW: tooltip for Executable file name entry
        if hasattr(self.exec_file, "_fields") and self.exec_file._fields:
            _lbl, edit, _btn = self.exec_file._fields[0]
            if isinstance(edit, QLineEdit):
                edit.setToolTip(
                    "Executable file used to evaluate this objective.\n"
                    "Can be any runnable program (binary), a shell script (.sh), or a Python script (.py).\n"
                    "It will be executed during runs to produce the objective output.\n"
                    "Note: If an Alias is provided, this field is not used and becomes disabled."
                )

        # NEW: apply initial state (in case alias has a default)
        self._sync_executable_with_alias()

        self.grad_exec_file = FilePathField(
            "Gradient executable file name",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.grad_exec_file.hide()

        self.training_file = FilePathField(
            "Training data file",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
            filters="CSV files (*.csv)",  # only CSV allowed in dialog
        )
        # validate & normalize on change
        self.training_file.pathChanged.connect(self._on_training_file_changed)

        # NEW: add user hint in the entry field
        if hasattr(self.training_file, "_fields") and self.training_file._fields:
            _label, edit, _btn = self.training_file._fields[0]
            edit.setPlaceholderText("Specify a CSV file (*.csv)")

        self.design_file = FilePathField(
            "Design variables file",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        # NEW: validate filename
        self.design_file.pathChanged.connect(lambda _p: self._validate_filename_field(self.design_file))

        self.output_file = FilePathField(
            "Output file",
            path="",
            select_mode="save_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        # NEW: validate filename
        self.output_file.pathChanged.connect(lambda _p: self._validate_filename_field(self.output_file))

        self.grad_output_file = FilePathField(
            "Gradient output file",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.grad_output_file.hide()

        self.working_dir_field = DirectoryPathField(
            "Working directory",
            path=self._default_workdir,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        # ------------------------------------------------------------
        # Remote server
        # ------------------------------------------------------------
        self.remote_server_widget = RemoteServerWidget(
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.remote_server_widget.setVisible(False)

        # ------------------------------------------------------------
        # Clear button
        # ------------------------------------------------------------
        self.clear_button = QPushButton("Clear", self.group_box)
        self.clear_button.clicked.connect(self.clear_fields)

        # ------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------
        inner = QVBoxLayout(self.group_box)
        inner.setContentsMargins(8, 16, 8, 8)
        inner.setSpacing(5)
        inner.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        for w in (
            self.name_field,
            self.alias_field,  # NEW: ensure alias_field is added to the layout
            self.execution_location_field,
            self.derivative_info_field,
            self.exec_file,
            self.grad_exec_file,
            self.training_file,
            self.design_file,
            self.output_file,
            self.grad_output_file,
            self.working_dir_field,
            self.remote_server_widget,
        ):
            inner.addWidget(w)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_button)
        inner.addLayout(btn_row)

        outer = QVBoxLayout(self)
        outer.addWidget(self.group_box)
        self.setLayout(outer)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # ------------------------------------------------------------
        # Signals
        # ------------------------------------------------------------
        self.name_field.textChanged.connect(self._on_name_changed)

        self.execution_location_field.valueChanged.connect(
            self._on_execution_location_changed
        )
        self.derivative_info_field.valueChanged.connect(
            self._on_derivative_info_changed
        )

        for w in (
            self.exec_file,
            self.grad_exec_file,
            self.training_file,
            self.design_file,
            self.output_file,
            self.grad_output_file,
            self.working_dir_field,
        ):
            if hasattr(w, "pathChanged"):
                w.pathChanged.connect(lambda _: self.changed.emit())

        self.remote_server_widget.changed.connect(self.changed.emit)

        # NEW: validate executable existence whenever path/location changes
        self.exec_file.pathChanged.connect(lambda _p: self._validate_local_executable())
        self.execution_location_field.valueChanged.connect(lambda _v: self._validate_local_executable())

    # ==============================================================
    # Problem type integration
    # ==============================================================
    def set_problem_type(self, problem_type: str | None) -> None:
        self._problem_type = problem_type
        self.derivative_info_field.setVisible(problem_type == "Optimization")

    def _on_derivative_info_changed(self, value: str) -> None:
        is_grad = value == "Gradient-enhanced"
        self.grad_exec_file.setVisible(is_grad)
        self.grad_output_file.setVisible(is_grad)
        self.changed.emit()

    def _on_execution_location_changed(self, value: str) -> None:
        self.remote_server_widget.setVisible(value.lower() == "remote")
        self.changed.emit()

    # ==============================================================
    # Core behavior
    # ==============================================================
    def clear_fields(self) -> None:
        self.name_field.text = self._default_name
        self.alias_field.text = ""  # NEW: clear alias field
        self.execution_location_field.value = self._default_execution_location
        self.derivative_info_field.value = self._default_derivative_info

        for w in (
            self.exec_file,
            self.grad_exec_file,
            self.training_file,
            self.design_file,
            self.output_file,
            self.grad_output_file,
        ):
            w.path = ""

        self.working_dir_field.path = self._default_workdir
        self.remote_server_widget.setVisible(False)
        self.remote_server_widget.set_values(
            hostname="", username="", port="22"
        )
        self.changed.emit()

    # --------------------------------------------------
    # Alias behavior: disables executable when alias is set
    # --------------------------------------------------
    def _on_alias_changed(self, text: str) -> None:
        """
        Alias rules:
          - empty is allowed
          - if non-empty: only letters/digits/underscore; no whitespace
        Invalid alias is shown with a red border.
        """
        alias = text  # do NOT strip; "abc " should be invalid

        if not alias:
            valid = True
        elif any(ch.isspace() for ch in alias):
            valid = False
        else:
            valid = bool(re.fullmatch(r"[A-Za-z0-9_]+", alias))

        # apply red-border feedback to alias field's QLineEdit
        edit = self.alias_field.findChild(QLineEdit)
        if edit is not None:
            if valid:
                edit.setStyleSheet("")
                edit.setToolTip("")
            else:
                edit.setStyleSheet(self._invalid_name_style)
                edit.setToolTip(
                    "Invalid alias. Use only letters, digits, and underscore; "
                    "no spaces or special characters."
                )

        # Only disable/clear executable/design fields if alias is non-empty AND valid
        if valid and alias.strip():
            self._sync_executable_with_alias()
        else:
            # if alias is empty OR invalid, ensure fields are enabled
            # (so user can still provide executable paths)
            self.alias_field.textChanged.disconnect(self._on_alias_changed)  # avoid recursion if any
            try:
                # re-enable without clearing if alias invalid/empty
                alias_before = self.alias_field.text
                self.alias_field.text = alias_before
            finally:
                self.alias_field.textChanged.connect(self._on_alias_changed)

            # force alias_active = False behavior by temporarily treating alias as empty
            # simplest: manually enable the fields here
            inactive_style = "QLineEdit { background: #f0f0f0; color: #666; }"

            def _enable_file_field(field) -> None:
                if field is None or not hasattr(field, "_fields") or not field._fields:
                    return
                _lbl, e, b = field._fields[0]
                e.setEnabled(True)
                b.setEnabled(True)
                # don't clobber red-border validation on other fields; only remove inactive gray
                if e.styleSheet() == inactive_style:
                    e.setStyleSheet("")

            _enable_file_field(getattr(self, "exec_file", None))
            _enable_file_field(getattr(self, "design_file", None))

        self.changed.emit()

    def _sync_executable_with_alias(self) -> None:
        """
        If alias is non-empty:
          - clear and disable 'Executable file name'
          - clear and disable 'Design variables file' (when available)
        Else:
          - re-enable both
        """
        alias_active = bool((self.alias_field.text or "").strip())
        inactive_style = "QLineEdit { background: #f0f0f0; color: #666; }"

        def _toggle_file_field(field, *, clear: bool) -> None:
            if field is None or not hasattr(field, "_fields") or not field._fields:
                return
            _lbl, edit, btn = field._fields[0]

            if alias_active:
                # CHANGED: if inactive, it must be empty (always clear)
                try:
                    field.path = ""
                except Exception:
                    pass
                edit.blockSignals(True)
                edit.setText("")
                edit.blockSignals(False)

                edit.setEnabled(False)
                btn.setEnabled(False)
                edit.setStyleSheet(inactive_style)
            else:
                edit.setEnabled(True)
                btn.setEnabled(True)
                edit.setStyleSheet("")

        # Executable file (always exists when this is called)
        _toggle_file_field(getattr(self, "exec_file", None), clear=True)

        # Design variables file (may not exist yet during __init__)
        _toggle_file_field(getattr(self, "design_file", None), clear=True)

    # --------------------------------------------------
    # Filename validation for design/output files
    # --------------------------------------------------
    def _validate_filename_field(self, field: "FilePathField") -> None:
        """
        Validate file name (basename) for Design variables file / Output file.

        Regex:
          ^[A-Za-z0-9][A-Za-z0-9 _.-]{0,198}[A-Za-z0-9]$
        """
        if field is None or not hasattr(field, "_fields") or not field._fields:
            return

        # underlying QLineEdit in FilePathField
        _lbl, edit, _btn = field._fields[0]
        if not isinstance(edit, QLineEdit):
            return

        path = (field.path or "").strip()
        # allow empty here (so user can decide), but mark invalid if non-empty and bad
        if not path:
            edit.setStyleSheet("")
            edit.setToolTip("")
            return

        import os
        name = os.path.basename(path)

        pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\.-]{0,198}[A-Za-z0-9]$")
        ok = bool(pattern.fullmatch(name))

        if ok:
            edit.setStyleSheet("")
            edit.setToolTip("")
        else:
            edit.setStyleSheet(self._invalid_name_style)
            edit.setToolTip(
                "Invalid filename. Allowed: letters/digits; may include space, underscore, dot, hyphen; "
                "must start and end with a letter/digit; length 2-200."
            )

    def _validate_local_executable(self) -> None:
        """
        If execution location is local, executable must exist as a file.
        Missing executable is shown with a red border.
        """
        try:
            is_local = (self.execution_location_field.value or "").strip().lower() == "local"
        except Exception:
            is_local = True

        # underlying QLineEdit in FilePathField
        edit = None
        if hasattr(self.exec_file, "_fields") and self.exec_file._fields:
            _lbl, e, _btn = self.exec_file._fields[0]
            edit = e

        if edit is None:
            return

        if not is_local:
            # remote: do not require local executable existence
            edit.setStyleSheet("")
            edit.setToolTip("")
            return

        path = (self.exec_file.path or "").strip()
        ok = bool(path) and os.path.isfile(path)

        if ok:
            edit.setStyleSheet("")
            edit.setToolTip("")
        else:
            edit.setStyleSheet(self._invalid_name_style)
            edit.setToolTip("Executable file not found. Please select an existing file for local execution.")

    # ==============================================================
    # Snapshot / XML
    # ==============================================================
    def snapshot(self) -> Dict[str, str | Dict[str, str]]:
        data = {
            "name": self.name_field.text,
            "alias": self.alias_field.text,  # NEW
            "execution_location": self.execution_location_field.value,
            "executable_filename": self.exec_file.path,
            "training_data_filename": self.training_file.path,
            "design_vector_filename": self.design_file.path,
            "output_filename": self.output_file.path,
            "working_directory": self.working_dir_field.path,
        }

        if self._problem_type == "Optimization":
            data["derivative_information"] = self.derivative_info_field.value
            if self.derivative_info_field.value == "Gradient-enhanced":
                data["gradient_executable_filename"] = self.grad_exec_file.path
                data["gradient_output_filename"] = self.grad_output_file.path

        if self.execution_location_field.value == "remote":
            data["remote_server"] = self.remote_server_widget.snapshot()

        return data

    def to_xml(self, *, include_empty: bool = False) -> ET.Element:
        root = ET.Element("objective_function")

        def add(tag: str, text: str):
            if text or include_empty:
                ET.SubElement(root, tag).text = text

        add("name", self.name_field.text.strip())

        # CHANGED: write <alias> only if non-empty (or include_empty=True)
        alias = self.alias_field.text.strip()
        if alias or include_empty:
            add("alias", alias)

        add("execution_location", self.execution_location_field.value)

        if self._problem_type == "Optimization":
            add("derivative_information", self.derivative_info_field.value)

            if self.derivative_info_field.value == "Gradient-enhanced":
                add("gradient_executable_filename", self.grad_exec_file.path)
                add("gradient_output_filename", self.grad_output_file.path)

        add("executable_filename", self.exec_file.path)
        add("training_data_filename", self.training_file.path)
        add("design_vector_filename", self.design_file.path)
        add("output_filename", self.output_file.path)
        add("working_directory", self.working_dir_field.path)

        if self.execution_location_field.value == "remote":
            root.append(self.remote_server_widget.to_xml("remote_server"))

        return root

    def from_xml(self, element: ET.Element) -> None:
        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        self.name_field.text = get("name") or self._default_name
        self.alias_field.text = get("alias")  # NEW
        self.execution_location_field.value = (
            get("execution_location") or self._default_execution_location
        )

        if (di := get("derivative_information")):
            self.derivative_info_field.value = di

        self.exec_file.path = get("executable_filename")
        self.training_file.path = get("training_data_filename")
        self.design_file.path = get("design_vector_filename")
        self.output_file.path = get("output_filename")
        self.grad_exec_file.path = get("gradient_executable_filename")
        self.grad_output_file.path = get("gradient_output_filename")
        self.working_dir_field.path = get("working_directory")

        # NEW: refresh validation after loading values
        self._validate_local_executable()

        if element.find("remote_server") is not None:
            self.remote_server_widget.from_xml(element.find("remote_server"))
            self.remote_server_widget.setVisible(True)

        self._on_derivative_info_changed(self.derivative_info_field.value)

    
    def _name_line_edit(self) -> QLineEdit | None:
        """
        Safely obtain the internal QLineEdit of StringField.
        """
        return self.name_field.findChild(QLineEdit)

    def _is_valid_name(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text))


    def _on_name_changed(self, text: str) -> None:
        valid = self._is_valid_name(text)
        self._name_valid = valid

        edit = self._name_line_edit()
        if edit is not None:
            if valid:
                edit.setStyleSheet("")
            else:
                edit.setStyleSheet("""
                    QLineEdit {
                        border: 2px solid red;
                        border-radius: 3px;
                    }
                """)

        self.changed.emit()


    def is_name_valid(self) -> bool:
        return self._name_valid

    def _on_training_file_changed(self, new_path: str) -> None:
        """
        Keep only basename and ensure it is a .csv file.
        Show red border if invalid.
        """
        raw = new_path.strip()
        filename = os.path.basename(raw)

        # normalize display to basename only
        if filename != self.training_file.path:
            self.training_file.path = filename

        if not filename:
            # empty is considered invalid here
            self._set_filefield_valid(
                self.training_file,
                valid=False,
                tooltip="Training data file is required and must be a .csv file.",
            )
            return

        if filename.lower().endswith(".csv"):
            self._set_filefield_valid(self.training_file, valid=True, tooltip="")
        else:
            self._set_filefield_valid(
                self.training_file,
                valid=False,
                tooltip="Training data file must have .csv extension.",
            )

    def _set_filefield_valid(self, field: FilePathField, *, valid: bool, tooltip: str) -> None:
        """
        Simple visual validation for a single-field FilePathField:
        - red border on invalid
        - normal border on valid
        """
        if not hasattr(field, "_fields") or not field._fields:
            return

        # assuming FilePathField internally stores tuples (label, edit, btn)
        label, edit, btn = field._fields[0]

        if valid:
            edit.setStyleSheet("")  # reset to default
        else:
            edit.setStyleSheet(
                "QLineEdit { border: 2px solid red; border-radius: 3px; }"
            )
        edit.setToolTip(tooltip)

# ---------------- Demo ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ObjectiveFunction()
    w.setWindowTitle("ObjectiveFunction — Demo")
    w.show()
    sys.exit(app.exec())
