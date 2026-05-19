from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt
import db
from utils.colors import text_color_for_bg


class PromemoriePage(QWidget):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("Promemoria")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        sub = QLabel("Tutti i promemoria attivi e gli avvisi automatici.")
        sub.setObjectName("subtitle")
        layout.addWidget(sub)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #1E1E30;
                color: #8888AA;
                padding: 8px 20px;
                border: none;
                border-radius: 0;
            }
            QTabBar::tab:selected {
                color: #5B5BFF;
                border-bottom: 2px solid #5B5BFF;
                background: #1E1E30;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
        """)

        # Tab 1: Manuali
        self.tab_manuali = QWidget()
        manuali_layout = QVBoxLayout(self.tab_manuali)
        manuali_layout.setContentsMargins(0, 12, 0, 0)
        manuali_scroll = QScrollArea()
        manuali_scroll.setWidgetResizable(True)
        manuali_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.manuali_container = QWidget()
        self.manuali_vbox = QVBoxLayout(self.manuali_container)
        self.manuali_vbox.setSpacing(8)
        self.manuali_vbox.setContentsMargins(0, 0, 0, 0)
        manuali_scroll.setWidget(self.manuali_container)
        manuali_layout.addWidget(manuali_scroll)
        self.tabs.addTab(self.tab_manuali, "🔔 Promemoria manuali")

        # Tab 2: Automatici
        self.tab_auto = QWidget()
        auto_layout = QVBoxLayout(self.tab_auto)
        auto_layout.setContentsMargins(0, 12, 0, 0)
        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.auto_container = QWidget()
        self.auto_vbox = QVBoxLayout(self.auto_container)
        self.auto_vbox.setSpacing(8)
        self.auto_vbox.setContentsMargins(0, 0, 0, 0)
        auto_scroll.setWidget(self.auto_container)
        auto_layout.addWidget(auto_scroll)
        self.tabs.addTab(self.tab_auto, "⚡ Avvisi automatici")

        layout.addWidget(self.tabs)

    def refresh(self):
        self._refresh_manuali()
        self._refresh_auto()

    def _refresh_manuali(self):
        while self.manuali_vbox.count():
            child = self.manuali_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        promemoria = db.get_promemoria_attivi()
        if not promemoria:
            lbl = QLabel("Nessun promemoria attivo.\nAggiungi promemoria dalle schede personali.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666688; font-size: 14px; padding: 30px;")
            self.manuali_vbox.addWidget(lbl)
        else:
            for pm in promemoria:
                self.manuali_vbox.addWidget(self._make_promemoria_card(pm))

        self.manuali_vbox.addStretch()

    def _refresh_auto(self):
        while self.auto_vbox.count():
            child = self.auto_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        auto = db.get_promemoria_automatici()
        if not auto:
            lbl = QLabel("Nessun avviso automatico attivo.\nTutti i tuoi contatti sono stati raggiunti di recente!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666688; font-size: 14px; padding: 30px;")
            self.auto_vbox.addWidget(lbl)
        else:
            for item in auto:
                self.auto_vbox.addWidget(self._make_auto_card(item))

        self.auto_vbox.addStretch()

    def _make_promemoria_card(self, pm):
        card = QFrame()
        card.setObjectName("card")
        colore = pm.get('priorita_colore') or '#5B5BFF'
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: #1E1E30;
                border: 1px solid #2E2E4A;
                border-left: 4px solid {colore};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)

        info_layout = QVBoxLayout()
        nome = f"{pm['persona_nome']} {pm['persona_cognome'] or ''}".strip()

        top = QLabel(f"<b>{nome}</b>")
        top.setStyleSheet("background: transparent; color: #E8E8F0;")
        info_layout.addWidget(top)

        msg = QLabel(pm['messaggio'])
        msg.setWordWrap(True)
        msg.setStyleSheet("background: transparent; color: #AAAACC;")
        info_layout.addWidget(msg)

        if pm.get('data_scadenza'):
            scad = QLabel(f"📅 Scade: {pm['data_scadenza']}")
            scad.setStyleSheet(f"background: transparent; color: {colore}; font-size: 12px;")
            info_layout.addWidget(scad)

        if pm.get('priorita_nome'):
            prio = QLabel(f"● {pm['priorita_nome']}")
            prio.setStyleSheet(f"background: transparent; color: {colore}; font-size: 11px; font-weight: bold;")
            info_layout.addWidget(prio)

        layout.addLayout(info_layout, 1)

        btn_layout = QVBoxLayout()
        done_btn = QPushButton("✓ Fatto")
        done_btn.setFixedWidth(90)
        pid = pm['id']
        persona_id = pm['persona_id']
        done_btn.clicked.connect(lambda _, i=pid: self._complete(i))
        btn_layout.addWidget(done_btn)

        vai_btn = QPushButton("Vai →")
        vai_btn.setFixedWidth(90)
        vai_btn.clicked.connect(lambda _, p=persona_id: self.parent_window.switch_page("persone", persona_id=p))
        btn_layout.addWidget(vai_btn)

        layout.addLayout(btn_layout)
        return card

    def _make_auto_card(self, item):
        card = QFrame()
        card.setObjectName("card")
        colore = item.get('priorita_colore') or '#FF9500'
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: #1E1E30;
                border: 1px solid #2E2E4A;
                border-left: 4px solid {colore};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)

        info_layout = QVBoxLayout()
        nome = f"{item['nome']} {item['cognome'] or ''}".strip()

        top = QLabel(f"<b>{nome}</b>")
        top.setStyleSheet("background: transparent; color: #E8E8F0;")
        info_layout.addWidget(top)

        gg = item['giorni_silenzio']
        soglia = item['soglia_giorni']
        msg = QLabel(f"Non lo/la senti da {gg} giorni (soglia: {soglia} giorni)")
        msg.setStyleSheet("background: transparent; color: #AAAACC;")
        info_layout.addWidget(msg)

        if item.get('ultima_interazione'):
            ul = QLabel(f"Ultima interazione: {item['ultima_interazione']}")
            ul.setStyleSheet(f"background: transparent; color: {colore}; font-size: 12px;")
            info_layout.addWidget(ul)

        prio = QLabel(f"● {item['priorita_nome']}")
        prio.setStyleSheet(f"background: transparent; color: {colore}; font-size: 11px; font-weight: bold;")
        info_layout.addWidget(prio)

        layout.addLayout(info_layout, 1)

        vai_btn = QPushButton("Vai →")
        vai_btn.setFixedWidth(90)
        pid = item['id']
        vai_btn.clicked.connect(lambda _, p=pid: self.parent_window.switch_page("persone", persona_id=p))
        layout.addWidget(vai_btn)

        return card

    def _complete(self, pm_id):
        db.complete_promemoria(pm_id)
        self.refresh()
        self.parent_window.notify_refresh()
