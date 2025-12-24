# constraint_function_widget.py
from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QApplication,
    QSizePolicy, QGroupBox, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt
from xml.etree import ElementTree as ET
import sys, os, re

from string_field import StringField
from string_options_field import StringOptionsField
from file_path_field import FilePathField
from directory_path_field import DirectoryPathField
from remote_server_widget import RemoteServerWidget


class ConstraintFunction(QWidget):
    """
    Widget for configuring a Constraint Function.
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

        # --------------------------------------------------
        # Defaults
        # --------------------------------------------------
        self._default_name = "ConstraintFunction"
        self._default_execution_location = "local"
        self._default_paths = ["", "", "", ""]
        self._default_workdir = os.getcwd()

        # --------------------------------------------------
        # Group box
        # --------------------------------------------------
        self.group_box = QGroupBox("Constraint Function", self)
        approx_width = label_width + field_width + 230
        self.group_box.setMinimumWidth(approx_width)
        self.group_box.setMaximumWidth(approx_width + 230)
        self.group_box.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )

        # --------------------------------------------------
        # Fields
        # --------------------------------------------------
        self.name_field = StringField(
            "Name",
            default=self._default_name,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.execution_location_field = StringOptionsField(
            "Execution location",
            value=self._default_execution_location,
            options=["local", "remote"],
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.definition_field = StringField(
            "Definition",
            default="> 0.0",
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.file_fields = FilePathField(
            ["Executable file name",
             "Training data file",
             "Design variables file",
             "Output file"],
            path=list(self._default_paths),
            select_mode="open_file",
            dialog_title="Select File",
            filters=[
                ["Python (*.py)", "Executables (*.sh *.bin *.exe)", "All files (*)"],
                ["Data (*.csv *.dat *.txt)", "All files (*)"],
                ["Data (*.csv *.dat *.txt *.xml)", "All files (*)"],
                ["Data (*.dat *.txt *.csv)", "All files (*)"],
            ],
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.working_dir_field = DirectoryPathField(
            "Working directory",
            path=self._default_workdir,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        if hasattr(self.working_dir_field, "layout"):
            self.working_dir_field.layout().setAlignment(
                Qt.AlignmentFlag.AlignLeft
            )

        self.remote_server_widget = RemoteServerWidget(
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.remote_server_widget.setVisible(False)

        self.clear_button = QPushButton("Clear", self.group_box)
        self.clear_button.clicked.connect(self.clear_fields)

        # --------------------------------------------------
        # Layout
        # --------------------------------------------------
        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(8, 16, 8, 8)
        inner_layout.setSpacing(5)
        inner_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        inner_layout.addWidget(self.name_field)
        inner_layout.addWidget(self.execution_location_field)
        inner_layout.addWidget(self.definition_field)
        inner_layout.addWidget(self.file_fields)
        inner_layout.addWidget(self.working_dir_field)
        inner_layout.addWidget(self.remote_server_widget)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_button)
        inner_layout.addLayout(btn_row)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.group_box)
        outer_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.setLayout(outer_layout)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # --------------------------------------------------
        # Signals
        # --------------------------------------------------
        self.name_field.textChanged.connect(self.changed.emit)
        self.execution_location_field.valueChanged.connect(
            self._on_execution_location_changed
        )
        self.definition_field.textChanged.connect(self._on_definition_changed)

        if hasattr(self.file_fields, "pathChanged"):
            self.file_fields.pathChanged.connect(lambda _: self.changed.emit())

        self.working_dir_field.pathChanged.connect(lambda _: self.changed.emit())
        self.remote_server_widget.changed.connect(self.changed.emit)

        # initial validation
        self._on_definition_changed(self.definition_field.text)

    # ==================================================
    # Validation
    # ==================================================

    def _is_valid_definition(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        pattern = r'^[<>]\s*[+-]?\d+(\.\d+)?$'
        return re.match(pattern, text) is not None

    def _on_definition_changed(self, text: str) -> None:
        valid = self._is_valid_definition(text)
        self.definition_field.set_valid(
            valid,
            tooltip="Expected format: > 10.0 or < -3"
        )
        self.changed.emit()

    # ==================================================
    # Core logic
    # ==================================================

    def clear_fields(self) -> None:
        self.name_field.text = self._default_name
        self.execution_location_field.value = self._default_execution_location
        self.definition_field.text = ""
        self.file_fields.set_paths(list(self._default_paths))
        self.working_dir_field.path = self._default_workdir
        self.remote_server_widget.setVisible(False)
        self.remote_server_widget.set_values(
            hostname="", username="", port="22"
        )
        self.changed.emit()

    def snapshot(self) -> Dict[str, str | Dict[str, str]]:
        paths = self.file_fields.paths
        data: Dict[str, str | Dict[str, str]] = {
            "name": self.name_field.text.strip(),
            "execution_location": self.execution_location_field.value.strip(),
            "definition": self.definition_field.text.strip(),
            "executable_filename": paths[0],
            "training_data_filename": paths[1],
            "design_vector_filename": paths[2],
            "output_filename": paths[3],
            "working_directory": self.working_dir_field.path.strip(),
        }
        if self.execution_location_field.value.lower() == "remote":
            data["remote_server"] = self.remote_server_widget.snapshot()
        return data

    # ==================================================
    # XML
    # ==================================================

    def to_xml(self, *, include_empty: bool = False) -> ET.Element:
        root = ET.Element("constraint_function")

        def add(tag: str, text: str):
            if text or include_empty:
                ET.SubElement(root, tag).text = text

        add("name", self.name_field.text.strip())
        add("execution_location", self.execution_location_field.value.strip())

        s = self.definition_field.text.strip()
        if self._is_valid_definition(s):
            m = re.match(r'^([<>])\s*([+-]?\d+(\.\d+)?)$', s)
            op, val = m.group(1), m.group(2)
            add("constraint_type", "gt" if op == ">" else "lt")
            add("constraint_value", val)

        tags = [
            "executable_filename",
            "training_data_filename",
            "design_vector_filename",
            "output_filename",
        ]
        for tag, val in zip(tags, self.file_fields.paths):
            add(tag, val.strip())

        add("working_directory", self.working_dir_field.path.strip())

        if self.execution_location_field.value.lower() == "remote":
            root.append(self.remote_server_widget.to_xml("remote_server"))

        return root

    def from_xml(self, element: ET.Element) -> None:
        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        self.name_field.text = get("name") or self._default_name
        loc = get("execution_location") or self._default_execution_location
        self.execution_location_field.value = loc
        self.remote_server_widget.setVisible(loc.lower() == "remote")

        ctype = get("constraint_type")
        cval = get("constraint_value")
        if ctype and cval:
            self.definition_field.text = (
                (">" if ctype == "gt" else "<") + " " + cval
            )

        self.file_fields.set_paths([
            get("executable_filename"),
            get("training_data_filename"),
            get("design_vector_filename"),
            get("output_filename"),
        ])

        wd = get("working_directory")
        if wd:
            self.working_dir_field.path = wd

        rs_el = element.find("remote_server")
        if rs_el is not None:
            self.remote_server_widget.from_xml(rs_el)
            self.remote_server_widget.setVisible(True)

        self._on_definition_changed(self.definition_field.text)

    # --------------------------------------------------
    def _on_execution_location_changed(self, value: str) -> None:
        self.remote_server_widget.setVisible(
            value.strip().lower() == "remote"
        )
        self.changed.emit()


# --------------------------------------------------
# Demo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ConstraintFunction()
    w.setWindowTitle("ConstraintFunction — Demo")
    w.show()
    sys.exit(app.exec())
