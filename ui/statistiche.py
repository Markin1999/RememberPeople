from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt
import db

try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False


DARK_BG = '#0F0F1A'
CARD_BG = '#1E1E30'
TEXT_COLOR = '#E8E8F0'
ACCENT = '#5B5BFF'


def make_figure(figsize=(5, 3)):
    fig = Figure(figsize=figsize, facecolor=DARK_BG)
    return fig


class StatCard(QFrame):
    def __init__(self, title, value, subtitle="", color=ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color}; background: transparent;")
        layout.addWidget(val_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; color: #E8E8F0; background: transparent;")
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("font-size: 11px; color: #8888AA; background: transparent;")
            layout.addWidget(sub_lbl)


class StatistichePage(QWidget):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 24, 30, 24)
        outer.setSpacing(16)

        title = QLabel("Statistiche")
        title.setObjectName("sectionTitle")
        outer.addWidget(title)

        sub = QLabel("Panoramica delle tue relazioni e interazioni.")
        sub.setObjectName("subtitle")
        outer.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.content)
        outer.addWidget(scroll)

    def refresh(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                pass

        self._build_stat_cards()
        self._build_charts()
        self._build_top_persone()
        self._build_rischio_silenzio()
        self.content_layout.addStretch()

    def _build_stat_cards(self):
        try:
            all_persone = db.get_all_persone()
            n_persone = len(all_persone)

            conn = __import__('db').get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM interazioni")
            n_inter = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM promemoria WHERE completato=FALSE")
            n_prom = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tipi")
            n_tipi = cur.fetchone()[0]
            cur.close(); conn.close()

            grid = QGridLayout()
            grid.setSpacing(12)
            grid.addWidget(StatCard("Persone totali", n_persone, color='#5B5BFF'), 0, 0)
            grid.addWidget(StatCard("Interazioni totali", n_inter, color='#00C896'), 0, 1)
            grid.addWidget(StatCard("Promemoria attivi", n_prom, color='#FF9500'), 0, 2)
            grid.addWidget(StatCard("Tipi creati", n_tipi, color='#FF3B5C'), 0, 3)
            self.content_layout.addLayout(grid)
        except Exception as e:
            self.content_layout.addWidget(QLabel(f"Errore caricamento dati: {e}"))

    def _build_charts(self):
        if not HAS_MATPLOTLIB:
            self.content_layout.addWidget(QLabel("matplotlib non disponibile per i grafici."))
            return

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Chart 1: persone per tipo
        tipo_data = db.stats_persone_per_tipo()
        if tipo_data:
            fig1 = make_figure((4, 3))
            ax1 = fig1.add_subplot(111)
            ax1.set_facecolor(CARD_BG)
            labels = [r['nome'] for r in tipo_data]
            values = [r['totale'] for r in tipo_data]
            colors = [r['colore'] for r in tipo_data]
            wedges, texts, autotexts = ax1.pie(
                values, labels=labels, colors=colors,
                autopct='%1.0f%%', startangle=90,
                textprops={'color': TEXT_COLOR, 'fontsize': 9}
            )
            for at in autotexts:
                at.set_color(TEXT_COLOR)
            ax1.set_title("Persone per tipo", color=TEXT_COLOR, fontsize=11, pad=10)
            fig1.tight_layout()

            canvas1 = FigureCanvas(fig1)
            canvas1.setStyleSheet("background-color: #1E1E30; border-radius: 12px;")
            charts_row.addWidget(canvas1)

        # Chart 2: interazioni per mese
        mese_data = db.stats_interazioni_per_mese()
        if mese_data:
            fig2 = make_figure((5, 3))
            ax2 = fig2.add_subplot(111)
            ax2.set_facecolor(CARD_BG)
            fig2.patch.set_facecolor(DARK_BG)
            mesi = [r['mese'] for r in mese_data]
            totali = [r['totale'] for r in mese_data]
            ax2.bar(mesi, totali, color=ACCENT, alpha=0.8, width=0.6)
            ax2.set_title("Interazioni (ultimi 12 mesi)", color=TEXT_COLOR, fontsize=11)
            ax2.tick_params(colors=TEXT_COLOR, labelsize=8, axis='both')
            ax2.spines['bottom'].set_color('#2E2E4A')
            ax2.spines['left'].set_color('#2E2E4A')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            fig2.tight_layout()

            canvas2 = FigureCanvas(fig2)
            canvas2.setStyleSheet("background-color: #1E1E30; border-radius: 12px;")
            charts_row.addWidget(canvas2)

        if tipo_data or mese_data:
            self.content_layout.addLayout(charts_row)

    def _build_top_persone(self):
        top = db.stats_top_persone()
        if not top:
            return

        lbl = QLabel("🏆 Top 5 persone con più interazioni")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #E8E8F0;")
        self.content_layout.addWidget(lbl)

        for i, row in enumerate(top):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 10, 16, 10)

            rank = QLabel(f"#{i+1}")
            rank.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 16px; background: transparent; min-width: 30px;")
            card_layout.addWidget(rank)

            nome = f"{row['nome']} {row['cognome'] or ''}".strip()
            nome_lbl = QLabel(nome)
            nome_lbl.setStyleSheet("background: transparent; font-size: 14px; color: #E8E8F0;")
            card_layout.addWidget(nome_lbl, 1)

            count_lbl = QLabel(f"{row['totale_interazioni']} interazioni")
            count_lbl.setStyleSheet("background: transparent; color: #8888AA; font-size: 12px;")
            card_layout.addWidget(count_lbl)

            self.content_layout.addWidget(card)

    def _build_rischio_silenzio(self):
        rischio = db.get_promemoria_automatici()
        if not rischio:
            return

        lbl = QLabel("⚠️ Persone a rischio silenzio")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF9500;")
        self.content_layout.addWidget(lbl)

        for item in rischio[:5]:
            card = QFrame()
            card.setObjectName("card")
            colore = item.get('priorita_colore') or '#FF9500'
            card.setStyleSheet(f"""
                QFrame#card {{
                    background-color: #1E1E30;
                    border: 1px solid #2E2E4A;
                    border-left: 3px solid {colore};
                    border-radius: 10px;
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 10, 16, 10)

            nome = f"{item['nome']} {item['cognome'] or ''}".strip()
            nome_lbl = QLabel(nome)
            nome_lbl.setStyleSheet("background: transparent; font-size: 14px; color: #E8E8F0;")
            card_layout.addWidget(nome_lbl, 1)

            gg = QLabel(f"{item['giorni_silenzio']} giorni fa")
            gg.setStyleSheet(f"background: transparent; color: {colore}; font-weight: bold;")
            card_layout.addWidget(gg)

            self.content_layout.addWidget(card)
