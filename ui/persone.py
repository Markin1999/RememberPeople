from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QTextEdit, QDateEdit, QCheckBox,
    QMessageBox, QGridLayout, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import db
from utils.colors import pick_color, colored_badge_style, text_color_for_bg


class ColorButton(QPushButton):
    def __init__(self, hex_color="#3498DB", parent=None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setFixedSize(32, 32)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.hex_color};
                border: 2px solid #2E2E4A;
                border-radius: 16px;
            }}
            QPushButton:hover {{ border: 2px solid #5B5BFF; }}
        """)

    def set_color(self, hex_color):
        self.hex_color = hex_color
        self._update_style()


class TagWidget(QLabel):
    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        text_col = text_color_for_bg(color)
        self.setStyleSheet(f"""
            background-color: {color};
            color: {text_col};
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.setFixedHeight(22)


class PriorityBadge(QLabel):
    def __init__(self, text, color, parent=None):
        super().__init__(f"● {text}", parent)
        self.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent;")


# ─── Dialogs ─────────────────────────────────────────────────────────────────

class QuickCreateDialog(QDialog):
    """Create a tipo or priorità on the fly."""
    def __init__(self, mode="tipo", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setModal(True)
        title = "Crea nuovo tipo" if mode == "tipo" else "Crea nuova priorità"
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel(f"<b>{title}</b>"))

        layout.addWidget(QLabel("Nome:"))
        self.nome_edit = QLineEdit()
        layout.addWidget(self.nome_edit)

        if mode == "priorita":
            layout.addWidget(QLabel("Soglia giorni (promemoria automatico):"))
            from PyQt6.QtWidgets import QSpinBox
            self.soglia_spin = QSpinBox()
            self.soglia_spin.setRange(1, 365)
            self.soglia_spin.setValue(30)
            layout.addWidget(self.soglia_spin)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Colore:"))
        self.color_btn = ColorButton("#5B5BFF")
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick_color(self):
        c = pick_color(self, self.color_btn.hex_color)
        if c:
            self.color_btn.set_color(c)

    def get_data(self):
        data = {'nome': self.nome_edit.text().strip(), 'colore': self.color_btn.hex_color}
        if self.mode == "priorita":
            data['soglia_giorni'] = self.soglia_spin.value()
        return data


class PersonaDialog(QDialog):
    def __init__(self, persona=None, parent=None):
        super().__init__(parent)
        self.persona = persona
        self.setModal(True)
        self.setWindowTitle("Modifica persona" if persona else "Nuova persona")
        self.setMinimumWidth(500)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("<b>Nuova persona</b>" if not persona else f"<b>Modifica — {persona['nome']}</b>")
        title.setStyleSheet("font-size: 16px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(QLabel("Nome *"), 0, 0)
        self.nome_edit = QLineEdit()
        grid.addWidget(self.nome_edit, 0, 1)

        grid.addWidget(QLabel("Cognome"), 1, 0)
        self.cognome_edit = QLineEdit()
        grid.addWidget(self.cognome_edit, 1, 1)

        layout.addLayout(grid)

        # Priorità
        prio_row = QHBoxLayout()
        prio_row.addWidget(QLabel("Priorità:"))
        self.prio_combo = QComboBox()
        self.prio_combo.addItem("— nessuna —", None)
        self._load_priorita()
        prio_row.addWidget(self.prio_combo, 1)
        add_prio_btn = QPushButton("+ Crea")
        add_prio_btn.setFixedWidth(70)
        add_prio_btn.clicked.connect(self._create_priorita)
        prio_row.addWidget(add_prio_btn)
        layout.addLayout(prio_row)

        # Tipi
        layout.addWidget(QLabel("Tipi (uno o più):"))
        self.tipi_container = QWidget()
        self.tipi_layout = QHBoxLayout(self.tipi_container)
        self.tipi_layout.setContentsMargins(0, 0, 0, 0)
        self.tipi_layout.setSpacing(6)
        self.tipi_checks = {}
        self._load_tipi()
        add_tipo_btn = QPushButton("+ Crea tipo")
        add_tipo_btn.setFixedWidth(90)
        add_tipo_btn.clicked.connect(self._create_tipo)
        self.tipi_layout.addWidget(add_tipo_btn)
        self.tipi_layout.addStretch()
        layout.addWidget(self.tipi_container)

        # Note
        layout.addWidget(QLabel("Note generali:"))
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(80)
        layout.addWidget(self.note_edit)

        # Fill data if editing
        if persona:
            self.nome_edit.setText(persona['nome'])
            self.cognome_edit.setText(persona['cognome'] or "")
            self.note_edit.setText(persona['note_generali'] or "")
            if persona['priorita_id']:
                idx = self.prio_combo.findData(persona['priorita_id'])
                if idx >= 0:
                    self.prio_combo.setCurrentIndex(idx)
            tipi_persona = [t['id'] for t in db.get_tipi_persona(persona['id'])]
            for tid, cb in self.tipi_checks.items():
                cb.setChecked(tid in tipi_persona)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_priorita(self):
        current_data = self.prio_combo.currentData()
        while self.prio_combo.count() > 1:
            self.prio_combo.removeItem(1)
        for p in db.get_all_priorita():
            self.prio_combo.addItem(f"● {p['nome']}", p['id'])
        if current_data:
            idx = self.prio_combo.findData(current_data)
            if idx >= 0:
                self.prio_combo.setCurrentIndex(idx)

    def _load_tipi(self):
        checked = {tid for tid, cb in self.tipi_checks.items() if cb.isChecked()}
        # Remove old checkboxes
        for tid, cb in list(self.tipi_checks.items()):
            self.tipi_layout.removeWidget(cb)
            cb.deleteLater()
        self.tipi_checks.clear()

        for t in db.get_all_tipi():
            cb = QCheckBox(t['nome'])
            tc = text_color_for_bg(t['colore'])
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {t['colore']}; font-weight: bold; background: transparent; }}
                QCheckBox::indicator:checked {{ background-color: {t['colore']}; border-radius: 3px; }}
            """)
            cb.setChecked(t['id'] in checked)
            self.tipi_layout.insertWidget(self.tipi_layout.count() - 1, cb)
            self.tipi_checks[t['id']] = cb

    def _create_priorita(self):
        dlg = QuickCreateDialog(mode="priorita", parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.create_priorita(data['nome'], data['colore'], data['soglia_giorni'])
                self._load_priorita()

    def _create_tipo(self):
        dlg = QuickCreateDialog(mode="tipo", parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['nome']:
                db.create_tipo(data['nome'], data['colore'])
                self._load_tipi()

    def _validate_and_accept(self):
        if not self.nome_edit.text().strip():
            QMessageBox.warning(self, "Errore", "Il nome è obbligatorio.")
            return
        self.accept()

    def get_data(self):
        return {
            'nome': self.nome_edit.text().strip(),
            'cognome': self.cognome_edit.text().strip(),
            'note_generali': self.note_edit.toPlainText().strip(),
            'priorita_id': self.prio_combo.currentData(),
            'tipo_ids': [tid for tid, cb in self.tipi_checks.items() if cb.isChecked()]
        }


class InterazioneDialog(QDialog):
    def __init__(self, interazione=None, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Modifica interazione" if interazione else "Nuova interazione")
        self.setMinimumWidth(480)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("<b>Interazione</b>", styleSheet="font-size:16px;"))

        layout.addWidget(QLabel("Data:"))
        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDate(QDate.currentDate())
        layout.addWidget(self.data_edit)

        layout.addWidget(QLabel("Cosa mi ha detto:"))
        self.detto_edit = QTextEdit()
        self.detto_edit.setMinimumHeight(80)
        layout.addWidget(self.detto_edit)

        layout.addWidget(QLabel("Cosa so di lui/lei:"))
        self.so_edit = QTextEdit()
        self.so_edit.setMinimumHeight(80)
        layout.addWidget(self.so_edit)

        if interazione:
            y, m, d = map(int, str(interazione['data']).split('-'))
            self.data_edit.setDate(QDate(y, m, d))
            self.detto_edit.setText(interazione['cosa_ha_detto'] or "")
            self.so_edit.setText(interazione['cosa_so'] or "")

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            'data': self.data_edit.date().toPyDate(),
            'cosa_ha_detto': self.detto_edit.toPlainText().strip(),
            'cosa_so': self.so_edit.toPlainText().strip(),
        }


class PromemoriaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Nuovo promemoria")
        self.setMinimumWidth(420)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("<b>Nuovo promemoria</b>", styleSheet="font-size:16px;"))

        layout.addWidget(QLabel("Messaggio:"))
        self.msg_edit = QTextEdit()
        self.msg_edit.setMaximumHeight(80)
        layout.addWidget(self.msg_edit)

        layout.addWidget(QLabel("Data scadenza (opzionale):"))
        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDate(QDate.currentDate())
        layout.addWidget(self.data_edit)

        prio_row = QHBoxLayout()
        prio_row.addWidget(QLabel("Priorità:"))
        self.prio_combo = QComboBox()
        self.prio_combo.addItem("— nessuna —", None)
        for p in db.get_all_priorita():
            self.prio_combo.addItem(f"● {p['nome']}", p['id'])
        prio_row.addWidget(self.prio_combo, 1)
        layout.addLayout(prio_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            'messaggio': self.msg_edit.toPlainText().strip(),
            'data_scadenza': self.data_edit.date().toPyDate(),
            'priorita_id': self.prio_combo.currentData(),
        }


# ─── Person Card (in list) ────────────────────────────────────────────────────

class PersonCard(QFrame):
    def __init__(self, persona, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.on_click = on_click
        self.persona = persona

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Top row: name + priority
        top_row = QHBoxLayout()
        name = f"{persona['nome']} {persona['cognome'] or ''}".strip()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #E8E8F0; background: transparent;")
        top_row.addWidget(name_lbl)
        top_row.addStretch()
        if persona.get('priorita_nome'):
            badge = PriorityBadge(persona['priorita_nome'], persona['priorita_colore'] or '#888')
            top_row.addWidget(badge)
        layout.addLayout(top_row)

        # Tipi tags
        tipi = db.get_tipi_persona(persona['id'])
        if tipi:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(6)
            for t in tipi:
                tags_row.addWidget(TagWidget(t['nome'], t['colore']))
            tags_row.addStretch()
            layout.addLayout(tags_row)

        # Ultima interazione
        if persona.get('ultima_interazione'):
            sub = QLabel(f"Ultima interazione: {persona['ultima_interazione']}")
        else:
            sub = QLabel("Nessuna interazione registrata")
        sub.setStyleSheet("font-size: 11px; color: #8888AA; background: transparent;")
        layout.addWidget(sub)

    def mousePressEvent(self, event):
        self.on_click(self.persona['id'])


# ─── Persona Detail View ──────────────────────────────────────────────────────

class PersonaDetailView(QWidget):
    def __init__(self, persona_id, back_callback, parent_window, parent=None):
        super().__init__(parent)
        self.persona_id = persona_id
        self.back_callback = back_callback
        self.parent_window = parent_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        # Back button
        back_btn = QPushButton("← Torna alla lista")
        back_btn.setFixedWidth(160)
        back_btn.clicked.connect(back_callback)
        layout.addWidget(back_btn)

        # Header
        self.persona = db.get_persona(persona_id)
        name = f"{self.persona['nome']} {self.persona['cognome'] or ''}".strip()

        header_row = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setObjectName("sectionTitle")
        header_row.addWidget(name_lbl)
        header_row.addStretch()

        edit_btn = QPushButton("✏️ Modifica")
        edit_btn.clicked.connect(self._edit_persona)
        header_row.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Elimina")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_persona)
        header_row.addWidget(del_btn)
        layout.addLayout(header_row)

        # Info row
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        if self.persona.get('priorita_nome'):
            badge = PriorityBadge(self.persona['priorita_nome'], self.persona['priorita_colore'] or '#888')
            info_row.addWidget(badge)

        tipi = db.get_tipi_persona(persona_id)
        for t in tipi:
            info_row.addWidget(TagWidget(t['nome'], t['colore']))

        info_row.addStretch()
        layout.addLayout(info_row)

        # Note generali
        if self.persona.get('note_generali'):
            note_frame = QFrame()
            note_frame.setObjectName("card")
            note_layout = QVBoxLayout(note_frame)
            note_lbl = QLabel(f"📝 {self.persona['note_generali']}")
            note_lbl.setWordWrap(True)
            note_lbl.setStyleSheet("color: #AAAACC; font-size: 13px; background: transparent;")
            note_layout.addWidget(note_lbl)
            layout.addWidget(note_frame)

        sep = QFrame(); sep.setObjectName("separator"); layout.addWidget(sep)

        # Promemoria section
        prom_header = QHBoxLayout()
        prom_header.addWidget(QLabel("🔔 Promemoria", styleSheet="font-size:15px; font-weight:bold;"))
        prom_header.addStretch()
        add_prom_btn = QPushButton("+ Aggiungi promemoria")
        add_prom_btn.clicked.connect(self._add_promemoria)
        prom_header.addWidget(add_prom_btn)
        layout.addLayout(prom_header)

        self.prom_container = QWidget()
        self.prom_vbox = QVBoxLayout(self.prom_container)
        self.prom_vbox.setSpacing(6)
        self.prom_vbox.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.prom_container)

        sep2 = QFrame(); sep2.setObjectName("separator"); layout.addWidget(sep2)

        # Interazioni
        int_header = QHBoxLayout()
        int_header.addWidget(QLabel("💬 Interazioni", styleSheet="font-size:15px; font-weight:bold;"))
        int_header.addStretch()
        add_int_btn = QPushButton("+ Aggiungi interazione")
        add_int_btn.setObjectName("primaryBtn")
        add_int_btn.clicked.connect(self._add_interazione)
        int_header.addWidget(add_int_btn)
        layout.addLayout(int_header)

        # Scrollable interazioni
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.int_container = QWidget()
        self.int_vbox = QVBoxLayout(self.int_container)
        self.int_vbox.setSpacing(10)
        self.int_vbox.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.int_container)
        layout.addWidget(scroll, 1)

        self._refresh_promemoria()
        self._refresh_interazioni()

    def _refresh_promemoria(self):
        while self.prom_vbox.count():
            child = self.prom_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for pm in db.get_promemoria_persona(self.persona_id):
            row = QFrame()
            row.setObjectName("card")
            row.setStyleSheet(f"{'opacity: 0.5;' if pm['completato'] else ''}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            colore = pm.get('priorita_colore') or '#888888'
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {colore}; font-size:12px; background:transparent;")
            row_layout.addWidget(dot)

            txt = pm['messaggio']
            if pm['data_scadenza']:
                txt += f"  (scade {pm['data_scadenza']})"
            if pm['completato']:
                txt = f"✓ {txt}"
            lbl = QLabel(txt)
            lbl.setStyleSheet("background: transparent; color: #CCCCDD;")
            row_layout.addWidget(lbl, 1)

            if not pm['completato']:
                done_btn = QPushButton("✓ Fatto")
                done_btn.setFixedWidth(80)
                pid = pm['id']
                done_btn.clicked.connect(lambda _, i=pid: self._complete_promemoria(i))
                row_layout.addWidget(done_btn)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("dangerBtn")
            del_btn.setFixedWidth(36)
            pid = pm['id']
            del_btn.clicked.connect(lambda _, i=pid: self._delete_promemoria(i))
            row_layout.addWidget(del_btn)

            self.prom_vbox.addWidget(row)

        if not db.get_promemoria_persona(self.persona_id):
            self.prom_vbox.addWidget(QLabel("Nessun promemoria", styleSheet="color:#666688;"))

    def _refresh_interazioni(self):
        while self.int_vbox.count():
            child = self.int_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        interazioni = db.get_interazioni(self.persona_id)
        if not interazioni:
            lbl = QLabel("Nessuna interazione ancora.\nClicca '+ Aggiungi interazione' per iniziare.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666688; font-size: 14px;")
            self.int_vbox.addWidget(lbl)
            return

        for inter in interazioni:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)

            # Date header
            date_row = QHBoxLayout()
            date_lbl = QLabel(f"📅 {inter['data']}")
            date_lbl.setStyleSheet("color: #5B5BFF; font-weight: bold; background: transparent;")
            date_row.addWidget(date_lbl)
            date_row.addStretch()

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            iid = inter['id']
            edit_btn.clicked.connect(lambda _, i=iid: self._edit_interazione(i))
            date_row.addWidget(edit_btn)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("dangerBtn")
            del_btn.setFixedSize(30, 30)
            del_btn.clicked.connect(lambda _, i=iid: self._delete_interazione(i))
            date_row.addWidget(del_btn)

            card_layout.addLayout(date_row)

            if inter['cosa_ha_detto']:
                lbl = QLabel(f"<b>Cosa mi ha detto:</b> {inter['cosa_ha_detto']}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet("background: transparent; color: #CCCCEE;")
                card_layout.addWidget(lbl)

            if inter['cosa_so']:
                lbl2 = QLabel(f"<b>Cosa so:</b> {inter['cosa_so']}")
                lbl2.setWordWrap(True)
                lbl2.setStyleSheet("background: transparent; color: #AAAACC;")
                card_layout.addWidget(lbl2)

            self.int_vbox.addWidget(card)

        self.int_vbox.addStretch()

    def _add_interazione(self):
        dlg = InterazioneDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            db.create_interazione(self.persona_id, data['data'], data['cosa_ha_detto'], data['cosa_so'])
            self._refresh_interazioni()
            self.parent_window.notify_refresh()

    def _edit_interazione(self, interazione_id):
        interazioni = db.get_interazioni(self.persona_id)
        inter = next((i for i in interazioni if i['id'] == interazione_id), None)
        if not inter:
            return
        dlg = InterazioneDialog(interazione=inter, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            db.update_interazione(interazione_id, data['data'], data['cosa_ha_detto'], data['cosa_so'])
            self._refresh_interazioni()

    def _delete_interazione(self, interazione_id):
        reply = QMessageBox.question(self, "Conferma", "Eliminare questa interazione?")
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_interazione(interazione_id)
            self._refresh_interazioni()

    def _edit_persona(self):
        dlg = PersonaDialog(persona=self.persona, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            db.update_persona(self.persona_id, data['nome'], data['cognome'],
                              data['note_generali'], data['priorita_id'], data['tipo_ids'])
            self.back_callback()

    def _delete_persona(self):
        reply = QMessageBox.question(self, "Conferma", "Eliminare questa persona e tutti i dati correlati?")
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_persona(self.persona_id)
            self.back_callback()

    def _add_promemoria(self):
        dlg = PromemoriaDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data['messaggio']:
                db.create_promemoria(self.persona_id, data['priorita_id'], data['messaggio'], data['data_scadenza'])
                self._refresh_promemoria()
                self.parent_window.notify_refresh()

    def _complete_promemoria(self, pm_id):
        db.complete_promemoria(pm_id)
        self._refresh_promemoria()
        self.parent_window.notify_refresh()

    def _delete_promemoria(self, pm_id):
        db.delete_promemoria(pm_id)
        self._refresh_promemoria()
        self.parent_window.notify_refresh()


# ─── Main Persone Page ────────────────────────────────────────────────────────

class PersonePage(QWidget):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.current_detail = None

        self.stack = QStackedWidget = None
        self._build_ui()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── List view ──
        self.list_widget = QWidget()
        list_layout = QVBoxLayout(self.list_widget)
        list_layout.setContentsMargins(30, 24, 30, 24)
        list_layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Persone")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        add_btn = QPushButton("+ Nuova persona")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_persona)
        header_row.addWidget(add_btn)
        list_layout.addLayout(header_row)

        # Search + filter
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Cerca per nome...")
        self.search_edit.textChanged.connect(self._refresh_list)
        search_row.addWidget(self.search_edit, 2)

        self.tipo_filter = QComboBox()
        self.tipo_filter.addItem("Tutti i tipi", None)
        self.tipo_filter.currentIndexChanged.connect(self._refresh_list)
        search_row.addWidget(self.tipo_filter, 1)
        list_layout.addLayout(search_row)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.cards_container)
        list_layout.addWidget(scroll)

        # ── Detail view (replaced dynamically) ──
        self.detail_widget = QWidget()
        detail_placeholder = QVBoxLayout(self.detail_widget)

        self.main_layout.addWidget(self.list_widget)
        self.main_layout.addWidget(self.detail_widget)
        self.detail_widget.hide()

    def refresh(self):
        self._load_tipo_filter()
        self._refresh_list()

    def _load_tipo_filter(self):
        current = self.tipo_filter.currentData()
        while self.tipo_filter.count() > 1:
            self.tipo_filter.removeItem(1)
        for t in db.get_all_tipi():
            self.tipo_filter.addItem(t['nome'], t['id'])
        if current:
            idx = self.tipo_filter.findData(current)
            if idx >= 0:
                self.tipo_filter.setCurrentIndex(idx)

    def _refresh_list(self):
        # Clear cards
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        search = self.search_edit.text()
        tipo_id = self.tipo_filter.currentData()
        persone = db.get_all_persone(search=search, tipo_id=tipo_id)

        if not persone:
            lbl = QLabel("Nessuna persona trovata.\nClicca '+ Nuova persona' per iniziare!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666688; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl)
        else:
            for p in persone:
                card = PersonCard(p, on_click=self.open_persona)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def open_persona(self, persona_id):
        # Remove old detail widget content
        old_layout = self.detail_widget.layout()
        if old_layout:
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            from PyQt6.QtWidgets import QLayout
        else:
            from PyQt6.QtWidgets import QVBoxLayout as VB
            VB(self.detail_widget)

        detail = PersonaDetailView(
            persona_id=persona_id,
            back_callback=self._show_list,
            parent_window=self.parent_window,
            parent=self.detail_widget
        )
        self.detail_widget.layout().addWidget(detail)
        self.list_widget.hide()
        self.detail_widget.show()

    def _show_list(self):
        self.list_widget.show()
        self.detail_widget.hide()
        self.refresh()
        self.parent_window.notify_refresh()

    def _add_persona(self):
        dlg = PersonaDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            db.create_persona(data['nome'], data['cognome'], data['note_generali'],
                              data['priorita_id'], data['tipo_ids'])
            self._refresh_list()
            self.parent_window.notify_refresh()


# Fix missing import
from PyQt6.QtWidgets import QStackedWidget
