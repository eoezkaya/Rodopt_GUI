from __future__ import annotations
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QApplication, QTabWidget, QFileDialog, QMessageBox, QTabBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from xml.etree import ElementTree as ET
import sys
import os
import json

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
      - observes GeneralSettings
      - keeps and propagates `problem_type`
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
        # Buttons
        # ------------------------------------------------------------
        icon_size = QSize(button_size, button_size)

        def _btn(text, icon, cb):
            b = QToolButton(text=text)
            b.setIcon(QIcon(icon))
            b.setIconSize(icon_size)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.tabs)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        # ------------------------------------------------------------
        # State
        # ------------------------------------------------------------
        self._widgets: Dict[str, QWidget] = {}
        self._label_width = label_width
        self._field_width = field_width
        self._int_field_width = int_field_width
        self._button_size = button_size
        self._dirty = False

        # ------------------------------------------------------------
        # Init
        # ------------------------------------------------------------
        self._add_core_tabs()
        self._add_objective_tab()
        self._setup_sync()
        # Ensure General Settings is active initially
        self.tabs.setCurrentIndex(0)

    # ==============================================================
    # Core tabs
    # ==============================================================
    def _add_core_tabs(self) -> None:
        # --- General Settings ---
        gs = GeneralSettings(
            label_width=self._label_width,
            text_field_width=self._field_width,
            int_field_width=self._int_field_width,
        )
        gs.changed.connect(self._mark_dirty)
        gs.problemTypeChanged.connect(self._on_problem_type_changed)

        self.problem_type = gs.problem_type

        self._add_tab(gs, "General Settings", align_top=True, closable=False)

        # --- Parameters ---
        par = Parameters(initial_rows=3)
        par.rowCountChanged.connect(self._mark_dirty)
        self._add_tab(par, "Parameters", align_top=False, closable=False)

        self._propagate_problem_type()
        self.tabs.setCurrentIndex(0)

    # ==============================================================
    def _add_tab(
        self,
        child: QWidget,
        key: str,
        *,
        align_top: bool = True,
        closable: bool = True,
    ) -> None:
        wrapper = QWidget()
        wrapper._child = child  # explicit ownership

        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(0)

        if align_top:
            lay.addWidget(child, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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
    def _add_objective_tab(self, *, from_element: ET.Element | None = None) -> None:
        idx = sum(1 for k in self._widgets if k.startswith("Objective")) + 1
        key = f"Objective {idx}"

        obj = ObjectiveFunction(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )
        if from_element is not None:
            obj.from_xml(from_element)

        obj.name_field.textChanged.connect(
            lambda name, k=key: self._rename_tab(k, name)
        )
        obj.name_field.textChanged.connect(self._mark_dirty)

        self._add_tab(obj, key, align_top=True, closable=True)
        self._propagate_problem_type()
        self.tabs.setCurrentWidget(self._widgets[key])

    def _add_constraint_tab(self, *, from_element: ET.Element | None = None) -> None:
        idx = sum(1 for k in self._widgets if k.startswith("Constraint")) + 1
        key = f"Constraint {idx}"

        con = ConstraintFunction(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )
        if from_element is not None:
            con.from_xml(from_element)

        con.name_field.textChanged.connect(
            lambda name, k=key: self._rename_tab(k, name)
        )
        con.name_field.textChanged.connect(self._mark_dirty)

        self._add_tab(con, key, align_top=True, closable=True)
        self._propagate_problem_type()
        self.tabs.setCurrentWidget(self._widgets[key])

    # ==============================================================
    # Problem type propagation
    # ==============================================================
    def _on_problem_type_changed(self, value: str):
        self.problem_type = value
        self._propagate_problem_type()

    def _propagate_problem_type(self):
        for wrapper in self._widgets.values():
            child = getattr(wrapper, "_child", None)
            if child and hasattr(child, "set_problem_type"):
                child.set_problem_type(self.problem_type)

    # ==============================================================
    # Tab helpers
    # ==============================================================
    def _rename_tab(self, key: str, title: str) -> None:
        wrapper = self._widgets.get(key)
        if not wrapper:
            return
        idx = self.tabs.indexOf(wrapper)
        if idx != -1:
            self.tabs.setTabText(idx, title.strip() or key)
        self._mark_dirty()

    def _close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        for key, w in list(self._widgets.items()):
            if w is widget:
                if key in self.CORE_TABS:
                    return
                self._widgets.pop(key)
                self.tabs.removeTab(index)
                widget.deleteLater()
                self._mark_dirty()
                return

    # ==============================================================
    # New / Save / Load
    # ==============================================================
    def _new_study(self) -> None:
        if QMessageBox.question(
            self, "New Study", "Discard current study?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        self.tabs.clear()
        self._widgets.clear()
        self._dirty = False

        self._add_core_tabs()
        self._add_objective_tab()
        self._setup_sync()

    def _save_to_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save XML", "", "XML Files (*.xml)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_xml_string())
        self._dirty = False

    def _load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load XML", "", "XML Files (*.xml)")
        if not path:
            return

        tree = ET.parse(path)
        root = tree.getroot()

        self.tabs.clear()
        self._widgets.clear()

        self._add_core_tabs()

        gs = self._widgets["General Settings"]._child
        gs.from_xml(root.find("general_settings"))
        self.problem_type = gs.problem_type

        par = self._widgets["Parameters"]._child
        par.from_xml(root.find("problem_parameters"))

        for el in root.findall("objective_function"):
            self._add_objective_tab(from_element=el)

        for el in root.findall("constraint_function"):
            self._add_constraint_tab(from_element=el)

        self._propagate_problem_type()
        self._dirty = False

    # ==============================================================
    # RUN
    # ==============================================================
    def _run_doe(self) -> None:
        config_path = os.path.join(os.path.expanduser("~"), ".rodop_run_config.json")
        last_loaded_xml = None

        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                last_loaded_xml = json.load(f).get("last_loaded_xml")

        gs = self._widgets["General Settings"]._child
        data = gs.snapshot()

        problem_name = data["problem_name"]
        working_dir = data["working_directory"]

        if not os.path.isdir(working_dir):
            QMessageBox.critical(self, "Error", "Invalid working directory.")
            return

        if last_loaded_xml and os.path.isfile(last_loaded_xml):
            xml_path = last_loaded_xml
        else:
            xml_path = os.path.join(working_dir, f"{problem_name}.xml")

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(self.to_xml_string())

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"last_loaded_xml": os.path.abspath(xml_path)}, f, indent=2)

        if "Run" in self._widgets:
            self.tabs.setCurrentWidget(self._widgets["Run"])
            return

        run = RunDoE(
            label_width=self._label_width,
            field_width=self._field_width,
            button_size=self._button_size,
        )
        run.xml_field.path = xml_path

        self._add_tab(run, "Run", align_top=True, closable=True)
        self._propagate_problem_type()
        self.tabs.setCurrentWidget(self._widgets["Run"])

    # ==============================================================
    # Exit / Sync / XML
    # ==============================================================
    def _exit_app(self) -> None:
        if self._dirty:
            r = QMessageBox.warning(
                self, "Unsaved Changes", "Save before exit?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                self._save_to_file()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        QApplication.instance().quit()

    def _mark_dirty(self, *args):
        self._dirty = True

    def _setup_sync(self) -> None:
        gs = self._widgets["General Settings"]._child
        par = self._widgets["Parameters"]._child

        gs.num_params_field.valueChanged.connect(
            lambda n: par.set_rows(par.snapshot()[:n])
            if par.row_count() > n else None
        )
        par.rowCountChanged.connect(lambda n: setattr(gs.num_params_field, "value", n))

    def to_xml(self, *, root_tag: str = "optimization_study") -> ET.Element:
        root = ET.Element(root_tag)
        for w in self._widgets.values():
            child = getattr(w, "_child", None)
            if child and hasattr(child, "to_xml"):
                root.append(child.to_xml())
        return root

    def to_xml_string(self) -> str:
        return ET.tostring(self.to_xml(), encoding="utf-8").decode("utf-8")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    from themes import apply_theme

    app = QApplication(sys.argv)
    apply_theme(app, "neutral")

    w = Study()
    w.setWindowTitle("Study — Demo")
    w.resize(1100, 750)
    w.show()

    sys.exit(app.exec())
