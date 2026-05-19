import os
import sys
import threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
import db

# ─── Flask keep-alive per Render + UptimeRobot ───────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 RememberPeople Bot is running!", 200

@flask_app.route("/ping")
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# ─── Stati conversazione ─────────────────────────────────────────────────────
(
    # Nuova persona
    NP_NOME, NP_COGNOME, NP_PRIORITA, NP_TIPI, NP_NOTE,
    # Nuova interazione
    NI_PERSONA, NI_DATA, NI_DETTO, NI_SO,
    # Nuovo promemoria
    NPM_PERSONA, NPM_MESSAGGIO, NPM_DATA, NPM_PRIORITA,
    # Nuova priorità
    NPRIO_NOME, NPRIO_COLORE, NPRIO_SOGLIA,
    # Nuovo tipo
    NTIPO_NOME, NTIPO_COLORE,
    # Cerca
    CERCA_QUERY,
) = range(19)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def fmt_persona(p, tipi=None):
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    lines = [f"👤 *{nome}*"]
    if p.get('priorita_nome'):
        lines.append(f"● Priorità: {p['priorita_nome']}")
    if tipi:
        tags = " · ".join(t['nome'] for t in tipi)
        lines.append(f"🏷️ {tags}")
    if p.get('ultima_interazione'):
        lines.append(f"📅 Ultima interazione: {p['ultima_interazione']}")
    else:
        lines.append("📅 Nessuna interazione ancora")
    return "\n".join(lines)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Persone", callback_data="menu_persone"),
         InlineKeyboardButton("🔔 Promemoria", callback_data="menu_promemoria")],
        [InlineKeyboardButton("📊 Statistiche", callback_data="menu_stats"),
         InlineKeyboardButton("⚙️ Impostazioni", callback_data="menu_impostazioni")],
    ])

def back_keyboard(back_to="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Indietro", callback_data=f"back_{back_to}")]])

# ─── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👥 *RememberPeople*\nCosa vuoi fare?",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ─── Menu principale ─────────────────────────────────────────────────────────

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu_persone":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Cerca persona", callback_data="persone_cerca"),
             InlineKeyboardButton("📋 Tutte le persone", callback_data="persone_lista")],
            [InlineKeyboardButton("➕ Nuova persona", callback_data="persone_nuova")],
            [InlineKeyboardButton("← Menu", callback_data="back_menu")],
        ])
        await q.edit_message_text("👥 *Persone*", parse_mode="Markdown", reply_markup=kb)

    elif data == "menu_promemoria":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Promemoria attivi", callback_data="promemoria_lista")],
            [InlineKeyboardButton("⚡ Avvisi automatici", callback_data="promemoria_auto")],
            [InlineKeyboardButton("← Menu", callback_data="back_menu")],
        ])
        await q.edit_message_text("🔔 *Promemoria*", parse_mode="Markdown", reply_markup=kb)

    elif data == "menu_stats":
        await show_stats(q)

    elif data == "menu_impostazioni":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷️ Tipi", callback_data="imp_tipi"),
             InlineKeyboardButton("⭐ Priorità", callback_data="imp_priorita")],
            [InlineKeyboardButton("← Menu", callback_data="back_menu")],
        ])
        await q.edit_message_text("⚙️ *Impostazioni*", parse_mode="Markdown", reply_markup=kb)

    elif data == "back_menu":
        await q.edit_message_text("👥 *RememberPeople*\nCosa vuoi fare?",
                                   parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "persone_lista":
        await show_persone_lista(q, ctx)

    elif data == "persone_cerca":
        await q.edit_message_text("🔍 Scrivi il nome da cercare:")
        ctx.user_data['action'] = 'cerca'

    elif data == "promemoria_lista":
        await show_promemoria(q)

    elif data == "promemoria_auto":
        await show_promemoria_auto(q)

    elif data == "imp_tipi":
        await show_tipi(q)

    elif data == "imp_priorita":
        await show_priorita(q)

    elif data.startswith("persona_"):
        pid = int(data.split("_")[1])
        await show_persona_detail(q, ctx, pid)

    elif data.startswith("persona_inter_"):
        pid = int(data.split("_")[2])
        await show_interazioni(q, pid)

    elif data.startswith("persona_prom_"):
        pid = int(data.split("_")[2])
        await show_promemoria_persona(q, pid)

    elif data.startswith("prom_done_"):
        pm_id = int(data.split("_")[2])
        db.complete_promemoria(pm_id)
        await show_promemoria(q)

# ─── Lista persone ────────────────────────────────────────────────────────────

async def show_persone_lista(q, ctx, search=""):
    persone = db.get_all_persone(search=search)
    if not persone:
        testo = "Nessuna persona trovata." if search else "Nessuna persona ancora."
        await q.edit_message_text(testo, reply_markup=back_keyboard("menu_persone"))
        return

    buttons = []
    for p in persone[:20]:
        nome = f"{p['nome']} {p['cognome'] or ''}".strip()
        prio = f" ●" if p.get('priorita_nome') else ""
        buttons.append([InlineKeyboardButton(f"{nome}{prio}", callback_data=f"persona_{p['id']}")])

    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_persone")])
    await q.edit_message_text(
        f"👥 *{len(persone)} persone*" + (f" per '{search}'" if search else ""),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ─── Dettaglio persona ────────────────────────────────────────────────────────

async def show_persona_detail(q, ctx, persona_id):
    p = db.get_persona(persona_id)
    if not p:
        await q.edit_message_text("Persona non trovata.")
        return
    tipi = db.get_tipi_persona(persona_id)
    testo = fmt_persona(p, tipi)
    if p.get('note_generali'):
        testo += f"\n\n📝 _{p['note_generali']}_"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Interazioni", callback_data=f"persona_inter_{persona_id}"),
         InlineKeyboardButton("🔔 Promemoria", callback_data=f"persona_prom_{persona_id}")],
        [InlineKeyboardButton("➕ Nuova interazione", callback_data=f"nuova_inter_{persona_id}")],
        [InlineKeyboardButton("← Lista", callback_data="persone_lista")],
    ])
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=kb)
    ctx.user_data['current_persona'] = persona_id

# ─── Interazioni persona ──────────────────────────────────────────────────────

async def show_interazioni(q, persona_id):
    interazioni = db.get_interazioni(persona_id)
    p = db.get_persona(persona_id)
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()

    if not interazioni:
        testo = f"*{nome}* — nessuna interazione ancora."
    else:
        lines = [f"💬 *{nome}* — {len(interazioni)} interazioni\n"]
        for i in interazioni[:5]:
            lines.append(f"📅 *{i['data']}*")
            if i['cosa_ha_detto']:
                lines.append(f"› {i['cosa_ha_detto'][:100]}")
            if i['cosa_so']:
                lines.append(f"› _{i['cosa_so'][:80]}_")
            lines.append("")
        testo = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Persona", callback_data=f"persona_{persona_id}")],
    ])
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=kb)

# ─── Promemoria persona ───────────────────────────────────────────────────────

async def show_promemoria_persona(q, persona_id):
    promemoria = db.get_promemoria_persona(persona_id)
    p = db.get_persona(persona_id)
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()

    if not promemoria:
        testo = f"*{nome}* — nessun promemoria."
        buttons = [[InlineKeyboardButton("← Persona", callback_data=f"persona_{persona_id}")]]
    else:
        lines = [f"🔔 *Promemoria — {nome}*\n"]
        buttons = []
        for pm in promemoria:
            stato = "✓" if pm['completato'] else "●"
            scad = f" ({pm['data_scadenza']})" if pm['data_scadenza'] else ""
            lines.append(f"{stato} {pm['messaggio']}{scad}")
            if not pm['completato']:
                buttons.append([InlineKeyboardButton(
                    f"✓ Fatto: {pm['messaggio'][:30]}",
                    callback_data=f"prom_done_{pm['id']}"
                )])
        testo = "\n".join(lines)
        buttons.append([InlineKeyboardButton("← Persona", callback_data=f"persona_{persona_id}")])

    await q.edit_message_text(testo, parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

# ─── Promemoria globali ───────────────────────────────────────────────────────

async def show_promemoria(q):
    promemoria = db.get_promemoria_attivi()
    if not promemoria:
        await q.edit_message_text("✅ Nessun promemoria attivo!", reply_markup=back_keyboard("menu_promemoria"))
        return

    lines = ["🔔 *Promemoria attivi*\n"]
    buttons = []
    for pm in promemoria:
        nome = f"{pm['persona_nome']} {pm['persona_cognome'] or ''}".strip()
        scad = f" — {pm['data_scadenza']}" if pm['data_scadenza'] else ""
        prio = f" [{pm['priorita_nome']}]" if pm.get('priorita_nome') else ""
        lines.append(f"● *{nome}*{prio}\n  {pm['messaggio']}{scad}")
        buttons.append([InlineKeyboardButton(
            f"✓ Fatto: {pm['messaggio'][:35]}",
            callback_data=f"prom_done_{pm['id']}"
        )])

    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_promemoria")])
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

async def show_promemoria_auto(q):
    auto = db.get_promemoria_automatici()
    if not auto:
        await q.edit_message_text("✅ Nessun avviso automatico!\nTutti i contatti sono aggiornati.",
                                   reply_markup=back_keyboard("menu_promemoria"))
        return

    lines = ["⚡ *Avvisi automatici*\n"]
    buttons = []
    for item in auto:
        nome = f"{item['nome']} {item['cognome'] or ''}".strip()
        lines.append(f"● *{nome}* — {item['giorni_silenzio']} giorni fa\n  Soglia: {item['soglia_giorni']} giorni")
        buttons.append([InlineKeyboardButton(f"→ {nome}", callback_data=f"persona_{item['id']}")])

    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_promemoria")])
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

# ─── Statistiche ─────────────────────────────────────────────────────────────

async def show_stats(q):
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM persone")
        n_p = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM interazioni")
        n_i = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM promemoria WHERE completato=FALSE")
        n_pm = cur.fetchone()[0]
        cur.close(); conn.close()

        top = db.stats_top_persone()
        rischio = db.get_promemoria_automatici()

        lines = [
            "📊 *Statistiche*\n",
            f"👤 Persone: *{n_p}*",
            f"💬 Interazioni: *{n_i}*",
            f"🔔 Promemoria attivi: *{n_pm}*",
        ]

        if top:
            lines.append("\n🏆 *Top contatti:*")
            for i, r in enumerate(top[:3]):
                nome = f"{r['nome']} {r['cognome'] or ''}".strip()
                lines.append(f"{i+1}. {nome} — {r['totale_interazioni']} interazioni")

        if rischio:
            lines.append(f"\n⚠️ *A rischio silenzio: {len(rischio)} persone*")

        await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                                   reply_markup=back_keyboard("menu"))
    except Exception as e:
        await q.edit_message_text(f"Errore: {e}", reply_markup=back_keyboard("menu"))

# ─── Tipi ─────────────────────────────────────────────────────────────────────

async def show_tipi(q):
    tipi = db.get_all_tipi()
    if not tipi:
        testo = "🏷️ *Tipi*\nNessun tipo creato ancora."
    else:
        lines = ["🏷️ *Tipi esistenti:*\n"]
        for t in tipi:
            lines.append(f"● {t['nome']} ({t['colore']})")
        testo = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Crea nuovo tipo", callback_data="crea_tipo")],
        [InlineKeyboardButton("← Impostazioni", callback_data="menu_impostazioni")],
    ])
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=kb)

async def show_priorita(q):
    priorita = db.get_all_priorita()
    if not priorita:
        testo = "⭐ *Priorità*\nNessuna priorità creata ancora."
    else:
        lines = ["⭐ *Priorità esistenti:*\n"]
        for p in priorita:
            lines.append(f"● {p['nome']} — ogni {p['soglia_giorni']} giorni ({p['colore']})")
        testo = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Crea nuova priorità", callback_data="crea_priorita")],
        [InlineKeyboardButton("← Impostazioni", callback_data="menu_impostazioni")],
    ])
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=kb)

# ─── Conversazioni: Nuova Persona ────────────────────────────────────────────

async def nuova_persona_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
        await q.edit_message_text("➕ *Nuova persona*\n\nInserisci il *nome*:", parse_mode="Markdown")
    else:
        await update.message.reply_text("➕ *Nuova persona*\n\nInserisci il *nome*:", parse_mode="Markdown")
    ctx.user_data['np'] = {}
    return NP_NOME

async def np_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['np']['nome'] = update.message.text.strip()
    await update.message.reply_text("Inserisci il *cognome* (o /salta):", parse_mode="Markdown")
    return NP_COGNOME

async def np_cognome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text.strip()
    ctx.user_data['np']['cognome'] = "" if testo == "/salta" else testo

    priorita = db.get_all_priorita()
    if not priorita:
        ctx.user_data['np']['priorita_id'] = None
        await update.message.reply_text("Nessuna priorità disponibile. Inserisci le *note generali* (o /salta):", parse_mode="Markdown")
        return NP_NOTE

    buttons = [[InlineKeyboardButton(p['nome'], callback_data=f"sel_prio_{p['id']}")] for p in priorita]
    buttons.append([InlineKeyboardButton("Nessuna", callback_data="sel_prio_none")])
    await update.message.reply_text("Scegli la *priorità*:", parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(buttons))
    return NP_PRIORITA

async def np_priorita(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    ctx.user_data['np']['priorita_id'] = None if data == "sel_prio_none" else int(data.split("_")[2])

    tipi = db.get_all_tipi()
    ctx.user_data['np']['tipo_ids'] = []
    if not tipi:
        await q.edit_message_text("Nessun tipo disponibile.\n\nInserisci le *note generali* (o /salta):", parse_mode="Markdown")
        return NP_NOTE

    buttons = [[InlineKeyboardButton(t['nome'], callback_data=f"sel_tipo_{t['id']}")] for t in tipi]
    buttons.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="sel_tipo_done")])
    ctx.user_data['np']['tipi_msg'] = await q.edit_message_text(
        "Scegli i *tipi* (puoi selezionarne più di uno):",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NP_TIPI

async def np_tipi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "sel_tipo_done":
        await q.edit_message_text("Inserisci le *note generali* (o /salta):", parse_mode="Markdown")
        return NP_NOTE

    tipo_id = int(data.split("_")[2])
    ids = ctx.user_data['np']['tipo_ids']
    if tipo_id in ids:
        ids.remove(tipo_id)
    else:
        ids.append(tipo_id)

    tipi = db.get_all_tipi()
    buttons = []
    for t in tipi:
        mark = "✅ " if t['id'] in ids else ""
        buttons.append([InlineKeyboardButton(f"{mark}{t['nome']}", callback_data=f"sel_tipo_{t['id']}")])
    buttons.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="sel_tipo_done")])

    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    return NP_TIPI

async def np_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text.strip()
    ctx.user_data['np']['note'] = "" if testo == "/salta" else testo

    data = ctx.user_data['np']
    persona = db.create_persona(
        data['nome'], data.get('cognome', ''),
        data.get('note', ''), data.get('priorita_id'),
        data.get('tipo_ids', [])
    )
    await update.message.reply_text(
        f"✅ *{data['nome']} {data.get('cognome', '')}* salvato!".strip(),
        parse_mode="Markdown", reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# ─── Conversazioni: Nuova Interazione ────────────────────────────────────────

async def nuova_inter_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    persona_id = int(q.data.split("_")[2])
    ctx.user_data['ni'] = {'persona_id': persona_id}
    p = db.get_persona(persona_id)
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    await q.edit_message_text(f"💬 Nuova interazione con *{nome}*\n\nCosa ti ha detto? (o /salta)", parse_mode="Markdown")
    return NI_DETTO

async def ni_detto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text.strip()
    ctx.user_data['ni']['detto'] = "" if testo == "/salta" else testo
    await update.message.reply_text("Cosa sai di lui/lei? (o /salta)")
    return NI_SO

async def ni_so(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text.strip()
    ctx.user_data['ni']['so'] = "" if testo == "/salta" else testo
    from datetime import date
    data = ctx.user_data['ni']
    db.create_interazione(data['persona_id'], date.today(), data.get('detto', ''), data.get('so', ''))
    await update.message.reply_text("✅ Interazione salvata!", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Conversazioni: Nuova Priorità ───────────────────────────────────────────

async def crea_priorita_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data['nprio'] = {}
    await q.edit_message_text("⭐ *Nuova priorità*\n\nNome:", parse_mode="Markdown")
    return NPRIO_NOME

async def nprio_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['nprio']['nome'] = update.message.text.strip()
    await update.message.reply_text("Colore in formato HEX (es. #FF3B5C):")
    return NPRIO_COLORE

async def nprio_colore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colore = update.message.text.strip()
    if not colore.startswith('#') or len(colore) != 7:
        await update.message.reply_text("Formato non valido. Usa #RRGGBB (es. #FF3B5C):")
        return NPRIO_COLORE
    ctx.user_data['nprio']['colore'] = colore
    await update.message.reply_text("Soglia giorni per promemoria automatico (es. 30):")
    return NPRIO_SOGLIA

async def nprio_soglia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        soglia = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Inserisci un numero intero (es. 30):")
        return NPRIO_SOGLIA
    data = ctx.user_data['nprio']
    db.create_priorita(data['nome'], data['colore'], soglia)
    await update.message.reply_text(f"✅ Priorità *{data['nome']}* creata!", parse_mode="Markdown",
                                     reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Conversazioni: Nuovo Tipo ────────────────────────────────────────────────

async def crea_tipo_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data['ntipo'] = {}
    await q.edit_message_text("🏷️ *Nuovo tipo*\n\nNome:", parse_mode="Markdown")
    return NTIPO_NOME

async def ntipo_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['ntipo']['nome'] = update.message.text.strip()
    await update.message.reply_text("Colore in formato HEX (es. #3498DB):")
    return NTIPO_COLORE

async def ntipo_colore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colore = update.message.text.strip()
    if not colore.startswith('#') or len(colore) != 7:
        await update.message.reply_text("Formato non valido. Usa #RRGGBB (es. #3498DB):")
        return NTIPO_COLORE
    data = ctx.user_data['ntipo']
    db.create_tipo(data['nome'], colore)
    await update.message.reply_text(f"✅ Tipo *{data['nome']}* creato!", parse_mode="Markdown",
                                     reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Testo libero (cerca) ────────────────────────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    action = ctx.user_data.get('action')
    if action == 'cerca':
        ctx.user_data['action'] = None
        persone = db.get_all_persone(search=update.message.text.strip())
        if not persone:
            await update.message.reply_text("Nessuna persona trovata.", reply_markup=main_keyboard())
            return
        buttons = []
        for p in persone[:15]:
            nome = f"{p['nome']} {p['cognome'] or ''}".strip()
            buttons.append([InlineKeyboardButton(nome, callback_data=f"persona_{p['id']}")])
        buttons.append([InlineKeyboardButton("← Menu", callback_data="back_menu")])
        await update.message.reply_text(f"🔍 Trovate {len(persone)} persone:",
                                         reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("Usa il menu:", reply_markup=main_keyboard())

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operazione annullata.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN non impostato!")
        return

    db.init_db()
    app = Application.builder().token(TOKEN).build()

    # Conversazione nuova persona
    np_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(nuova_persona_start, pattern="^persone_nuova$")],
        states={
            NP_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, np_nome)],
            NP_COGNOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, np_cognome)],
            NP_PRIORITA: [CallbackQueryHandler(np_priorita, pattern="^sel_prio_")],
            NP_TIPI: [CallbackQueryHandler(np_tipi, pattern="^sel_tipo_")],
            NP_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, np_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Conversazione nuova interazione
    ni_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(nuova_inter_start, pattern="^nuova_inter_")],
        states={
            NI_DETTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ni_detto)],
            NI_SO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ni_so)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Conversazione nuova priorità
    nprio_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(crea_priorita_start, pattern="^crea_priorita$")],
        states={
            NPRIO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nprio_nome)],
            NPRIO_COLORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nprio_colore)],
            NPRIO_SOGLIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nprio_soglia)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Conversazione nuovo tipo
    ntipo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(crea_tipo_start, pattern="^crea_tipo$")],
        states={
            NTIPO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ntipo_nome)],
            NTIPO_COLORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ntipo_colore)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(np_conv)
    app.add_handler(ni_conv)
    app.add_handler(nprio_conv)
    app.add_handler(ntipo_conv)
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Avvia Flask in background per keep-alive
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    print("🤖 Bot avviato!")
    print("🌐 Flask keep-alive attivo")
    app.run_polling()

if __name__ == "__main__":
    main()
