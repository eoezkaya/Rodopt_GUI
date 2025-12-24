from __future__ import annotations
from typing import Optional, Sequence
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QApplication, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtGui import QIcon
import sys, os, re
from xml.etree import ElementTree as ET


class DirectoryPathField(QWidget):
    """
    One or multiple directory path fields.
    Each field is (Label + QLineEdit + Browse button).
    If `name` is a list, multiple fields are stacked vertically.

    Layout contract intentionally matches FilePathField:
      - Label: Fixed
      - LineEdit: Expanding (with minimum width)
      - Button: Fixed
    """
    pathChanged = pyqtSignal(str)

    def __init__(
        self,
        name: str | Sequence[str],
        path: str | Sequence[str] = "",
        *,
        label_width: int = 120,
        field_width: int = 500,
        button_size: int = 28,
        dialog_title: str = "Select directory",
        dialog_width: int = 600,
        dialog_height: int = 400,
        browse_enabled: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._browse_enabled = browse_enabled

        names = [name] if isinstance(name, str) else list(name)
        if isinstance(path, str):
            paths = [path] + [""] * (len(names) - 1)
        else:
            paths = list(path) + [""] * (len(names) - len(path))

        self._fields: list[tuple[QLabel, QLineEdit, QPushButton]] = []

        outer_layout = QVBoxLayout(self) if len(names) > 1 else QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(6)

        self._dialog_title = dialog_title
        self._dialog_width = dialog_width
        self._dialog_height = dialog_height

        for nm, p in zip(names, paths, strict=False):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            # Label (fixed)
            label = QLabel(nm, self)
            if label_width > 0:
                label.setFixedWidth(label_width)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            # Line edit (EXPANDING, matches FilePathField)
            edit = QLineEdit(self)
            edit.setText(p)
            if field_width > 0:
                edit.setMinimumWidth(field_width)
            edit.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed
            )

            # Browse button (fixed)
            btn = QPushButton(self)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            if button_size > 0:
                btn.setFixedSize(QSize(button_size, button_size))

            icon_path = os.path.join("images", "folder_open.svg")
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(
                    QSize(max(1, button_size - 2), max(1, button_size - 2))
                )
            else:
                btn.setText("...")

            btn.setEnabled(browse_enabled)

            row.addWidget(label)
            row.addWidget(edit)
            row.addWidget(btn)

            self._fields.append((label, edit, btn))
            outer_layout.addLayout(row)

            btn.clicked.connect(lambda _, e=edit: self._browse(e))
            edit.textChanged.connect(self.pathChanged.emit)

        self.setLayout(outer_layout)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

    # --------------------------------------------------
    # Accessors
    # --------------------------------------------------

    @property
    def names(self) -> list[str]:
        return [lbl.text() for lbl, _, _ in self._fields]

    @property
    def paths(self) -> list[str]:
        return [edit.text() for _, edit, _ in self._fields]

    def set_paths(self, paths: list[str]) -> None:
        for (_, edit, _), p in zip(self._fields, paths, strict=False):
            edit.setText(p)

    @property
    def name(self) -> str:
        return self.names[0]

    @property
    def path(self) -> str:
        return self.paths[0]

    @path.setter
    def path(self, p: str) -> None:
        self._fields[0][1].setText(p)

    # --------------------------------------------------
    # XML helpers
    # --------------------------------------------------

    def to_xml(
        self,
        root_tag: str | None = None,
        attr_label: str | None = None
    ) -> ET.Element:
        if len(self._fields) == 1:
            safe_tag = root_tag or self._sanitize_tag(self.name)
            el = ET.Element(safe_tag)
            el.text = self.path
            if attr_label:
                el.set(attr_label, self.name)
            return el

        root = ET.Element(root_tag or "directories")
        for lbl, edit, _ in self._fields:
            child = ET.Element(self._sanitize_tag(lbl.text()))
            child.text = edit.text()
            if attr_label:
                child.set(attr_label, lbl.text())
            root.append(child)
        return root

    def to_xml_string(self, **kwargs) -> str:
        el = self.to_xml(**kwargs)
        return ET.tostring(el, encoding="utf-8").decode("utf-8")

    def from_xml(self, element: ET.Element) -> None:
        if len(self._fields) == 1:
            lbl, edit, _ = self._fields[0]
            tag = self._sanitize_tag(lbl.text())

            if element.tag.lower() == tag.lower():
                if element.text:
                    edit.setText(element.text.strip())
                return

            child = element.find(tag)
            if child is not None and child.text:
                edit.setText(child.text.strip())
            return

        paths: list[str] = []
        for lbl, edit, _ in self._fields:
            tag = self._sanitize_tag(lbl.text())
            child = element.find(tag)
            paths.append(child.text.strip() if child is not None and child.text else "")
        self.set_paths(paths)

    @staticmethod
    def _sanitize_tag(label: str) -> str:
        s = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
        s = re.sub(r"_+", "_", s)
        if not s or s[0].isdigit():
            s = "d_" + (s or "directory")
        return s

    # --------------------------------------------------
    # Browsing
    # --------------------------------------------------

    def _browse(self, edit: QLineEdit) -> None:
        if not self._browse_enabled:
            return

        dlg = QFileDialog(self, self._dialog_title)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setFixedSize(self._dialog_width, self._dialog_height)

        if dlg.exec():
            dirs = dlg.selectedFiles()
            if dirs:
                edit.setText(dirs[0])


# --------------------------------------------------
# Demo
# --------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DirectoryPathField(
        "Working directory",
        path="/tmp",
        browse_enabled=False,
    )
    w.setWindowTitle("DirectoryPathField — Demo")
    w.show()
    sys.exit(app.exec())
