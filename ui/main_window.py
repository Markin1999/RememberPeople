from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import db
from utils.colors import text_color_for_bg

STYLE = """
QMainWindow, QWidget {
    background-color: #0F0F1A;
    color: #E8E8F0;
    font-family: 'Helvetica Neue', Arial, sans-serif;
}
QPushButton {
    background-color: #1E1E30;
    color: #E8E8F0;
    border: 1px solid #2E2E4A;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2E2E4A;
    border: 1px solid #5B5BFF;
}
QPushButton:pressed {
    background-color: #5B5BFF;
}
QPushButton#navBtn {
    background-color: transparent;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
    font-size: 14px;
    font-weight: bold;
    color: #8888AA;
}
QPushButton#navBtn:hover {
    background-color: #1E1E30;
    color: #E8E8F0;
}
QPushButton#navBtn[active=true] {
    background-color: #1E1E30;
    color: #5B5BFF;
    border-left: 3px solid #5B5BFF;
}
QPushButton#primaryBtn {
    background-color: #5B5BFF;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #7B7BFF;
}
QPushButton#dangerBtn {
    background-color: #FF3B5C;
    color: white;
    border: none;
}
QPushButton#dangerBtn:hover {
    background-color: #FF6B85;
}
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
    background-color: #1E1E30;
    color: #E8E8F0;
    border: 1px solid #2E2E4A;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #5B5BFF;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #1E1E30;
    color: #E8E8F0;
    border: 1px solid #2E2E4A;
    selection-background-color: #5B5BFF;
}
QScrollBar:vertical {
    background: #0F0F1A;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2E2E4A;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QLabel#sectionTitle {
    font-size: 22px;
    font-weight: bold;
    color: #E8E8F0;
}
QLabel#subtitle {
    font-size: 13px;
    color: #8888AA;
}
QFrame#card {
    background-color: #1E1E30;
    border: 1px solid #2E2E4A;
    border-radius: 12px;
}
QFrame#card:hover {
    border: 1px solid #5B5BFF;
}
QFrame#separator {
    background-color: #2E2E4A;
    max-height: 1px;
    min-height: 1px;
}
"""

class NotificationBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notifBanner")
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(12, 8, 12, 8)
        self.setVisible(False)
        self.navigate_callback = None

    def refresh(self, navigate_callback=None):
        if navigate_callback:
            self.navigate_callback = navigate_callback

        # Clear
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        items = []

        # Manual promemoria
        try:
            for pm in db.get_promemoria_attivi():
                nome = f"{pm['persona_nome']} {pm['persona_cognome'] or ''}".strip()
                colore = pm['priorita_colore'] or '#FF3B5C'
                scad = f" — scade {pm['data_scadenza']}" if pm['data_scadenza'] else ""
                items.append({
                    'colore': colore,
                    'testo': f"{nome}: {pm['messaggio']}{scad}",
                    'persona_id': pm['persona_id'],
                    'tipo': 'manuale'
                })
        except Exception:
            pass

        # Automatic promemoria
        try:
            for auto in db.get_promemoria_automatici():
                nome = f"{auto['nome']} {auto['cognome'] or ''}".strip()
                colore = auto['priorita_colore'] or '#FF9500'
                gg = auto['giorni_silenzio']
                items.append({
                    'colore': colore,
                    'testo': f"{nome} — silenzio da {gg} giorni (soglia: {auto['soglia_giorni']})",
                    'persona_id': auto['id'],
                    'tipo': 'auto'
                })
        except Exception:
            pass

        if not items:
            self.setVisible(False)
            return

        self.setVisible(True)
        for item in items:
            row = QFrame()
            row.setStyleSheet(f"background-color: {item['colore']}22; border-radius: 8px; border-left: 4px solid {item['colore']};")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 10, 6)

            dot = QLabel("●")
            dot.setStyleSheet(f"color: {item['colore']}; font-size: 10px; background: transparent; border: none;")
            row_layout.addWidget(dot)

            lbl = QLabel(item['testo'])
            lbl.setStyleSheet("color: #E8E8F0; font-size: 12px; background: transparent; border: none;")
            lbl.setWordWrap(True)
            row_layout.addWidget(lbl, 1)

            btn = QPushButton("Vai →")
            btn.setFixedWidth(65)
            pid = item['persona_id']
            btn.setStyleSheet(f"background-color: {item['colore']}44; color: #E8E8F0; border: none; border-radius: 6px; padding: 4px 8px; font-size: 11px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, p=pid: self.navigate_callback and self.navigate_callback(p))
            row_layout.addWidget(btn)

            self.layout.addWidget(row)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RememberPeople")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(STYLE)

        # Init DB
        db.init_db()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #0A0A14; border-right: 1px solid #1E1E30;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Logo
        logo = QLabel("👥 Remember\nPeople")
        logo.setStyleSheet("color: #5B5BFF; font-size: 16px; font-weight: bold; padding: 0 10px 20px 10px; background: transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(logo)

        sep = QFrame(); sep.setObjectName("separator"); sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(10)

        # Nav buttons
        self.nav_buttons = {}
        nav_items = [
            ("persone", "👤  Persone"),
            ("promemoria", "🔔  Promemoria"),
            ("statistiche", "📊  Statistiche"),
            ("impostazioni", "⚙️  Impostazioni"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sidebar_layout.addStretch()

        version = QLabel("v1.0")
        version.setStyleSheet("color: #444466; font-size: 11px; padding: 0 10px; background: transparent;")
        sidebar_layout.addWidget(version)

        main_layout.addWidget(sidebar)

        # ── Content area ─────────────────────────────────────────
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Notification banner
        self.banner = NotificationBanner()
        self.banner.setStyleSheet("background-color: #0F0F1A; border-bottom: 1px solid #2E2E4A;")
        content_layout.addWidget(self.banner)

        # Pages
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # Import pages here to avoid circular imports
        from ui.persone import PersonePage
        from ui.promemoria import PromemoriePage
        from ui.statistiche import StatistichePage
        from ui.impostazioni import ImpostazioniPage

        self.pages = {
            "persone": PersonePage(self),
            "promemoria": PromemoriePage(self),
            "statistiche": StatistichePage(self),
            "impostazioni": ImpostazioniPage(self),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        main_layout.addWidget(content_area)

        # Start on persone
        self.switch_page("persone")

        # Refresh banner every 60 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_banner)
        self.timer.start(60000)
        self.refresh_banner()

    def switch_page(self, key, persona_id=None):
        for k, btn in self.nav_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.stack.setCurrentWidget(self.pages[key])
        page = self.pages[key]

        if hasattr(page, 'refresh'):
            page.refresh()

        if key == "persone" and persona_id and hasattr(page, 'open_persona'):
            page.open_persona(persona_id)

    def refresh_banner(self):
        self.banner.refresh(navigate_callback=lambda pid: self.switch_page("persone", persona_id=pid))

    def notify_refresh(self):
        """Called by child pages when data changes."""
        self.refresh_banner()
