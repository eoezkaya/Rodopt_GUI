# string_options_field.py
from __future__ import annotations
from typing import Optional, Sequence, List
from PyQt6.QtWidgets import QWidget, QLabel, QComboBox, QHBoxLayout, QApplication, QSizePolicy
from PyQt6.QtCore import pyqtSignal
from xml.etree import ElementTree as ET
import sys
import re


class StringOptionsField(QWidget):
    """
    Fixed-size label + QComboBox (string options).

    Properties:
        name (str)          : label text
        value (str)         : current selected text
        options (List[str]) : available options
        label_width (int)   : fixed label width (0 = auto reset)
        field_width (int)   : fixed combo width (0 = auto reset)

    Signals:
        valueChanged(str)

    XML helpers:
        to_xml(tag=None, attr_label=None) -> ET.Element
        to_xml_string(**kwargs) -> str
        from_xml(element)                # reads element.text
    """
    valueChanged = pyqtSignal(str)

    def __init__(
        self,
        name: str,
        value: str = "",
        options: Sequence[str] = (),
        *,
        label_width: int = 120,
        field_width: int = 160,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # --- Label ---
        self._label = QLabel(name, self)
        if label_width > 0:
            self._label.setFixedWidth(label_width)
        self._label.setFixedHeight(self._label.sizeHint().height())
        self._label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # --- ComboBox ---
        self._combo = QComboBox(self)
        self._combo.setEditable(False)
        self._combo.addItems(list(options))
        if field_width > 0:
            self._combo.setFixedWidth(field_width)
        self._combo.setFixedHeight(self._combo.sizeHint().height())
        self._combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # set initial value if present in options; else append it (if non-empty)
        if value:
            idx = self._combo.findText(value)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)
            else:
                # if value not in options, insert it as first item to reflect state
                self._combo.insertItem(0, value)
                self._combo.setCurrentIndex(0)

        # --- Layout (no stretching) ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._label)
        layout.addWidget(self._combo)
        self.setLayout(layout)

        # signal
        self._combo.currentTextChanged.connect(self.valueChanged.emit)

        # lock composite size
        self.setFixedSize(self.sizeHint())

    # --- XML helpers ---
    def from_xml(self, element: ET.Element) -> None:
        """
        Restore value from an XML element produced by to_xml().
        Example:
            <Method>average</Method>
        """
        if element is not None and element.text is not None:
            self.value = element.text.strip()

    def to_xml(self, tag: str | None = None, attr_label: str | None = None) -> ET.Element:
        """
        Build an XML element for this string options field.
        element.text holds the string value.

        Args:
            tag: custom tag; if None, a safe tag is derived from the label text.
            attr_label: optional attribute name to store the human label, e.g. "label".
        """
        safe_tag = tag or self._sanitize_tag(self.name)
        el = ET.Element(safe_tag)
        el.text = self.value
        if attr_label:
            el.set(attr_label, self.name)
        return el

    def to_xml_string(self, **kwargs) -> str:
        el = self.to_xml(**kwargs)
        return ET.tostring(el, encoding="utf-8").decode("utf-8")

    # --- properties ---
    @property
    def name(self) -> str:
        return self._label.text()

    @name.setter
    def name(self, text: str) -> None:
        self._label.setText(text)

    @property
    def value(self) -> str:
        return self._combo.currentText()

    @value.setter
    def value(self, v: str) -> None:
        if v is None:
            v = ""
        idx = self._combo.findText(v)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
        else:
            # keep options intact; just prepend this value so UI reflects it
            self._combo.insertItem(0, v)
            self._combo.setCurrentIndex(0)

    @property
    def options(self) -> List[str]:
        return [self._combo.itemText(i) for i in range(self._combo.count())]

    @options.setter
    def options(self, items: Sequence[str]) -> None:
        current = self.value
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(list(items))
        # try to preserve previous selection
        idx = self._combo.findText(current)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
        elif current:  # if not in new options, prepend it so state is preserved
            self._combo.insertItem(0, current)
            self._combo.setCurrentIndex(0)
        self._combo.blockSignals(False)

    # --- width controls (match IntegerSpinBoxField API) ---
    @property
    def label_width(self) -> int:
        return self._label.width()

    @label_width.setter
    def label_width(self, w: int) -> None:
        if w > 0:
            self._label.setFixedWidth(w)
        else:
            self._label.setMaximumWidth(16777215)  # reset to auto
        self.setFixedSize(self.sizeHint())

    @property
    def field_width(self) -> int:
        return self._combo.width()

    @field_width.setter
    def field_width(self, w: int) -> None:
        if w > 0:
            self._combo.setFixedWidth(w)
        else:
            self._combo.setMaximumWidth(16777215)  # reset to auto
        self.setFixedSize(self.sizeHint())

    # --- utils ---
    @staticmethod
    def _sanitize_tag(label: str) -> str:
        s = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
        s = re.sub(r"_+", "_", s)
        if not s or s[0].isdigit():
            s = "f_" + (s or "field")
        return s


# ----------------------------------------------------------
# Run standalone for quick demo
if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = StringOptionsField(
        "Method",
        value="median",
        options=["min", "average", "max"],
        label_width=200,
        field_width=140
    )
    widget.valueChanged.connect(lambda v: print("Value changed to:", v))
    widget.show()

    def _about_to_quit():
        print("Current:", widget.value)
        print("XML:", widget.to_xml_string())
        print("XML with attr:", widget.to_xml_string(attr_label="label"))
        # round-trip test
        el = ET.fromstring(widget.to_xml_string())
        widget.from_xml(el)
        print("Reloaded:", widget.value)

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
