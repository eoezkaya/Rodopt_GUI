from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QApplication, QTabWidget, QFileDialog, QMessageBox,
    QTabBar, QLabel, QScrollArea  # <-- NEW
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from xml.etree import ElementTree as ET
import sys
import os

from general_settings_widget import GeneralSettings
from objective_function_widget import ObjectiveFunction
from parameters_widget import Parameters
from constraint_function_widget import ConstraintFunction
from run_doe import RunDoE


class Study(QWidget):
    """
    Study composite widget.

    Responsibilities:
      - owns tabs and lifecycle
      - owns XML lifecycle
      - owns objective identity (Objective1, Objective2, ...)
      - passes XML path directly to RunDoE
      - displays current XML filename + dirty state
    """

    CORE_TABS = ("General Settings", "Parameters")

    def __init__(
        self,
        *,
        label_width: int = 180,
        field_width: int = 360,
        int_field_width: int = 100,
        button_size: int = 40,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ==============================================================
        # Make Study scrollable (NEW)
        # ==============================================================
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        scroll.setWidget(content)

        outer.addWidget(scroll)

        # IMPORTANT: use 'content' as the widget that holds the existing Study layout
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)

        # ------------------------------------------------------------
        # Shared state
        # ------------------------------------------------------------
        self.problem_type: str | None = None

        # ------------------------------------------------------------
        # Tabs
        # ------------------------------------------------------------
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)

        # ------------------------------------------------------------
        # XML label (top-right)
        # ------------------------------------------------------------
        self._xml_label = QLabel("MyStudy.xml", self)
        self._xml_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._xml_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding-right: 6px;
            }
        """)
        self._xml_label.setToolTip("Unsaved study")

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------
        icon_size = QSize(button_size, button_size)

        def _btn(text, icon, cb):
            b = QToolButton(text=text)
            b.setIcon(QIcon(icon))
            b.setIconSize(icon_size)
            b.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon
            )
            b.clicked.connect(cb)
            return b

        buttons = [
            _btn("Save XML", "images/save_as.svg", self._save_to_file),
            _btn("Load XML", "images/file_load.svg", self._load_from_file),
            _btn("New Study", "images/new_window.svg", self._new_study),
            _btn("Add Objective", "images/objective.svg", self._add_objective_tab),
            _btn("Add Constraint", "images/constraint.svg", self._add_constraint_tab),
            _btn("Run", "images/run.svg", self._run_doe),
            _btn("Exit", "images/exit.svg", self._exit_app),
        ]

        max_w = max(b.sizeHint().width() for b in buttons)
        max_h = max(b.sizeHint().height() for b in buttons)
        for b in buttons:
            b.setFixedSize(max_w, max_h)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        for b in buttons:
            btn_row.addWidget(b)
        btn_row.addStretch(1)

        # ------------------------------------------------------------
        # Main layout
        # ------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        top_row.addWidget(self._xml_label)

        layout.addLayout(top_row)
        layout.addWidget(self.tabs)
        layout.addLayout(btn_row)
        self.setLayout(outer)

        # ------------------------------------------------------------
        # State
        # ------------------------------------------------------------
        self._widgets: Dict[str, QWidget] = {}
        self._label_width = label_width
        self._field_width = field_width
        self._int_field_width = int_field_width
        self._button_size = button_size
        self._dirty = False
        self._study_path: str | None = None
        self._study_filename: str = "MyStudy.xml"

        # ------------------------------------------------------------
        # Init
        # ------------------------------------------------------------
        self._add_core_tabs()
        self._add_objective_tab()
        self._setup_sync()
        self.tabs.setCurrentIndex(0)
        self._update_xml_label()

    # ==============================================================
    # Core tabs
    # ==============================================================
    def _add_core_tabs(self) -> None:
        gs = GeneralSettings(
            label_width=self._label_width,
            text_field_width=self._field_width,
            int_field_width=self._int_field_width,
        )
        gs.changed.connect(self._mark_dirty)
        gs.problemTypeChanged.connect(self._on_problem_type_changed)

        self.problem_type = gs.problem_type
        self._add_tab(gs, "General Settings", align_top=True, closable=False)

        par = Parameters(initial_rows=3)
        par.rowCountChanged.connect(self._mark_dirty)
        par.changed.connect(self._mark_dirty)   # <--- NEW: mark study dirty on any param change
        self._add_tab(par, "Parameters", align_top=False, closable=False)

        self._propagate_problem_type()

    def _add_tab(
        self,
        child: QWidget,
        key: str,
        *,
        align_top: bool = True,
        closable: bool = True,
    ) -> None:
        wrapper = QWidget()
        wrapper._child = child

        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(0)

        if align_top:
            lay.addWidget(
                child,
                alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            )
            lay.addStretch(1)
        else:
            lay.addWidget(child)

        self._widgets[key] = wrapper
        self.tabs.addTab(wrapper, key)

        if not closable:
            idx = self.tabs.indexOf(wrapper)
            tb = self.tabs.tabBar()
            tb.setTabButton(idx, QTabBar.ButtonPosition.RightSide, None)
            tb.setTabButton(idx, QTabBar.ButtonPosition.LeftSide, None)

    # ==============================================================
    # Objective / Constraint
    # ==============================================================
    def _next_objective_name(self) -> str:
        i = 1
        while f"Objective{i}" in self._widgets:
            i += 1
        return f"Objective{i}"

    def _next_constraint_name(self) -> str:
        i = 1
        while f"Constraint{i}" in self._widgets:
            i += 1
        return f"Constraint{i}"

    def _add_objective_tab(self, *, from_element: ET.Element | None = None) -> None:
        name = self._next_objective_name()

        obj = ObjectiveFunction(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )

        # Objective identity is owned by Study
        obj.name_field.text = name
        obj.name_field.setEnabled(True)

        if from_element is not None:
            obj.from_xml(from_element)
            obj.name_field.text = name  # enforce consistency

        self._add_tab(obj, name, align_top=True, closable=True)

        wrapper = self._widgets[name]

        # keep tab label in sync with name field
        obj.name_field.textChanged.connect(
            lambda text, w=wrapper: self._sync_tab_title(w, text)
        )

        obj.changed.connect(self._mark_dirty)

        self._propagate_problem_type()
        self.tabs.setCurrentWidget(wrapper)

    def _sync_tab_title(self, wrapper: QWidget, title: str) -> None:
        idx = self.tabs.indexOf(wrapper)
        if idx != -1:
            self.tabs.setTabText(idx, title.strip() or "Objective")

    def _add_constraint_tab(self, *, from_element: ET.Element | None = None) -> None:
        name = self._next_constraint_name()
        key = name  # key matches the visible/default name

        con = ConstraintFunction(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )

        # Constraint identity is owned by Study
        con.name = name
        con.name_field.setEnabled(True)

        if from_element is not None:
            con.from_xml(from_element)
            # enforce consistency: label matches our Study-owned name
            con.name = name

        self._add_tab(con, key, align_top=True, closable=True)

        wrapper = self._widgets[key]

        # keep tab label in sync with constraint name field
        con.name_field.textChanged.connect(
            lambda text, w=wrapper: self._sync_constraint_tab_title(w, text)
        )

        con.changed.connect(self._mark_dirty)

        self._propagate_problem_type()
        self.tabs.setCurrentWidget(wrapper)

    def _sync_constraint_tab_title(self, wrapper: QWidget, title: str) -> None:
        idx = self.tabs.indexOf(wrapper)
        if idx != -1:
            self.tabs.setTabText(idx, title.strip() or "Constraint")

    # ==============================================================
    # RUN
    # ==============================================================
    def _run_doe(self) -> None:
        gs = self._widgets["General Settings"]._child
        data = gs.snapshot()

        working_dir = data["working_directory"]

        if not os.path.isdir(working_dir):
            QMessageBox.critical(self, "Error", "Invalid working directory.")
            return

        if not self._study_path:
            QMessageBox.warning(
                self,
                "Save required",
                "Please save the study before running."
            )
            self._save_to_file()
            if not self._study_path:
                return

        with open(self._study_path, "w", encoding="utf-8") as f:
            f.write(self.to_xml_string())

        self._dirty = False
        self._update_xml_label()

        if "Run" in self._widgets:
            run = self._widgets["Run"]._child
            run.set_xml_path(self._study_path)
            self.tabs.setCurrentWidget(self._widgets["Run"])
            return

        run = RunDoE(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )
        run.set_xml_path(self._study_path)

        self._add_tab(run, "Run", align_top=True, closable=True)
        self._propagate_problem_type()
        self.tabs.setCurrentWidget(self._widgets["Run"])

    # ==============================================================
    # New / Save / Load / Exit
    # ==============================================================
    def _new_study(self) -> None:
        if self._dirty:
            r = QMessageBox.question(
                self,
                "New Study",
                "Discard current study?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return

        self.tabs.clear()
        self._widgets.clear()
        self._dirty = False
        self._study_path = None

        self._add_core_tabs()
        self._add_objective_tab()
        self._setup_sync()
        self.tabs.setCurrentIndex(0)
        self._update_xml_label()

    def _save_to_file(self) -> None:
        default_path = self._study_path or self._study_filename
        path, _ = QFileDialog.getSaveFileName(
            self, "Save XML", default_path, "XML Files (*.xml)"
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_xml_string())

        self._study_path = path
        self._dirty = False
        self._update_xml_label()

    def _load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load XML", "", "XML Files (*.xml)"
        )
        if not path:
            return

        tree = ET.parse(path)
        root = tree.getroot()

        self.tabs.clear()
        self._widgets.clear()

        self._add_core_tabs()
        self._widgets["General Settings"]._child.from_xml(
            root.find("general_settings")
        )
        self._widgets["Parameters"]._child.from_xml(
            root.find("problem_parameters")
        )

        for el in root.findall("objective_function"):
            self._add_objective_tab(from_element=el)

        for el in root.findall("constraint_function"):
            self._add_constraint_tab(from_element=el)

        self._study_path = path
        self._dirty = False
        self._update_xml_label()

        # after all tabs are (re)created and populated
        if "General Settings" in self._widgets:
            general_wrapper = self._widgets["General Settings"]
            self.tabs.setCurrentWidget(general_wrapper)

    def _exit_app(self) -> None:
        if self._dirty:
            r = QMessageBox.warning(
                self,
                "Unsaved Changes",
                "Save before exit?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                self._save_to_file()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        QApplication.instance().quit()

    # ==============================================================
    # Helpers
    # ==============================================================
    def _update_xml_label(self):
        if self._study_path:
            name = os.path.basename(self._study_path)
            self._xml_label.setToolTip(self._study_path)
        else:
            name = "MyStudy.xml"
            self._xml_label.setToolTip("Unsaved study")

        self._xml_label.setText(f"{name}*" if self._dirty else name)

    def _close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        for key, w in list(self._widgets.items()):
            if w is widget and key not in self.CORE_TABS:
                self._widgets.pop(key)
                self.tabs.removeTab(index)
                widget.deleteLater()
                self._mark_dirty()
                return

    def _on_problem_type_changed(self, value: str):
        self.problem_type = value
        self._propagate_problem_type()

    def _propagate_problem_type(self):
        for wrapper in self._widgets.values():
            child = getattr(wrapper, "_child", None)
            if child and hasattr(child, "set_problem_type"):
                child.set_problem_type(self.problem_type)

    def _mark_dirty(self, *args):
        if not self._dirty:
            self._dirty = True
            self._update_xml_label()

    def _setup_sync(self):
        gs = self._widgets["General Settings"]._child
        par = self._widgets["Parameters"]._child

        gs.num_params_field.valueChanged.connect(
            lambda n: par.set_rows(par.snapshot()[:n])
            if par.row_count() > n else None
        )
        par.rowCountChanged.connect(
            lambda n: setattr(gs.num_params_field, "value", n)
        )

    def to_xml(self, *, root_tag: str = "optimization_study") -> ET.Element:
        root = ET.Element(root_tag)
        for w in self._widgets.values():
            child = getattr(w, "_child", None)
            if child and hasattr(child, "to_xml"):
                root.append(child.to_xml())
        return root

    def to_xml_string(self) -> str:
        return ET.tostring(
            self.to_xml(),
            encoding="utf-8"
        ).decode("utf-8")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    from themes import apply_theme

    app = QApplication(sys.argv)
    apply_theme(app, "neutral")

    w = Study()
    w.setWindowTitle("Study")
    w.resize(1100, 750)
    w.show()

    sys.exit(app.exec())
