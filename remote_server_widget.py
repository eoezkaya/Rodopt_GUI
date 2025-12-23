# remote_server_widget.py
from __future__ import annotations
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QApplication,
    QGroupBox, QSizePolicy, QLabel
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from xml.etree import ElementTree as ET
import sys, subprocess

from string_field import StringField
from directory_path_field import DirectoryPathField


class RemoteServerWidget(QWidget):
    """
    Widget for configuring a remote server connection.
    Contains hostname, username, port, and working directory.
    Live SSH connection check with colored status indicator (debounced).
    """

    changed = pyqtSignal()

    def __init__(
        self,
        *,
        label_width: int = 180,
        field_width: int = 360,
        parent: Optional[QWidget] = None,
        default_hostname: str = "",
        default_username: str = "",
        default_port: str = "22",
        default_working_dir: str = "",
    ):
        super().__init__(parent)

        self.group_box = QGroupBox("Remote Server", self)

        # --- fields ---
        self.hostname_field = StringField(
            "host",
            default=default_hostname,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.username_field = StringField(
            "user",
            default=default_username,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.port_field = StringField(
            "port",
            default=default_port,
            label_width=label_width,
            field_width=field_width,
            parent=self.group_box,
        )
        self.working_dir_field = DirectoryPathField(
            "remote working directory",
            path=default_working_dir,
            label_width=label_width,
            field_width=field_width,
            browse_enabled=False,  # user must type remote path
            parent=self.group_box,
        )

        # --- fix alignment for working_dir_field ---
        self.working_dir_field.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if hasattr(self.working_dir_field, "layout"):
            self.working_dir_field.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)

        # --- status indicator ---
        self.status_icon = QLabel()
        self.status_text = QLabel("Connection status: unknown")
        self._set_status(False, "Not checked yet")

        status_row = QHBoxLayout()
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_text)
        status_row.addStretch(1)

        # --- layout inside box ---
        inner_layout = QVBoxLayout(self.group_box)
        inner_layout.setContentsMargins(8, 16, 8, 8)
        inner_layout.setSpacing(8)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        inner_layout.addWidget(self.hostname_field)
        inner_layout.addWidget(self.username_field)
        inner_layout.addWidget(self.port_field)
        inner_layout.addWidget(self.working_dir_field)
        inner_layout.addLayout(status_row)

        self.group_box.setLayout(inner_layout)

        # --- outer layout ---
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.addWidget(self.group_box)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setLayout(outer_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # --- signals ---
        self.hostname_field.textChanged.connect(self._on_field_changed)
        self.username_field.textChanged.connect(self._on_field_changed)
        self.port_field.textChanged.connect(self._on_field_changed)
        self.working_dir_field.pathChanged.connect(lambda _=None: self.changed.emit())

        # --- debounce timer for SSH checks ---
        self._check_timer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.timeout.connect(self._check_connection)

        # initial check
        QTimer.singleShot(800, self._check_connection)

    # -------- public helpers --------
    def snapshot(self) -> Dict[str, str]:
        return {
            "hostname": self.hostname_field.text,
            "username": self.username_field.text,
            "port": self.port_field.text,
            "remote_working_directory": self.working_dir_field.path,
        }

    def get_payload(self) -> Dict[str, str]:
        data = self.snapshot()
        if not data["hostname"].strip():
            raise ValueError("RemoteServerWidget: Hostname is required.")
        if not data["username"].strip():
            raise ValueError("RemoteServerWidget: Username is required.")
        if not data["port"].strip():
            raise ValueError("RemoteServerWidget: Port is required.")
        if not data["remote_working_directory"].strip():
            raise ValueError("RemoteServerWidget: Working directory is required.")
        return data

    def set_values(
        self,
        *,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        port: Optional[str] = None,
        working_directory: Optional[str] = None,
    ) -> None:
        if hostname is not None:
            self.hostname_field.text = str(hostname)
        if username is not None:
            self.username_field.text = str(username)
        if port is not None:
            self.port_field.text = str(port)
        if working_directory is not None:
            self.working_dir_field.path = str(working_directory)
        self._schedule_check()

    # -------- XML helpers --------
    def to_xml(
        self,
        *,
        root_tag: str = "RemoteServer",
        include_empty: bool = False,
        label_attr: Optional[str] = None,
    ) -> ET.Element:
        root = ET.Element(root_tag)
        
        children = [
            self.hostname_field.to_xml(attr_label=label_attr),
            self.username_field.to_xml(attr_label=label_attr),
            self.port_field.to_xml(attr_label=label_attr),
            self.working_dir_field.to_xml(attr_label=label_attr),
        ]
        for child in children:
            text = (child.text or "").strip()
            if include_empty or text:
                root.append(child)
        return root

    def to_xml_string(self, **kwargs) -> str:
        el = self.to_xml(**kwargs)
        return ET.tostring(el, encoding="utf-8").decode("utf-8")

    def from_xml(self, element: ET.Element) -> None:
        tag_to_widget = {
            "host": self.hostname_field,
            "user": self.username_field,
            "port": self.port_field,
            "remote_working_directory": self.working_dir_field,
        }

        for child in element:
            tag = child.tag.lower()
            widget = tag_to_widget.get(tag)
            if widget and hasattr(widget, "from_xml"):
                widget.from_xml(child)

        self._schedule_check()


    # -------- SSH check --------
    def _on_field_changed(self) -> None:
        self.changed.emit()
        self._schedule_check()

    def _schedule_check(self) -> None:
        self._check_timer.start(1000)  # 1s debounce

    def _check_connection(self) -> None:
        host = self.hostname_field.text.strip()
        user = self.username_field.text.strip()
        port = self.port_field.text.strip()

        if not host or not user or not port:
            self._set_status(False, "Missing information")
            return

        ssh_target = f"{user}@{host}"
        try:
            result = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-p", port, ssh_target, "exit"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._set_status(True, f"Connected to {ssh_target}")
            else:
                msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                self._set_status(False, msg)
        except Exception as e:
            self._set_status(False, str(e))

    def _set_status(self, ok: bool, message: str) -> None:
        size = 12
        color = "green" if ok else "red"
        circle = f"""
            background-color: {color};
            border-radius: {size//2}px;
            min-width: {size}px;
            min-height: {size}px;
            max-width: {size}px;
            max-height: {size}px;
        """
        self.status_icon.setStyleSheet(circle)
        self.status_text.setText(f"Connection status: {message}")


# ---------------- Demo ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = RemoteServerWidget(
        default_hostname="elwe3.rz.rptu.de",
        default_username="student",
        default_port="22",
        default_working_dir="/home/student",
    )
    w.setWindowTitle("RemoteServerWidget — Demo")
    w.show()
    sys.exit(app.exec())
