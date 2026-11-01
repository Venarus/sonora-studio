"""
SONORA Studio - Visual Design System & Themes
Windows 11 Fluent dark/light themes with graphite surfaces, custom accent colors,
glass subtle borders, and smooth component styling.
"""

from app.config import config


def get_stylesheet(theme: str = "dark", accent_hex: str = "#00E5A3") -> str:
    """Generate complete application QSS stylesheet."""
    if theme == "light":
        bg_main = "#F3F4F6"
        bg_surface = "#FFFFFF"
        bg_card = "#F9FAFB"
        bg_input = "#FFFFFF"
        border = "#E5E7EB"
        border_hover = "#D1D5DB"
        text_primary = "#111827"
        text_secondary = "#4B5563"
        text_muted = "#9CA3AF"
        sidebar_bg = "#E5E7EB"
        item_hover = "#F3F4F6"
        item_selected = "#E5E7EB"
    else:  # Dark Mode (Default)
        bg_main = "#0F1015"
        bg_surface = "#16171E"
        bg_card = "#1C1E26"
        bg_input = "#222530"
        border = "#2B2E3C"
        border_hover = "#3D4255"
        text_primary = "#F3F4F6"
        text_secondary = "#9CA3AF"
        text_muted = "#6B7280"
        sidebar_bg = "#12131A"
        item_hover = "#252835"
        item_selected = "#2D3142"

    accent = accent_hex
    accent_hover = "#33EAB5"
    accent_dark = "#00B882"
    danger = "#EF4444"
    warning = "#F59E0B"

    qss = f"""
    /* GLOBAL RESETS & FONTS */
    QWidget {{
        background-color: transparent;
        color: {text_primary};
        font-family: 'Segoe UI Variable Display', 'Segoe UI', 'SF Pro Text', sans-serif;
        font-size: 13px;
        selection-background-color: {accent};
        selection-color: #0F1015;
    }}

    QMainWindow {{
        background-color: {bg_main};
    }}

    /* SCROLLBARS */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {border_hover};
        min-height: 25px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {border_hover};
        min-width: 25px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* BUTTONS */
    QPushButton {{
        background-color: {bg_card};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 7px;
        padding: 7px 15px;
        font-weight: 500;
        outline: none;
    }}
    QPushButton:hover {{
        background-color: {item_hover};
        border-color: {border_hover};
    }}
    QPushButton:pressed {{
        background-color: {bg_input};
        border-color: {accent};
    }}
    QPushButton:disabled {{
        background-color: {bg_surface};
        color: {text_muted};
        border-color: {border};
    }}

    /* PRIMARY ACCENT BUTTONS */
    QPushButton#primaryButton {{
        background-color: {accent};
        color: #0D0E12;
        border: 1px solid {accent};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {accent_hover};
        border-color: {accent_hover};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {accent_dark};
    }}

    /* DANGER BUTTONS */
    QPushButton#dangerButton {{
        background-color: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
        font-weight: 600;
    }}
    QPushButton#dangerButton:hover {{
        background-color: rgba(239, 68, 68, 0.28);
        border-color: #EF4444;
    }}

    /* RECORD BUTTON (Big Studio Record) */
    QPushButton#bigRecordButton {{
        background-color: #EF4444;
        color: #FFFFFF;
        border-radius: 35px;
        font-size: 16px;
        font-weight: 700;
        border: 3px solid rgba(255, 255, 255, 0.2);
    }}
    QPushButton#bigRecordButton:hover {{
        background-color: #DC2626;
        border-color: rgba(255, 255, 255, 0.4);
    }}

    /* INPUTS & COMBOS */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {bg_input};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {bg_surface};
        color: {text_primary};
        border: 1px solid {border};
        selection-background-color: {accent};
        selection-color: #0D0E12;
        border-radius: 6px;
        padding: 4px;
    }}

    /* SLIDERS */
    QSlider::groove:horizontal {{
        border: none;
        height: 5px;
        background: {bg_input};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #FFFFFF;
        border: 2px solid {accent};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {accent};
        border-color: #FFFFFF;
    }}

    /* CHECKBOX & RADIO */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {text_primary};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {border_hover};
        border-radius: 4px;
        background-color: {bg_input};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}

    /* CARDS & FRAMES */
    QFrame#cardFrame {{
        background-color: {bg_surface};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    QFrame#innerCard {{
        background-color: {bg_card};
        border: 1px solid {border};
        border-radius: 8px;
    }}

    /* SIDEBAR */
    QFrame#leftSidebar {{
        background-color: {sidebar_bg};
        border-right: 1px solid {border};
    }}
    QFrame#rightSidebar {{
        background-color: {sidebar_bg};
        border-left: 1px solid {border};
    }}

    /* LISTS & TABLES */
    QListWidget, QTableWidget {{
        background-color: {bg_surface};
        border: 1px solid {border};
        border-radius: 8px;
        gridline-color: {border};
    }}
    QListWidget::item, QTableWidget::item {{
        padding: 8px;
        border-radius: 6px;
    }}
    QListWidget::item:hover, QTableWidget::item:hover {{
        background-color: {item_hover};
    }}
    QListWidget::item:selected, QTableWidget::item:selected {{
        background-color: {item_selected};
        color: {accent};
    }}

    /* PROGRESS BAR */
    QProgressBar {{
        background-color: {bg_input};
        border: 1px solid {border};
        border-radius: 5px;
        text-align: center;
        color: {text_primary};
        font-weight: 600;
        height: 12px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 4px;
    }}

    /* TOOLTIP */
    QToolTip {{
        background-color: {bg_card};
        color: {text_primary};
        border: 1px solid {border_hover};
        padding: 5px 8px;
        border-radius: 4px;
    }}
    """
    return qss
