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
        button_size: int = 32,
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

        self._name_valid = True

        self._invalid_name_style = """
        QLineEdit {
            border: 2px solid red;
            border-radius: 3px;
        }
        """

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
        )

        self.design_file = FilePathField(
            "Design variables file",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.output_file = FilePathField(
            "Output file",
            path="",
            select_mode="open_file",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

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

    # ==============================================================
    # Snapshot / XML
    # ==============================================================
    def snapshot(self) -> Dict[str, str | Dict[str, str]]:
        data = {
            "name": self.name_field.text,
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

    def to_xml(self, *, root_tag: str = "objective_function") -> ET.Element:
        root = ET.Element(root_tag)

        ET.SubElement(root, "name").text = self.name_field.text
        ET.SubElement(root, "execution_location").text = self.execution_location_field.value

        if self._problem_type == "Optimization":
            ET.SubElement(
                root, "derivative_information"
            ).text = self.derivative_info_field.value

            if self.derivative_info_field.value == "Gradient-enhanced":
                ET.SubElement(
                    root, "gradient_executable_filename"
                ).text = self.grad_exec_file.path
                ET.SubElement(
                    root, "gradient_output_filename"
                ).text = self.grad_output_file.path

        ET.SubElement(root, "executable_filename").text = self.exec_file.path
        ET.SubElement(root, "training_data_filename").text = self.training_file.path
        ET.SubElement(root, "design_vector_filename").text = self.design_file.path
        ET.SubElement(root, "output_filename").text = self.output_file.path
        ET.SubElement(root, "working_directory").text = self.working_dir_field.path

        if self.execution_location_field.value == "remote":
            root.append(self.remote_server_widget.to_xml("remote_server"))

        return root

    def from_xml(self, element: ET.Element) -> None:
        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        self.name_field.text = get("name") or self._default_name
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
    
# ---------------- Demo ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ObjectiveFunction()
    w.setWindowTitle("ObjectiveFunction — Demo")
    w.show()
    sys.exit(app.exec())
