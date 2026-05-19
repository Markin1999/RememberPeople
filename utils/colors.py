from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog

def hex_to_qcolor(hex_str):
    """Convert hex string like '#FF0000' to QColor."""
    return QColor(hex_str)

def qcolor_to_hex(qcolor):
    """Convert QColor to hex string."""
    return qcolor.name().upper()

def pick_color(parent=None, initial_hex="#3498DB"):
    """Open color picker dialog and return hex string or None if cancelled."""
    initial = QColor(initial_hex)
    color = QColorDialog.getColor(initial, parent, "Scegli colore")
    if color.isValid():
        return color.name().upper()
    return None

def text_color_for_bg(hex_bg):
    """Return black or white text color for best contrast on given background."""
    c = QColor(hex_bg)
    luminance = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return "#000000" if luminance > 128 else "#FFFFFF"

def colored_badge_style(hex_color, radius=10):
    """Return QSS stylesheet for a colored badge/pill."""
    text_col = text_color_for_bg(hex_color)
    return f"""
        background-color: {hex_color};
        color: {text_col};
        border-radius: {radius}px;
        padding: 2px 10px;
        font-weight: bold;
        font-size: 11px;
    """
