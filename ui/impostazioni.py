from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QDialog, QDialogButtonBox,
    QLineEdit, QSpinBox, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt
import db
from utils.colors import pick_color, text_color_for_bg


class ColorDot(QLabel):
    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setStyleSheet(f"""
            background-color: {hex_color};
            border-radius: 10px;
            border: 2px solid #2E2E4A;
        """)


class EditTipoDialog(QDialog):
    def __init__(self, tipo=None, parent=None):
        super().__init__(parent)
        self.tipo = tipo
        self.setModal(True)
        self.setWindowTitle("Modifica tipo" if tipo else "Nuovo tipo")
        self.setMinimumWidth(320)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("<b>Nome:</b>"))
        self.nome_edit = QLineEdit()
        if tipo:
            self.nome_edit.setText(tipo['nome'])
        layout.addWidget(self.nome_edit)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Colore:"))
        self.current_color = tipo['colore'] if tipo else '#5B5BFF'
        self.color_dot = ColorDot(self.current_color)
        color_row.addWidget(self.color_dot)
        pick_btn = QPushButton("Cambia colore")
        pick_btn.clicked.connect(self._pick)
        color_row.addWidget(pick_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick(self):
        c = pick_color(self, self.current_color)
        if c:
            self.current_color = c
            self.color_dot.setStyleSheet(f"background-color: {c}; border-radius: 10px; border: 2px solid #2E2E4A;")

    def get_data(self):
        return {'nome': self.nome_edit.text().strip(), 'colore': self.current_color}


class EditPrioritaDialog(QDialog):
    def __init__(self, priorita=None, parent=None):
        super().__init__(parent)
        self.priorita = priorita
        self.setModal(True)
        self.setWindowTitle("Modifica priorità" if priorita else "Nuova priorità")
        self.setMinimumWidth(340)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("<b>Nome:</b>"))
        self.nome_edit = QLineEdit()
        if priorita:
            self.nome_edit.setText(priorita['nome'])
        layout.addWidget(self.nome_edit)

        layout.addWidget(QLabel("Soglia giorni (promemoria automatico):"))
        self.soglia_spin = QSpinBox()
        self.soglia_spin.setRange(1, 365)
        self.soglia_spin.setValue(priorita['soglia_giorni'] if priorita else 30)
        layout.addWidget(self.soglia_spin)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Colore:"))
        self.current_color = priorita['colore'] if priorita else '#FF3B5C'
        self.color_dot = ColorDot(self.current_color)
        color_row.addWidget(self.color_dot)
        pick_btn = QPushButton("Cambia colore")
        pick_btn.clicked.connect(self._pick)
        color_row.addWidget(pick_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick(self):
        c = pick_color(self, self.current_color)
        if c:
            self.current_color = c
            self.color_dot.setStyleSheet(f"background-color: {c}; border-radius: 10px; border: 2px solid #2E2E4A;")

    def get_data(self):
        return {
            'nome': self.nome_edit.text().strip(),
            'colore': self.current_color,
            'soglia_giorni': self.soglia_spin.value()
        }


class ImpostazioniPage(QWidget):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("Impostazioni")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        sub = QLabel("Gestisci i tuoi tipi e livelli di priorità.")
        sub.setObjectName("subtitle")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #1E1E30;
                color: #8888AA;
                padding: 8px 20px;
                border: none;
            }
            QTabBar::tab:selected {
                color: #5B5BFF;
                border-bottom: 2px solid #5B5BFF;
                background: #1E1E30;
            }
            QTabWidget::pane { border: none; background: transparent; }
        """)

        # Tab Tipi
        self.tab_tipi = QWidget()
        tipi_layout = QVBoxLayout(self.tab_tipi)
        tipi_layout.setContentsMargins(0, 12, 0, 0)
        tipi_layout.setSpacing(12)

        add_tipo_btn = QPushButton("+ Crea nuovo tipo")
        add_tipo_btn.setObjectName("primaryBtn")
        add_tipo_btn.setFixedWidth(180)
        add_tipo_btn.clicked.connect(self._create_tipo)
        tipi_layout.addWidget(add_tipo_btn)

        tipi_scroll = QScrollArea()
        tipi_scroll.setWidgetResizable(True)
        tipi_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tipi_container = QWidget()
        self.tipi_vbox = QVBoxLayout(self.tipi_container)
        self.tipi_vbox.setSpacing(8)
        self.tipi_vbox.setContentsMargins(0, 0, 0, 0)
        tipi_scroll.setWidget(self.tipi_container)
        tipi_layout.addWidget(tipi_scroll)
        self.tabs.addTab(self.tab_tipi, "🏷️ Tipi")

        # Tab Priorità
        self.tab_prio = QWidget()
        prio_layout = QVBoxLayout(self.tab_prio)
        prio_layout.setContentsMargins(0, 12, 0, 0)
        prio_layout.setSpacing(12)

        add_prio_btn = QPushButton("+ Crea nuova priorità")
        add_prio_btn.setObjectName("primaryBtn")
        add_prio_btn.setFixedWidth(200)
        add_prio_btn.clicked.connect(self._create_priorita)
        prio_layout.addWidget(add_prio_btn)

        prio_scroll = QScrollArea()
        prio_scroll.setWidgetResizable(True)
        prio_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.prio_container = QWidget()
        self.prio_vbox = QVBoxLayout(self.prio_container)
        self.prio_vbox.setSpacing(8)
        self.prio_vbox.setContentsMargins(0, 0, 0, 0)
        prio_scroll.setWidget(self.prio_container)
        prio_layout.addWidget(prio_scroll)
        self.tabs.addTab(self.tab_prio, "⭐ Priorità")

        layout.addWidget(self.tabs)

    def refresh(self):
        self._refresh_tipi()
        self._refresh_priorita()

    def _refresh_tipi(self):
        while self.tipi_vbox.count():
            child = self.tipi_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tipi = db.get_all_tipi()
        if not tipi:
            self.tipi_vbox.addWidget(QLabel("Nessun tipo creato ancora.", styleSheet="color:#666688;"))
        else:
            for t in tipi:
                self.tipi_vbox.addWidget(self._make_tipo_row(t))
        self.tipi_vbox.addStretch()

    def _refresh_priorita(self):
        while self.prio_vbox.count():
            child = self.prio_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        priorita = db.get_all_priorita()
        if not priorita:
            self.prio_vbox.addWidget(QLabel("Nessuna priorità creata ancora.", styleSheet="color:#666688;"))
        else:
            for p in priorita:
                self.prio_vbox.addWidget(self._make_prio_row(p))
        self.prio_vbox.addStretch()

    def _make_tipo_row(self, tipo):
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)

        layout.addWidget(ColorDot(tipo['colore']))

        nome = QLabel(tipo['nome'])
        nome.setStyleSheet(f"color: {tipo['colore']}; font-weight: bold; font-size: 14px; background: transparent;")
        layout.addWidget(nome, 1)

        edit_btn = QPushButton("✏️ Modifica")
        edit_btn.setFixedWidth(90)
        tid = tipo['id']
        edit_btn.clicked.connect(lambda _, t=tipo: self._edit_tipo(t))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setObjectName("dangerBtn")
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(lambda _, i=tid: self._delete_tipo(i))
        layout.addWidget(del_btn)

        return card

    def _make_prio_row(self, priorita):
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)

        layout.addWidget(ColorDot(priorita['colore']))

        nome = QLabel(priorita['nome'])
        nome.setStyleSheet(f"color: {priorita['colore']}; font-weight: bold; font-size: 14px; background: transparent;")
        layout.addWidget(nome)

        soglia = QLabel(f"ogni {priorita['soglia_giorni']} giorni")
        soglia.setStyleSheet("color: #8888AA; font-size: 12px; background: transparent;")
        layout.addWidget(soglia, 1)

        edit_btn = QPushButton("✏️ Modifica")
        edit_btn.setFixedWidth(90)
        edit_btn.clicked.connect(lambda _, p=priorita: self._edit_priorita(p))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setObjectName("dangerBtn")
        del_btn.setFixedWidth(40)
        pid = priorita['id']
        del_btn.clicked.connect(lambda _, i=pid: self._delete_priorita(i))
        layout.addWidget(del_btn)

        return card

    def _create_tipo(self):
        dlg = EditTipoDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.create_tipo(data['nome'], data['colore'])
                self._refresh_tipi()

    def _edit_tipo(self, tipo):
        dlg = EditTipoDialog(tipo=tipo, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.update_tipo(tipo['id'], data['nome'], data['colore'])
                self._refresh_tipi()

    def _delete_tipo(self, tipo_id):
        reply = QMessageBox.question(self, "Conferma", "Eliminare questo tipo?")
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_tipo(tipo_id)
            self._refresh_tipi()

    def _create_priorita(self):
        dlg = EditPrioritaDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.create_priorita(data['nome'], data['colore'], data['soglia_giorni'])
                self._refresh_priorita()
                self.parent_window.notify_refresh()

    def _edit_priorita(self, priorita):
        dlg = EditPrioritaDialog(priorita=priorita, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.update_priorita(priorita['id'], data['nome'], data['colore'], data['soglia_giorni'])
                self._refresh_priorita()
                self.parent_window.notify_refresh()

    def _delete_priorita(self, priorita_id):
        reply = QMessageBox.question(self, "Conferma", "Eliminare questa priorità?")
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_priorita(priorita_id)
            self._refresh_priorita()
            self.parent_window.notify_refresh()
