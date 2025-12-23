# themes.py
from PyQt6.QtWidgets import QApplication

def _qss_light():
    return """ 
    QWidget { background: #f5f5f5; color: #202124; font-size: 13px; }

    QGroupBox {
        background: #ffffff;
        border: 2px solid #d0d0d0;
        border-radius: 8px;
        margin-top: 1.4em;
        padding: 14px 16px 12px 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: #1a73e8;
        font-weight: 600;
    }

    QTabWidget::pane { border: 1px solid #d0d0d0; background: #ffffff; }
    QTabBar::tab { background: #e9ecef; border: 1px solid #d0d0d0; padding: 6px 12px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
    QTabBar::tab:selected { background: #ffffff; border-bottom-color: #ffffff; }

    QPushButton, QToolButton {
        background: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover, QToolButton:hover { border-color: #b7b7b7; }
    QPushButton:pressed, QToolButton:pressed { background: #e6eefc; border-color: #1a73e8; }

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background: #ffffff;
        border: 1px solid #cfcfcf;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #1a73e8; }

    QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #cfcfcf; selection-background-color: #e6eefc; }

    QTableWidget { background: #ffffff; gridline-color: #e0e0e0; selection-background-color: #e6eefc; }
    QHeaderView::section { background: #f1f3f4; padding: 6px; border: 1px solid #d0d0d0; }

    QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
    QScrollBar::handle:vertical { background: #cfd8dc; border-radius: 6px; min-height: 24px; }

    QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
    QScrollBar::handle:horizontal { background: #cfd8dc; border-radius: 6px; min-width: 24px; }

    QDoubleSpinBox[inactive="true"] {
        background: #e0e0e0;
        color: #555;
    }
    """


def _qss_neutral():
    return """ 
    QWidget { background: #eaeff1; color: #1f2933; font-size: 13px; }

    QGroupBox {
        background: #ffffff;
        border: 2px solid #c2c9cc;
        border-radius: 8px;
        margin-top: 1.4em;
        padding: 14px 16px 12px 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: #00695c;
        font-weight: 600;
    }

    QTabWidget::pane { border: 1px solid #c2c9cc; background: #ffffff; }
    QTabBar::tab { background: #dde3e6; border: 1px solid #c2c9cc; padding: 6px 12px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
    QTabBar::tab:selected { background: #ffffff; border-bottom-color: #ffffff; }

    QPushButton, QToolButton {
        background: #ffffff;
        border: 1px solid #c2c9cc;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover, QToolButton:hover { border-color: #9fb1b7; }
    QPushButton:pressed, QToolButton:pressed { background: #d8f1ee; border-color: #00695c; }

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background: #ffffff;
        border: 1px solid #c2c9cc;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #00695c; }

    QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #c2c9cc; selection-background-color: #d8f1ee; }

    QTableWidget { background: #ffffff; gridline-color: #d5dde0; selection-background-color: #d8f1ee; }
    QHeaderView::section { background: #eef2f4; padding: 6px; border: 1px solid #c2c9cc; }

    QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
    QScrollBar::handle:vertical { background: #cfd8dc; border-radius: 6px; min-height: 24px; }

    QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
    QScrollBar::handle:horizontal { background: #cfd8dc; border-radius: 6px; min-width: 24px; }

    QDoubleSpinBox[inactive="true"] {
        background: #e0e0e0;
        color: #555;
    }
    """


def _qss_dark():
    return """ 
    QWidget { background: #2e3440; color: #eceff4; font-size: 13px; }

    QGroupBox {
        background: #3b4252;
        border: 2px solid #4c566a;
        border-radius: 8px;
        margin-top: 1.4em;
        padding: 14px 16px 12px 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: #88c0d0;
        font-weight: 600;
    }

    QTabWidget::pane { border: 1px solid #4c566a; background: #3b4252; }
    QTabBar::tab { background: #434c5e; border: 1px solid #4c566a; padding: 6px 12px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
    QTabBar::tab:selected { background: #3b4252; border-bottom-color: #3b4252; }

    QPushButton, QToolButton {
        background: #3b4252;
        border: 1px solid #4c566a;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover, QToolButton:hover { border-color: #81a1c1; }
    QPushButton:pressed, QToolButton:pressed { background: #2e3440; border-color: #81a1c1; }

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background: #2e3440;
        color: #eceff4;
        border: 1px solid #4c566a;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #81a1c1; }

    QComboBox QAbstractItemView { background: #2e3440; border: 1px solid #4c566a; selection-background-color: #434c5e; }

    QTableWidget { background: #2e3440; gridline-color: #4c566a; selection-background-color: #434c5e; }
    QHeaderView::section { background: #3b4252; padding: 6px; border: 1px solid #4c566a; }

    QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
    QScrollBar::handle:vertical { background: #4c566a; border-radius: 6px; min-height: 24px; }

    QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
    QScrollBar::handle:horizontal { background: #4c566a; border-radius: 6px; min-width: 24px; }

    QDoubleSpinBox[inactive="true"] {
        background: #e0e0e0;
        color: #555;
    }
    """


def apply_theme(app: QApplication, name: str = "light"):
    name = (name or "light").strip().lower()
    if name == "dark":
        app.setStyleSheet(_qss_dark())
    elif name in ("neutral", "calm", "teal"):
        app.setStyleSheet(_qss_neutral())
    else:
        app.setStyleSheet(_qss_light())
