# constraint_function_widget.py
from __future__ import annotations
from typing import Optional, Dict, Tuple

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
from constraint_definition import ConstraintDefinition


class ConstraintFunction(QWidget):
    """
    Widget for configuring a Constraint Function.

    Fields:
      - Name
      - Host (local or remote)
      - Definition (ConstraintDefinition)
      - Executable / Training / Design / Output files
      - Working directory (local or remote)
      - RemoteServerWidget (visible only when host == remote)
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

        # --- Defaults ---
        self._default_name = "ConstraintFunction"
        self._default_host = "local host"
        self._default_paths = ["", "", "", ""]
        self._default_workdir = os.getcwd()

        # --- Main container ---
        self.group_box = QGroupBox("Constraint Function", self)
        # Give the group box a wider initial width to prevent horizontal stretching
        approx_width = label_width + field_width + 230  # small margin for spacing/buttons
        self.group_box.setMinimumWidth(approx_width)
        self.group_box.setMaximumWidth(approx_width + 230)
        self.group_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # --- Fields ---
        self.name_field = StringField(
            "Name",
            default=self._default_name,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.host_field = StringOptionsField(
            "Host",
            value=self._default_host,
            options=["local host", "remote host"],
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.definition_field = ConstraintDefinition(
            "Definition",
            default="",  # no default text, widget handles its own placeholder
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )

        self.file_fields = FilePathField(
            ["Executable file name", "Training data file", "Design variables file", "Output file"],
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

        self.remote_server_widget = RemoteServerWidget(
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.remote_server_widget.setVisible(False)

        self.clear_button = QPushButton("Clear", self.group_box)
        self.clear_button.clicked.connect(self.clear_fields)

        # --- Layout setup ---
        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(8, 16, 8, 8)
        inner_layout.setSpacing(5)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        inner_layout.addWidget(self.name_field)
        inner_layout.addWidget(self.host_field)
        inner_layout.addWidget(self.definition_field)

        # Fix alignment for file_fields
        self.file_fields.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        inner_layout.addWidget(self.file_fields)
        if hasattr(self.file_fields, "layout"):
            self.file_fields.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Fix alignment for working_dir_field
        self.working_dir_field.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        inner_layout.addWidget(self.working_dir_field)
        if hasattr(self.working_dir_field, "layout"):
            self.working_dir_field.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)

        inner_layout.addWidget(self.remote_server_widget)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_button)
        inner_layout.addLayout(btn_row)

        self.group_box.setLayout(inner_layout)
        self.group_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.group_box)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setLayout(outer_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # --- Signals ---
        self.name_field.textChanged.connect(self.changed.emit)
        self.host_field.valueChanged.connect(self._on_host_changed)
        self.definition_field.textChanged.connect(self.changed.emit)
        if hasattr(self.file_fields, "pathChanged"):
            self.file_fields.pathChanged.connect(lambda _: self.changed.emit())
        self.working_dir_field.pathChanged.connect(lambda _: self.changed.emit())
        self.remote_server_widget.changed.connect(self.changed.emit)

    # ==============================================================
    # Core methods
    # ==============================================================

    def clear_fields(self) -> None:
        self.name_field.text = self._default_name
        self.host_field.value = self._default_host
        self.definition_field.text = ""
        self.file_fields.set_paths(list(self._default_paths))
        self.working_dir_field.path = self._default_workdir
        self.remote_server_widget.setVisible(False)
        self.remote_server_widget.set_values(hostname="", username="", port="22")
        self.changed.emit()

    # --------------------------------------------------------------
    def snapshot(self) -> Dict[str, str | Dict[str, str]]:
        paths = self.file_fields.paths
        definition_raw = self.definition_field.text.strip()
        data: Dict[str, str | Dict[str, str]] = {
            "name": self.name_field.text.strip(),
            "host": self.host_field.value.strip(),
            "definition": definition_raw,
            "executable_filename": paths[0],
            "training_data_filename": paths[1],
            "design_vector_filename": paths[2],
            "output_filename": paths[3],
            "working_directory": self.working_dir_field.path.strip(),
        }
        if self.host_field.value.lower() == "remote host":
            data["remote_server"] = self.remote_server_widget.snapshot()
        return data

    # --------------------------------------------------------------

    def to_xml(
        self,
        *,
        root_tag: str = "constraint_function",
        include_empty: bool = False,
        label_attr: str = ""  # accepted but ignored
    ) -> ET.Element:
        """
        Serialize the constraint function to XML.
    
        - root_tag is forced lowercase "constraint_function"
        - include_empty=True → also creates empty tags
        - label_attr is accepted for compatibility but ignored
        """
        root_tag = "constraint_function"  # enforce lowercase tag name
        root = ET.Element(root_tag)
    
        # Helper: add tag only if non-empty or include_empty=True
        def add_tag(tag: str, text: str):
            if text or include_empty:
                ET.SubElement(root, tag).text = text
    
        # --- Basic info ---
        add_tag("name", self.name_field.text.strip())
        add_tag("host", self.host_field.value.strip())
    
        # --- Constraint definition ---
        s = self.definition_field.text.strip()
        if s:
            m = re.match(r'^(>=|<=|>|<|==|!=)\s*(-?\d+(\.\d+)?)$', s)
            if m:
                op, val = m.group(1), m.group(2)
                op_map = {">": "gt", ">=": "ge", "<": "lt", "<=": "le", "==": "eq", "!=": "ne"}
                add_tag("constraint_type", op_map.get(op, op))
                add_tag("constraint_value", val)
            elif include_empty:
                add_tag("constraint_type", "")
                add_tag("constraint_value", "")
        elif include_empty:
            add_tag("constraint_type", "")
            add_tag("constraint_value", "")
    
        # --- File paths ---
        paths = self.file_fields.paths
        tags = [
            "executable_filename",
            "training_data_filename",
            "design_vector_filename",
            "output_filename",
        ]
        for tag, val in zip(tags, paths):
            add_tag(tag, val.strip())
    
        # --- Working directory / remote server ---
        wd = self.working_dir_field.path.strip()
        host_lower = self.host_field.value.lower()

        # always save working directory as <working_directory>
        add_tag("working_directory", wd)

        # if remote host, also append <remote_server> block
        if host_lower == "remote host" and self.remote_server_widget is not None:
            rs_el = self.remote_server_widget.to_xml("remote_server")
            root.append(rs_el)

        return root


  

    def to_xml_string(self, **kwargs) -> str:
        el = self.to_xml(**kwargs)
        xml_bytes = ET.tostring(el, encoding="utf-8")
        import xml.dom.minidom as minidom
        parsed = minidom.parseString(xml_bytes)
        pretty = parsed.toprettyxml(indent="  ")
        return "\n".join(
            line for line in pretty.splitlines()
            if line.strip() and not line.strip().startswith("<?xml")
        )

    # --------------------------------------------------------------
    def from_xml(self, element: ET.Element) -> None:
        """
        Load constraint function fields from simplified lowercase XML.
        """
        def get(tag: str) -> str:
            el = element.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        self.name_field.text = get("name") or self._default_name
        host = get("host") or self._default_host
        self.host_field.value = host
        self.remote_server_widget.setVisible(host.lower() == "remote host")

        # Constraint definition
        ctype = get("constraint_type")
        cval = get("constraint_value")
        if ctype and cval:
            op_map = {"gt": ">", "ge": ">=", "lt": "<", "le": "<=", "eq": "==", "ne": "!="}
            self.definition_field.text = f"{op_map.get(ctype.strip().lower(), ctype)} {cval}"

        # Files
        paths = [
            get("executable_filename"),
            get("training_data_filename"),
            get("design_vector_filename"),
            get("output_filename"),
        ]
        self.file_fields.set_paths(paths)

        # Working directory (local or remote)
        wd = get("working_directory") or get("remote_working_directory")
        if wd:
            self.working_dir_field.path = wd

        # Remote server section
        rs_el = element.find("remote_server")
        if rs_el is not None:
            self.remote_server_widget.from_xml(rs_el)
            self.remote_server_widget.setVisible(True)

    # --------------------------------------------------------------
    def _on_host_changed(self, value: str) -> None:
        is_remote = value.strip().lower() == "remote host"
        self.remote_server_widget.setVisible(is_remote)
        self.changed.emit()


# ---------------- Demo ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ConstraintFunction(label_width=180, field_width=360, button_size=32)
    w.setWindowTitle("ConstraintFunction — Demo")
    w.show()

    def _about_to_quit():
        print("Snapshot:", w.snapshot())
        print("XML:")
        xml = w.to_xml_string()
        print(xml)
        el = ET.fromstring(xml)
        w.from_xml(el)
        print("Reloaded Snapshot:", w.snapshot())

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
