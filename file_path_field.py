from __future__ import annotations
from typing import Optional, Iterable, Sequence
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QApplication, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtGui import QIcon
import sys, os, re
from xml.etree import ElementTree as ET


class FilePathField(QWidget):
    """
    One or multiple file path fields.
    Each field is (Label + QLineEdit + Browse button).
    If `name` is a list, multiple fields are stacked vertically.

    Notes for theming:
    - No inline styles; all look is controlled by application-wide QSS.
    - Heights are not forced; QSS controls line height, padding, etc.
    """
    pathChanged = pyqtSignal(str)   # emits new text whenever any path changes

    def __init__(
        self,
        name: str | Sequence[str],
        path: str | Sequence[str] = "",
        *,
        label_width: int = 120,
        field_width: int = 500,
        button_size: int = 28,            # visual size only; QSS may further affect
        select_mode: str = "open_file",   # "open_file", "save_file", "open_dir"
        dialog_title: str = "Select file",
        filters: str | Iterable[str] | Sequence[str | Iterable[str]] = "All files (*)",
        dialog_width: int = 600,
        dialog_height: int = 400,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # normalize names/paths to lists
        if isinstance(name, str):
            names = [name]
        else:
            names = list(name)

        if isinstance(path, str):
            paths = [path] + [""] * (len(names) - 1)
        else:
            paths = list(path) + [""] * (len(names) - len(path))

        self._fields: list[tuple[QLabel, QLineEdit, QPushButton]] = []

        # layout (no inline styling)
        outer_layout = QVBoxLayout(self) if len(names) > 1 else QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(6)

        # normalize filters
        if isinstance(filters, (str, Iterable)) and not isinstance(filters, (list, tuple)):
            filters_list = [self._normalize_filters(filters)] * len(names)
        else:
            filters_list = [self._normalize_filters(f) for f in filters]  # type: ignore
            if len(filters_list) < len(names):
                filters_list += ["All files (*)"] * (len(names) - len(filters_list))

        self._filters_per_field = filters_list

        for idx, (nm, p) in enumerate(zip(names, paths, strict=False)):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            label = QLabel(nm, self)
            if label_width > 0:
                label.setFixedWidth(label_width)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            edit = QLineEdit(self)
            edit.setText(p)

# Let the line expand but keep a decent minimum size
            if field_width > 0:
                edit.setMinimumWidth(field_width)

            edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            
            btn = QPushButton(self)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            # Keep button square-ish; let QSS padding round it off visually
            if button_size > 0:
                btn.setFixedSize(QSize(button_size, button_size))
            icon_path = os.path.join("images", "folder_open.svg")
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(max(1, button_size - 2), max(1, button_size - 2)))
            else:
                btn.setText("...")

            # assemble row
            row.addWidget(label)
            row.addWidget(edit)
            row.addWidget(btn)

            # store
            self._fields.append((label, edit, btn))
            # vertical stack per field if multi, otherwise single row
            if len(names) > 1:
                row_wrap = QHBoxLayout()
                row_wrap.setContentsMargins(0, 0, 0, 0)
                row_wrap.setSpacing(0)
                row_wrap.addLayout(row)
                outer_layout.addLayout(row_wrap)
            else:
                outer_layout.addLayout(row)

            # signals
            btn.clicked.connect(lambda _, e=edit, f=self._filters_per_field[idx]: self._browse(e, f))
            # bubble the new text (matches DoE dirty tracking expectations)
            edit.textChanged.connect(self.pathChanged.emit)

        self.setLayout(outer_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._select_mode = select_mode
        self._dialog_title = dialog_title
        self._dialog_width = dialog_width
        self._dialog_height = dialog_height

    def from_xml(self, element: ET.Element) -> None:
        """Restore values from XML produced by to_xml()."""
        if len(self._fields) == 1:
            lbl, edit, _ = self._fields[0]
            tag = self._sanitize_tag(lbl.text())
            child = element.find(tag)
            if child is not None and child.text is not None:
                edit.setText(child.text.strip())
        else:
            paths: list[str] = []
            for lbl, edit, _ in self._fields:
                tag = self._sanitize_tag(lbl.text())
                child = element.find(tag)
                if child is not None and child.text is not None:
                    paths.append(child.text.strip())
                else:
                    paths.append("")
            self.set_paths(paths)

    # --- accessors ---
    @property
    def names(self) -> list[str]:
        return [lbl.text() for lbl, _, _ in self._fields]

    @property
    def paths(self) -> list[str]:
        return [edit.text() for _, edit, _ in self._fields]

    def set_paths(self, paths: list[str]) -> None:
        for (_, edit, _), p in zip(self._fields, paths, strict=False):
            edit.setText(p)

    # backwards-compat single-field accessors
    @property
    def name(self) -> str:
        return self.names[0]

    @property
    def path(self) -> str:
        return self.paths[0]

    @path.setter
    def path(self, p: str) -> None:
        self._fields[0][1].setText(p)

    # --- XML helpers ---
    def to_xml(self, root_tag: str | None = None, attr_label: str | None = None) -> ET.Element:
        if len(self._fields) == 1:
            safe_tag = root_tag or self._sanitize_tag(self.name)
            el = ET.Element(safe_tag)
            el.text = self.path
            if attr_label:
                el.set(attr_label, self.name)
            return el
        else:
            root = ET.Element(root_tag or "files")
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

    @staticmethod
    def _sanitize_tag(label: str) -> str:
        s = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
        s = re.sub(r"_+", "_", s)
        if not s or s[0].isdigit():
            s = "f_" + (s or "field")
        return s

    # --- browsing ---
    
    def _browse(self, edit: QLineEdit, filters: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        from pathlib import Path
    
        dlg = QFileDialog(self, self._dialog_title)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setNameFilter(filters)
        dlg.setFixedSize(self._dialog_width, self._dialog_height)
    
        if self._select_mode == "open_file":
            dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        elif self._select_mode == "save_file":
            dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        elif self._select_mode == "open_dir":
            dlg.setFileMode(QFileDialog.FileMode.Directory)
            dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        else:
            raise ValueError(f"Invalid select_mode: {self._select_mode!r}")
    
        if dlg.exec():
            files = dlg.selectedFiles()
            if not files:
                return
    
            path = Path(files[0]).expanduser().resolve()
    
            # --- Validate path ---
            if self._select_mode == "open_file":
                if not path.exists():
                    QMessageBox.critical(
                        self, "File Not Found",
                        f"The selected file does not exist:\n{path}"
                    )
                    return
                if not path.is_file():
                    QMessageBox.critical(
                        self, "Invalid Selection",
                        f"The selected path is not a file:\n{path}"
                    )
                    return
                if not os.access(path, os.R_OK):
                    QMessageBox.critical(
                        self, "Permission Denied",
                        f"You do not have permission to read this file:\n{path}"
                    )
                    return
    
            elif self._select_mode == "open_dir":
                if not path.exists():
                    QMessageBox.critical(
                        self, "Directory Not Found",
                        f"The selected directory does not exist:\n{path}"
                    )
                    return
                if not path.is_dir():
                    QMessageBox.critical(
                        self, "Invalid Selection",
                        f"The selected path is not a directory:\n{path}"
                    )
                    return
    
            # --- Passed validation ---
            edit.setText(str(path))
    

    @staticmethod
    def _normalize_filters(f: str | Iterable[str]) -> str:
        if isinstance(f, str):
            return f
        try:
            return ";;".join(f)
        except TypeError:
            return "All files (*)"


# --- demo ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = FilePathField(
        ["Any file", "Data file", "CSV only"],
        path=["", "", ""],
        filters=[
            "All files (*)",
            "Data files (*.dat *.csv)",
            "CSV files (*.csv)"
        ]
    )
    w.show()

    def _about_to_quit():
        print("XML output:\n", w.to_xml_string(attr_label="label"))

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
