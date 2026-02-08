# parameters_widget.py
from __future__ import annotations
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QLineEdit, QComboBox,
    QPushButton, QHeaderView, QApplication, QMessageBox, QGroupBox,
    QDoubleSpinBox, QSizePolicy
)
from PyQt6.QtGui import QValidator
from xml.etree import ElementTree as ET
import sys
import re


# ---------- Flexible double spinbox ----------
class FlexibleDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent: Optional[QWidget] = None, min_decimals: int = 4):
        super().__init__(parent)
        self._display_decimals = max(0, int(min_decimals))
        self.setDecimals(16)
        self.setSingleStep(0.1)
        self.valueChanged.connect(self._on_value_changed)
        self.editingFinished.connect(self._capture_user_precision)

    def validate(self, text: str, pos: int):
        t = text.strip()
        if t in {"", "-", "+", ".", ",", "-.", "-,", "+.", ",+"}:
            return (QValidator.State.Intermediate, text, pos)
        t_norm = t.replace(",", ".")
        try:
            float(t_norm)
        except ValueError:
            return (QValidator.State.Invalid, text, pos)
        return (QValidator.State.Acceptable, text, pos)

    def valueFromText(self, text: str) -> float:
        t_norm = text.replace(",", ".")
        try:
            return float(t_norm)
        except ValueError:
            return 0.0

    def textFromValue(self, value: float) -> str:
        return f"{value:.{self._display_decimals}f}"

    def _capture_user_precision(self) -> None:
        txt = self.lineEdit().text()
        if not txt:
            return
        if "," in txt:
            frac = txt.split(",", 1)[1]
        elif "." in txt:
            frac = txt.split(".", 1)[1]
        else:
            frac = ""
        if frac and len(frac) > self._display_decimals:
            self._display_decimals = min(16, len(frac))
        self.lineEdit().setText(self.text())

    def _on_value_changed(self, _v: float) -> None:
        if self.hasFocus():
            return
        self.lineEdit().setText(self.text())


class Parameters(QWidget):
    """
    Excel-like parameters editor with 5 columns:
      name | type | increment | lower bound | upper bound
    """
    changed = pyqtSignal()
    rowCountChanged = pyqtSignal(int)
    paramInfoChanged = pyqtSignal(int, list)  # (num_params, names)

    COL_NAME = 0
    COL_TYPE = 1
    COL_INCR = 2
    COL_LOWER = 3
    COL_UPPER = 4

    def __init__(self, *, initial_rows: int = 2, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # --- NEW: parameter-name invalid style ---
        self._invalid_param_name_style = """
        QLineEdit {
            border: 2px solid red;
            border-radius: 3px;
        }
        """

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["name", "type", "increment", "lower bound", "upper bound"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)

        # NEW: make selection row-based so "Remove selected" removes the intended row(s)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_INCR, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_LOWER, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(self.COL_UPPER, QHeaderView.ResizeMode.Interactive)

        self.add_btn = QPushButton("Add parameter", self)
        self.del_btn = QPushButton("Remove selected", self)
        self.check_btn = QPushButton("Check", self)

        self.add_btn.clicked.connect(self._add_row_and_emit)
        self.del_btn.clicked.connect(self._remove_selected_rows_and_emit)
        self.check_btn.clicked.connect(self._check_constraints)

        btns = QHBoxLayout()
        btns.setContentsMargins(0, 6, 0, 0)
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)
        btns.addStretch(1)
        btns.addWidget(self.check_btn)

        group = QGroupBox("Parameters", self)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(6)
        inner_layout.addWidget(self.table, 1)
        inner_layout.addLayout(btns)
        group.setLayout(inner_layout)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(group, 1)
        self.setLayout(root)

        for i in range(1, max(1, int(initial_rows)) + 1):
            self._add_row(default_index=i, emit=False)
        self._fix_default_names()
        self.rowCountChanged.emit(self.table.rowCount())

        

    # ---------- Internals ----------
    def _wire_editors(self, r: int) -> None:
        name_w = self.table.cellWidget(r, self.COL_NAME)
        type_w = self.table.cellWidget(r, self.COL_TYPE)
        incr_w = self.table.cellWidget(r, self.COL_INCR)
        low_w = self.table.cellWidget(r, self.COL_LOWER)
        up_w  = self.table.cellWidget(r, self.COL_UPPER)

        if isinstance(name_w, QLineEdit):
            name_w.textChanged.connect(lambda _=None: self.changed.emit())
        if isinstance(type_w, QComboBox):
            type_w.currentIndexChanged.connect(lambda _=None: self.changed.emit())
        for w in (incr_w, low_w, up_w):
            if isinstance(w, FlexibleDoubleSpinBox):
                w.valueChanged.connect(lambda _=None: self.changed.emit())

    def _default_param_name(self, idx1: int) -> str:
        return f"x{idx1}"

    def _add_row(self, default_index: Optional[int] = None, emit: bool = True) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        type_default = "continuous"
        name_text = self._default_param_name(r + 1) if default_index is None else self._default_param_name(default_index)

        name_w = QLineEdit(self)
        name_w.setText(name_text)
        # NEW: validate as user types
        name_w.textChanged.connect(self._on_param_name_changed)
        self.table.setCellWidget(r, self.COL_NAME, name_w)

        type_w = QComboBox(self)
        type_w.addItems(["continuous", "discrete"])
        type_w.setCurrentText(type_default)
        type_w.currentTextChanged.connect(lambda _t, cb=type_w: self._sync_row_widgets_for_type(cb))
        self.table.setCellWidget(r, self.COL_TYPE, type_w)

        incr_w = FlexibleDoubleSpinBox(self, min_decimals=4)
        incr_w.setRange(1e-12, 1e100)
        incr_w.setValue(1.0)
        incr_w.setEnabled(False)
        # theme-aware: mark inactive for continuous by default
        incr_w.setProperty("inactive", True)
        incr_w.style().unpolish(incr_w)
        incr_w.style().polish(incr_w)
        self.table.setCellWidget(r, self.COL_INCR, incr_w)

        low_w = FlexibleDoubleSpinBox(self, min_decimals=4)
        up_w  = FlexibleDoubleSpinBox(self, min_decimals=4)
        low_w.setRange(-1e100, 1e100)
        up_w.setRange(-1e100, 1e100)
        low_w.setValue(0.0)
        up_w.setValue(1.0)
        self.table.setCellWidget(r, self.COL_LOWER, low_w)
        self.table.setCellWidget(r, self.COL_UPPER, up_w)

        self._wire_editors(r)

        if emit:
            self.rowCountChanged.emit(self.table.rowCount())
            self.changed.emit()
            self._emit_param_info()  # NEW

    def _add_row_and_emit(self) -> None:
        self._add_row()

    def _remove_selected_rows_and_emit(self) -> None:
        sm = self.table.selectionModel()
        rows: list[int] = []

        if sm is not None:
            rows = [idx.row() for idx in sm.selectedRows()]

        # Fallback: remove the row of the current cell
        if not rows and sm is not None:
            cur = sm.currentIndex()
            if cur.isValid():
                rows = [cur.row()]

        if not rows:
            return

        for r in sorted(set(rows), reverse=True):
            if 0 <= r < self.table.rowCount():
                self.table.removeRow(r)

        self._fix_default_names()
        self.rowCountChanged.emit(self.table.rowCount())
        self.changed.emit()
        self._emit_param_info()  # NEW

    def _fix_default_names(self) -> None:
        default_pat = re.compile(r"^x\d+$", re.IGNORECASE)
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, self.COL_NAME)
            if isinstance(name_w, QLineEdit):
                txt = name_w.text().strip()
                if not txt or default_pat.match(txt):
                    name_w.setText(self._default_param_name(r + 1))

    def _sync_row_widgets_for_type(self, type_cb: QComboBox) -> None:
        r = self._find_row(type_cb)
        if r < 0:
            return
        typ = type_cb.currentText().lower()
        incr_w = self.table.cellWidget(r, self.COL_INCR)
        if isinstance(incr_w, FlexibleDoubleSpinBox):
            is_discrete = (typ == "discrete")
            incr_w.setEnabled(is_discrete)
            incr_w.setProperty("inactive", not is_discrete)
            incr_w.style().unpolish(incr_w)
            incr_w.style().polish(incr_w)

    def _find_row(self, child: QWidget) -> int:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                if self.table.cellWidget(r, c) is child:
                    return r
        return -1

    # ==================================================
    # NEW: parameter-name validation
    # ==================================================
    def _on_param_name_changed(self, text: str) -> None:
        """
        Parameter name is invalid if:
          - empty
          - contains ANY whitespace (leading, trailing, or inside)
          - contains characters other than letters, digits, underscore
        """
        name = text  # do NOT strip, so "x1 " stays invalid

        if not name or any(ch.isspace() for ch in name):
            is_valid = False
        else:
            is_valid = bool(re.fullmatch(r"[A-Za-z0-9_]+", name))

        editor = self.sender()
        if isinstance(editor, QLineEdit):
            if is_valid:
                editor.setStyleSheet("")
                editor.setToolTip("")
            else:
                editor.setStyleSheet(self._invalid_param_name_style)
                editor.setToolTip(
                    "Invalid name. Use only letters, digits, and underscore; "
                    "no spaces or special characters."
                )

        # keep existing behavior that editing marks widget dirty
        self.changed.emit()
        self._emit_param_info()  # NEW

    def _emit_param_info(self) -> None:
        snap = self.snapshot()
        names = [str(r.get("name", "")).strip() for r in snap if str(r.get("name", "")).strip()]
        self.paramInfoChanged.emit(len(snap), names)

    def ensure_row_count(self, n: int) -> None:
        """Ensure the table has exactly n rows (adds/removes rows as needed)."""
        n = max(0, int(n))
        cur = self.table.rowCount()

        if n == cur:
            return

        if n < cur:
            # remove from bottom
            for r in range(cur - 1, n - 1, -1):
                self.table.removeRow(r)
            self._fix_default_names()
            self.rowCountChanged.emit(self.table.rowCount())
            self.changed.emit()
            self._emit_param_info()
            return

        # n > cur: add rows
        for _ in range(cur, n):
            self._add_row(default_index=None, emit=False)
        self._fix_default_names()
        self.rowCountChanged.emit(self.table.rowCount())
        self.changed.emit()
        self._emit_param_info()

    # ---------- Public API ----------
    def row_count(self) -> int:
        return self.table.rowCount()

    def add_row(self) -> None:
        self._add_row()

    def remove_selected(self) -> None:
        self._remove_selected_rows_and_emit()

    def set_rows(self, params: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for i, p in enumerate(params, start=1):
            self._add_row(default_index=i, emit=False)
            r = i - 1
            name_w = self.table.cellWidget(r, self.COL_NAME)
            if isinstance(name_w, QLineEdit):
                name_w.setText(str(p.get("name", self._default_param_name(i))))
            type_w = self.table.cellWidget(r, self.COL_TYPE)
            if isinstance(type_w, QComboBox):
                typ = str(p.get("type", "continuous")).lower()
                j = type_w.findText(typ)
                type_w.setCurrentIndex(j if j >= 0 else 0)
                self._sync_row_widgets_for_type(type_w)
            incr_w = self.table.cellWidget(r, self.COL_INCR)
            if isinstance(incr_w, FlexibleDoubleSpinBox):
                if str(p.get("type", "continuous")).lower() == "discrete":
                    incr_val = float(p.get("increment", 1.0))
                    incr_w.setValue(incr_val)
                else:
                    incr_w.setEnabled(False)
                    incr_w.setProperty("inactive", True)
                    incr_w.style().unpolish(incr_w)
                    incr_w.style().polish(incr_w)
            low_w = self.table.cellWidget(r, self.COL_LOWER)
            up_w = self.table.cellWidget(r, self.COL_UPPER)
            if isinstance(low_w, FlexibleDoubleSpinBox):
                low_w.setValue(float(p.get("lower", 0.0)))
            if isinstance(up_w, FlexibleDoubleSpinBox):
                up_w.setValue(float(p.get("upper", 1.0)))

        self._fix_default_names()
        self.rowCountChanged.emit(self.table.rowCount())
        self.changed.emit()
        self._emit_param_info()  # NEW

    # ---------- Validation ----------
    def _check_constraints(self) -> None:
        issues: List[str] = []
        names_seen: dict[str, int] = {}
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, self.COL_NAME)
            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            if not name:
                continue
            if name in names_seen:
                first = names_seen[name] + 1
                issues.append(f"Duplicate name '{name}' at rows {first} and {r+1}.")
            else:
                names_seen[name] = r
        for r in range(self.table.rowCount()):
            low_w = self.table.cellWidget(r, self.COL_LOWER)
            up_w  = self.table.cellWidget(r, self.COL_UPPER)
            if not (isinstance(low_w, FlexibleDoubleSpinBox) and isinstance(up_w, FlexibleDoubleSpinBox)):
                continue
            lower = float(low_w.value())
            upper = float(up_w.value())
            if lower > upper:
                issues.append(f"Row {r+1}: lower bound ({lower}) is greater than upper bound ({upper}).")

        if issues:
            QMessageBox.warning(
                self,
                "Check failed",
                "Please fix the following issues:\n\n- " + "\n- ".join(issues),
                QMessageBox.StandardButton.Ok,
            )
        else:
            QMessageBox.information(
                self,
                "Check passed",
                "OK — Names are unique and all rows satisfy lower ≤ upper.",
                QMessageBox.StandardButton.Ok,
            )

    # ---------- XML ----------
    def to_xml(self) -> ET.Element:
        root = ET.Element("problem_parameters")
        for row in self.snapshot():
            param_el = ET.SubElement(root, "parameter")
            ET.SubElement(param_el, "name").text = str(row.get("name", ""))
            typ = str(row.get("type", "continuous")).lower()
            ET.SubElement(param_el, "type").text = "REAL" if typ == "continuous" else "INTEGER"
            lower = row.get("lower")
            if lower is not None:
                ET.SubElement(param_el, "lower_bound").text = f"{float(lower):.4f}"
            upper = row.get("upper")
            if upper is not None:
                ET.SubElement(param_el, "upper_bound").text = f"{float(upper):.4f}"
            if typ == "discrete" and row.get("increment") is not None:
                ET.SubElement(param_el, "increment").text = f"{float(row['increment']):.4f}"
        return root

    def to_xml_string(self) -> str:
        import xml.dom.minidom as minidom
        el = self.to_xml()
        xml_bytes = ET.tostring(el, encoding="utf-8")
        parsed = minidom.parseString(xml_bytes)
        pretty = parsed.toprettyxml(indent="  ")
        pretty_no_decl = "\n".join(line for line in pretty.splitlines() if not line.strip().startswith("<?xml"))
        return pretty_no_decl.strip() + "\n"

    def from_xml(self, element: ET.Element) -> None:
        params: List[Dict[str, Any]] = []
        for param_el in element.findall("parameter"):
            p: Dict[str, Any] = {}
            for child in param_el:
                tag = child.tag.lower().strip()
                val = (child.text or "").strip()
                if tag == "name":
                    p["name"] = val
                elif tag == "type":
                    if val.upper() == "REAL":
                        p["type"] = "continuous"
                    elif val.upper() == "INTEGER":
                        p["type"] = "discrete"
                    else:
                        p["type"] = "continuous"
                elif tag == "increment":
                    try:
                        p["increment"] = float(val)
                    except ValueError:
                        p["increment"] = 1.0
                elif tag == "lower_bound":
                    try:
                        p["lower"] = float(val)
                    except ValueError:
                        p["lower"] = 0.0
                elif tag == "upper_bound":
                    try:
                        p["upper"] = float(val)
                    except ValueError:
                        p["upper"] = 1.0
            params.append(p)
        self.set_rows(params)
    def snapshot(self) -> List[Dict[str, Any]]:
        """
        Return a list of dicts representing all parameter rows.
        Skips completely empty rows.
        """
        rows = self.table.rowCount()
        out: List[Dict[str, Any]] = []
        for r in range(rows):
            name_w = self.table.cellWidget(r, self.COL_NAME)
            type_w = self.table.cellWidget(r, self.COL_TYPE)
            incr_w = self.table.cellWidget(r, self.COL_INCR)
            low_w = self.table.cellWidget(r, self.COL_LOWER)
            up_w = self.table.cellWidget(r, self.COL_UPPER)

            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            typ = type_w.currentText().lower() if isinstance(type_w, QComboBox) else "continuous"
            incr = float(incr_w.value()) if (isinstance(incr_w, FlexibleDoubleSpinBox) and incr_w.isEnabled()) else None
            lower = float(low_w.value()) if isinstance(low_w, FlexibleDoubleSpinBox) else None
            upper = float(up_w.value()) if isinstance(up_w, FlexibleDoubleSpinBox) else None

            if not (name or lower is not None or upper is not None):
                continue

            out.append({
                "name": name,
                "type": typ,
                "increment": incr,
                "lower": lower,
                "upper": upper,
            })
        return out


# ---------------- Demo ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    from themes import apply_theme
    apply_theme(app, "light")  # or "neutral", "dark"

    w = Parameters(initial_rows=3)
    w.setWindowTitle("Parameters — Demo")
    w.resize(900, 420)
    w.show()

    def _about_to_quit():
        print("Snapshot:", w.snapshot())
        print("XML:")
        print(w.to_xml_string())

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
