import os
import sys
import threading
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
import db

# ─── Flask keep-alive ────────────────────────────────────────────────────────
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

# ─── Config ──────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
MY_CHAT_ID = 395777047

PRIORITA = [
    {"id": "alta",  "nome": "Alta",  "emoji": "🔴"},
    {"id": "media", "nome": "Media", "emoji": "🟡"},
    {"id": "bassa", "nome": "Bassa", "emoji": "🟢"},
]

def prio_label(prio_id):
    p = next((x for x in PRIORITA if x['id'] == prio_id), None)
    return f"{p['emoji']} {p['nome']}" if p else ""

# ─── Stati ───────────────────────────────────────────────────────────────────
(
    NP_NOME, NP_COGNOME, NP_TIPO, NP_NOTE,          # nuova persona
    MOD_CAMPO, MOD_VALORE, MOD_TIPO,                 # modifica persona
    NI_DETTO, NI_SO,                                 # nuova interazione
    NPM_MESSAGGIO, NPM_DATA, NPM_ORA, NPM_PRIORITA,  # nuovo promemoria
    NTIPO_NOME, NTIPO_COLORE,                        # nuovo tipo
) = range(15)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def fmt_persona(p, tipi=None):
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    lines = [f"👤 *{nome}*"]
    if tipi:
        lines.append("🏷️ " + " · ".join(f"[{t['nome']}]" for t in tipi))
    if p.get('ultima_interazione'):
        lines.append(f"📅 Ultima: {p['ultima_interazione']}")
    else:
        lines.append("📅 Nessuna interazione ancora")
    if p.get('note_generali'):
        lines.append(f"📝 _{p['note_generali']}_")
    return "\n".join(lines)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Persone", callback_data="menu_persone"),
         InlineKeyboardButton("🔔 Promemoria", callback_data="menu_promemoria")],
        [InlineKeyboardButton("📊 Statistiche", callback_data="menu_stats"),
         InlineKeyboardButton("🏷️ Tipi", callback_data="imp_tipi")],
    ])

def back_kb(to="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Indietro", callback_data=f"back_{to}")]])

# ─── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👥 *RememberPeople*\nCosa vuoi fare?",
        parse_mode="Markdown", reply_markup=main_keyboard()
    )

# ─── Menu callback ────────────────────────────────────────────────────────────

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "menu_persone":        await show_menu_persone(q)
    elif d == "persone_lista":     await show_persone_lista(q, ctx)
    elif d == "persone_cerca_nome":
        await q.edit_message_text("🔍 Scrivi il *nome* da cercare:", parse_mode="Markdown")
        ctx.user_data['action'] = 'cerca_nome'
    elif d == "persone_cerca_tipo": await show_filtra_tipo(q)
    elif d.startswith("filtra_tipo_"):
        await show_persone_per_tipo(q, int(d.split("_")[2]))
    elif d.startswith("persona_") and len(d.split("_")) == 2:
        await show_persona(q, ctx, int(d.split("_")[1]))
    elif d.startswith("p_inter_"):  await show_interazioni(q, int(d.split("_")[2]))
    elif d.startswith("p_prom_"):   await show_prom_persona(q, int(d.split("_")[2]))
    elif d.startswith("prom_done_"):
        db.complete_promemoria(int(d.split("_")[2]))
        await show_promemoria_attivi(q)
    elif d == "menu_promemoria":   await show_menu_promemoria(q)
    elif d == "promemoria_lista":  await show_promemoria_attivi(q)
    elif d == "promemoria_auto":   await show_promemoria_auto(q)
    elif d == "menu_stats":        await show_stats(q)
    elif d == "imp_tipi":          await show_tipi(q)
    elif d == "back_menu":
        await q.edit_message_text("👥 *RememberPeople*\nCosa vuoi fare?",
                                   parse_mode="Markdown", reply_markup=main_keyboard())
    elif d == "back_persone":      await show_menu_persone(q)
    elif d == "back_lista":        await show_persone_lista(q, ctx)
    elif d == "back_promemoria":   await show_menu_promemoria(q)

# ─── Persone ─────────────────────────────────────────────────────────────────

async def show_menu_persone(q):
    await q.edit_message_text("👥 *Persone*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Tutte", callback_data="persone_lista")],
        [InlineKeyboardButton("🔍 Cerca per nome", callback_data="persone_cerca_nome"),
         InlineKeyboardButton("🏷️ Filtra per tipo", callback_data="persone_cerca_tipo")],
        [InlineKeyboardButton("➕ Nuova persona", callback_data="persone_nuova")],
        [InlineKeyboardButton("← Menu", callback_data="back_menu")],
    ]))

async def show_persone_lista(q, ctx, search="", tipo_id=None):
    persone = db.get_all_persone(search=search, tipo_id=tipo_id)
    if not persone:
        await q.edit_message_text(
            "Nessuna persona trovata." if search else "Nessuna persona ancora.",
            reply_markup=back_kb("persone"))
        return
    buttons = []
    for p in persone[:20]:
        nome = f"{p['nome']} {p['cognome'] or ''}".strip()
        tipi = db.get_tipi_persona(p['id'])
        t_label = f" [{', '.join(t['nome'] for t in tipi)}]" if tipi else " [?]"
        buttons.append([InlineKeyboardButton(f"{nome}{t_label}", callback_data=f"persona_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_persone")])
    header = f"👥 *{len(persone)} persone*" + (f" — '{search}'" if search else "")
    await q.edit_message_text(header, parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

async def show_filtra_tipo(q):
    tipi = db.get_all_tipi()
    if not tipi:
        await q.edit_message_text("Nessun tipo creato ancora.", reply_markup=back_kb("persone"))
        return
    buttons = [[InlineKeyboardButton(f"🏷️ {t['nome']}", callback_data=f"filtra_tipo_{t['id']}")] for t in tipi]
    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_persone")])
    await q.edit_message_text("🏷️ *Filtra per tipo:*", parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

async def show_persone_per_tipo(q, tipo_id):
    tipi = db.get_all_tipi()
    tipo = next((t for t in tipi if t['id'] == tipo_id), None)
    persone = db.get_all_persone(tipo_id=tipo_id)
    tipo_nome = tipo['nome'] if tipo else "Tipo"
    if not persone:
        await q.edit_message_text(f"🏷️ *{tipo_nome}*\nNessuna persona.",
                                   parse_mode="Markdown", reply_markup=back_kb("persone_cerca_tipo"))
        return
    buttons = []
    for p in persone[:20]:
        nome = f"{p['nome']} {p['cognome'] or ''}".strip()
        buttons.append([InlineKeyboardButton(nome, callback_data=f"persona_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Tipi", callback_data="persone_cerca_tipo")])
    await q.edit_message_text(f"🏷️ *{tipo_nome}* — {len(persone)} persone",
                               parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_persona(q, ctx, persona_id):
    p = db.get_persona(persona_id)
    if not p:
        await q.edit_message_text("Persona non trovata.")
        return
    tipi = db.get_tipi_persona(persona_id)
    testo = fmt_persona(p, tipi)
    ctx.user_data['current_persona'] = persona_id
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Interazioni", callback_data=f"p_inter_{persona_id}"),
         InlineKeyboardButton("🔔 Promemoria", callback_data=f"p_prom_{persona_id}")],
        [InlineKeyboardButton("➕ Interazione", callback_data=f"nuova_inter_{persona_id}"),
         InlineKeyboardButton("➕ Promemoria", callback_data=f"nuova_prom_{persona_id}")],
        [InlineKeyboardButton("✏️ Modifica", callback_data=f"modifica_{persona_id}")],
        [InlineKeyboardButton("← Lista", callback_data="persone_lista")],
    ]))

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
                lines.append(f"› {i['cosa_ha_detto'][:120]}")
            if i['cosa_so']:
                lines.append(f"› _{i['cosa_so'][:100]}_")
            lines.append("")
        testo = "\n".join(lines)
    await q.edit_message_text(testo, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Persona", callback_data=f"persona_{persona_id}")]]))

async def show_prom_persona(q, persona_id):
    promemoria = db.get_promemoria_persona(persona_id)
    p = db.get_persona(persona_id)
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    buttons = []
    if not promemoria:
        testo = f"*{nome}* — nessun promemoria."
    else:
        lines = [f"🔔 *Promemoria — {nome}*\n"]
        for pm in promemoria:
            stato = "✓" if pm['completato'] else "●"
            scad = f" ({pm['data_scadenza']})" if pm['data_scadenza'] else ""
            lines.append(f"{stato} {pm['messaggio']}{scad}")
            if not pm['completato']:
                buttons.append([InlineKeyboardButton(
                    f"✓ {pm['messaggio'][:35]}", callback_data=f"prom_done_{pm['id']}")])
        testo = "\n".join(lines)
    buttons.append([InlineKeyboardButton("← Persona", callback_data=f"persona_{persona_id}")])
    await q.edit_message_text(testo, parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

# ─── Promemoria globali ───────────────────────────────────────────────────────

async def show_menu_promemoria(q):
    await q.edit_message_text("🔔 *Promemoria*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Promemoria attivi", callback_data="promemoria_lista")],
        [InlineKeyboardButton("⚡ Avvisi automatici", callback_data="promemoria_auto")],
        [InlineKeyboardButton("← Menu", callback_data="back_menu")],
    ]))

async def show_promemoria_attivi(q):
    promemoria = db.get_promemoria_attivi()
    if not promemoria:
        await q.edit_message_text("✅ Nessun promemoria attivo!", reply_markup=back_kb("promemoria"))
        return
    lines = ["🔔 *Promemoria attivi*\n"]
    buttons = []
    for pm in promemoria:
        nome = f"{pm['persona_nome']} {pm['persona_cognome'] or ''}".strip()
        scad = f" — {pm['data_scadenza']}" if pm['data_scadenza'] else ""
        lines.append(f"● *{nome}*\n  {pm['messaggio']}{scad}")
        buttons.append([InlineKeyboardButton(f"✓ {pm['messaggio'][:35]}", callback_data=f"prom_done_{pm['id']}")])
    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_promemoria")])
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

async def show_promemoria_auto(q):
    auto = db.get_promemoria_automatici()
    if not auto:
        await q.edit_message_text("✅ Tutti i contatti sono aggiornati!", reply_markup=back_kb("promemoria"))
        return
    lines = ["⚡ *Avvisi automatici*\n"]
    buttons = []
    for item in auto:
        nome = f"{item['nome']} {item['cognome'] or ''}".strip()
        lines.append(f"● *{nome}* — {item['giorni_silenzio']} giorni di silenzio")
        buttons.append([InlineKeyboardButton(f"→ {nome}", callback_data=f"persona_{item['id']}")])
    buttons.append([InlineKeyboardButton("← Indietro", callback_data="menu_promemoria")])
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(buttons))

# ─── Statistiche ─────────────────────────────────────────────────────────────

async def show_stats(q):
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM persone"); n_p = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM interazioni"); n_i = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM promemoria WHERE completato=FALSE"); n_pm = cur.fetchone()[0]
        cur.close(); conn.close()
        top = db.stats_top_persone()
        tipi_s = db.stats_persone_per_tipo()
        rischio = db.get_promemoria_automatici()
        lines = ["📊 *Statistiche*\n",
                 f"👤 Persone: *{n_p}*",
                 f"💬 Interazioni: *{n_i}*",
                 f"🔔 Promemoria attivi: *{n_pm}*"]
        if tipi_s:
            lines.append("\n🏷️ *Per tipo:*")
            for r in tipi_s:
                if r['totale'] > 0:
                    lines.append(f"  · {r['nome']}: {r['totale']}")
        if top:
            lines.append("\n🏆 *Top contatti:*")
            for i, r in enumerate(top[:3]):
                nome = f"{r['nome']} {r['cognome'] or ''}".strip()
                lines.append(f"  {i+1}. {nome} — {r['totale_interazioni']} interazioni")
        if rischio:
            lines.append(f"\n⚠️ *A rischio silenzio: {len(rischio)}*")
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_kb("menu"))
    except Exception as e:
        await q.edit_message_text(f"Errore: {e}", reply_markup=back_kb("menu"))

# ─── Tipi ────────────────────────────────────────────────────────────────────

async def show_tipi(q):
    tipi = db.get_all_tipi()
    testo = "🏷️ *Tipi esistenti:*\n\n" + "\n".join(f"· *{t['nome']}*" for t in tipi) if tipi else "🏷️ *Tipi*\nNessun tipo ancora."
    await q.edit_message_text(testo, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Crea nuovo tipo", callback_data="crea_tipo")],
        [InlineKeyboardButton("← Menu", callback_data="back_menu")],
    ]))

# ─── Conv: Nuova Persona ─────────────────────────────────────────────────────

async def nuova_persona_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not db.get_all_tipi():
        await q.edit_message_text(
            "⚠️ Devi prima creare almeno un tipo!\nVai in 🏷️ Tipi → Crea nuovo tipo.",
            reply_markup=back_kb("persone"))
        return ConversationHandler.END
    ctx.user_data['np'] = {}
    await q.edit_message_text("➕ *Nuova persona*\n\nNome:", parse_mode="Markdown")
    return NP_NOME

async def np_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['np']['nome'] = update.message.text.strip()
    await update.message.reply_text("Cognome (o /salta):")
    return NP_COGNOME

async def np_cognome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    ctx.user_data['np']['cognome'] = "" if t == "/salta" else t
    ctx.user_data['np']['tipo_ids'] = []
    return await _chiedi_tipo(update.message, ctx)

async def _chiedi_tipo(msg, ctx):
    tipi = db.get_all_tipi()
    ids = ctx.user_data['np']['tipo_ids']
    buttons = []
    for t in tipi:
        mark = "✅ " if t['id'] in ids else ""
        buttons.append([InlineKeyboardButton(f"{mark}{t['nome']}", callback_data=f"sel_tipo_{t['id']}")])
    n = len(ids)
    label = f"✅ Conferma ({n} selezionati)" if n > 0 else "✅ Conferma selezione"
    buttons.append([InlineKeyboardButton(label, callback_data="sel_tipo_done")])
    await msg.reply_text(
        "🏷️ Scegli uno o più *tipi* (obbligatorio):",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    return NP_TIPO

async def np_tipo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "sel_tipo_done":
        if not ctx.user_data['np'].get('tipo_ids'):
            await q.answer("⚠️ Seleziona almeno un tipo!", show_alert=True)
            return NP_TIPO
        await q.edit_message_text("📝 Note su questa persona (o /salta):")
        return NP_NOTE
    tipo_id = int(q.data.split("_")[2])
    ids = ctx.user_data['np']['tipo_ids']
    if tipo_id in ids: ids.remove(tipo_id)
    else: ids.append(tipo_id)
    tipi = db.get_all_tipi()
    buttons = []
    for t in tipi:
        mark = "✅ " if t['id'] in ids else ""
        buttons.append([InlineKeyboardButton(f"{mark}{t['nome']}", callback_data=f"sel_tipo_{t['id']}")])
    n = len(ids)
    buttons.append([InlineKeyboardButton(f"✅ Conferma ({n} selezionati)" if n else "✅ Conferma", callback_data="sel_tipo_done")])
    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    return NP_TIPO

async def np_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    ctx.user_data['np']['note'] = "" if t == "/salta" else t
    d = ctx.user_data['np']
    db.create_persona(d['nome'], d.get('cognome',''), d.get('note',''), None, d.get('tipo_ids',[]))
    tipi_tutti = db.get_all_tipi()
    tipi_nomi = [t['nome'] for t in tipi_tutti if t['id'] in d.get('tipo_ids',[])]
    msg = f"✅ *{d['nome']} {d.get('cognome','')}* salvato!".strip()
    if tipi_nomi: msg += f"\n🏷️ {', '.join(tipi_nomi)}"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Conv: Modifica Persona ───────────────────────────────────────────────────

async def modifica_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    persona_id = int(q.data.split("_")[1])
    p = db.get_persona(persona_id)
    tipi = db.get_tipi_persona(persona_id)
    ctx.user_data['mod'] = {
        'persona_id': persona_id,
        'nome': p['nome'],
        'cognome': p['cognome'] or '',
        'note': p['note_generali'] or '',
        'tipo_ids': [t['id'] for t in tipi],
    }
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    tipi_label = ", ".join(t['nome'] for t in tipi) if tipi else "nessuno"
    await q.edit_message_text(
        f"✏️ *Modifica — {nome}*\n\nCosa vuoi cambiare?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Nome: {p['nome']}", callback_data="mod_campo_nome")],
            [InlineKeyboardButton(f"Cognome: {p['cognome'] or '—'}", callback_data="mod_campo_cognome")],
            [InlineKeyboardButton(f"🏷️ Tipi: {tipi_label}", callback_data="mod_campo_tipi")],
            [InlineKeyboardButton(f"📝 Note", callback_data="mod_campo_note")],
            [InlineKeyboardButton("💾 Salva e chiudi", callback_data="mod_salva")],
            [InlineKeyboardButton("← Annulla", callback_data=f"persona_{persona_id}")],
        ])
    )
    return MOD_CAMPO

async def mod_campo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    pid = ctx.user_data['mod']['persona_id']

    if d == "mod_campo_nome":
        await q.edit_message_text("Nuovo nome:")
        ctx.user_data['mod']['editing'] = 'nome'
        return MOD_VALORE
    elif d == "mod_campo_cognome":
        await q.edit_message_text("Nuovo cognome (o /salta per rimuovere):")
        ctx.user_data['mod']['editing'] = 'cognome'
        return MOD_VALORE
    elif d == "mod_campo_note":
        await q.edit_message_text("Nuove note (o /salta per rimuovere):")
        ctx.user_data['mod']['editing'] = 'note'
        return MOD_VALORE
    elif d == "mod_campo_tipi":
        ids = ctx.user_data['mod']['tipo_ids']
        tipi = db.get_all_tipi()
        buttons = []
        for t in tipi:
            mark = "✅ " if t['id'] in ids else ""
            buttons.append([InlineKeyboardButton(f"{mark}{t['nome']}", callback_data=f"mod_tipo_{t['id']}")])
        buttons.append([InlineKeyboardButton("💾 Conferma tipi", callback_data="mod_tipo_done")])
        await q.edit_message_text("🏷️ Seleziona i tipi (almeno uno):",
                                   reply_markup=InlineKeyboardMarkup(buttons))
        return MOD_TIPO
    elif d == "mod_salva":
        m = ctx.user_data['mod']
        if not m.get('tipo_ids'):
            await q.answer("⚠️ Serve almeno un tipo!", show_alert=True)
            return MOD_CAMPO
        db.update_persona(m['persona_id'], m['nome'], m['cognome'], m['note'], None, m['tipo_ids'])
        await q.edit_message_text("✅ Persona aggiornata!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("← Torna alla persona", callback_data=f"persona_{pid}")]
        ]))
        return ConversationHandler.END

async def mod_valore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    campo = ctx.user_data['mod']['editing']
    pid = ctx.user_data['mod']['persona_id']
    if campo == 'nome':
        if not t: await update.message.reply_text("Il nome non può essere vuoto."); return MOD_VALORE
        ctx.user_data['mod']['nome'] = t
    elif campo == 'cognome':
        ctx.user_data['mod']['cognome'] = "" if t == "/salta" else t
    elif campo == 'note':
        ctx.user_data['mod']['note'] = "" if t == "/salta" else t

    m = ctx.user_data['mod']
    tipi = db.get_all_tipi()
    tipi_label = ", ".join(tt['nome'] for tt in tipi if tt['id'] in m['tipo_ids']) or "nessuno"
    await update.message.reply_text(
        f"✏️ *Modifica* — cosa vuoi cambiare ancora?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Nome: {m['nome']}", callback_data="mod_campo_nome")],
            [InlineKeyboardButton(f"Cognome: {m['cognome'] or '—'}", callback_data="mod_campo_cognome")],
            [InlineKeyboardButton(f"🏷️ Tipi: {tipi_label}", callback_data="mod_campo_tipi")],
            [InlineKeyboardButton(f"📝 Note", callback_data="mod_campo_note")],
            [InlineKeyboardButton("💾 Salva e chiudi", callback_data="mod_salva")],
            [InlineKeyboardButton("← Annulla", callback_data=f"persona_{pid}")],
        ])
    )
    return MOD_CAMPO

async def mod_tipo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    pid = ctx.user_data['mod']['persona_id']

    if d == "mod_tipo_done":
        if not ctx.user_data['mod']['tipo_ids']:
            await q.answer("⚠️ Seleziona almeno un tipo!", show_alert=True)
            return MOD_TIPO
        m = ctx.user_data['mod']
        tipi = db.get_all_tipi()
        tipi_label = ", ".join(tt['nome'] for tt in tipi if tt['id'] in m['tipo_ids']) or "nessuno"
        await q.edit_message_text(
            "✏️ *Modifica* — cosa vuoi cambiare ancora?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Nome: {m['nome']}", callback_data="mod_campo_nome")],
                [InlineKeyboardButton(f"Cognome: {m['cognome'] or '—'}", callback_data="mod_campo_cognome")],
                [InlineKeyboardButton(f"🏷️ Tipi: {tipi_label}", callback_data="mod_campo_tipi")],
                [InlineKeyboardButton(f"📝 Note", callback_data="mod_campo_note")],
                [InlineKeyboardButton("💾 Salva e chiudi", callback_data="mod_salva")],
                [InlineKeyboardButton("← Annulla", callback_data=f"persona_{pid}")],
            ])
        )
        return MOD_CAMPO

    tipo_id = int(d.split("_")[2])
    ids = ctx.user_data['mod']['tipo_ids']
    if tipo_id in ids: ids.remove(tipo_id)
    else: ids.append(tipo_id)
    tipi = db.get_all_tipi()
    buttons = []
    for t in tipi:
        mark = "✅ " if t['id'] in ids else ""
        buttons.append([InlineKeyboardButton(f"{mark}{t['nome']}", callback_data=f"mod_tipo_{t['id']}")])
    n = len(ids)
    buttons.append([InlineKeyboardButton(f"💾 Conferma ({n} selezionati)" if n else "💾 Conferma", callback_data="mod_tipo_done")])
    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    return MOD_TIPO

# ─── Conv: Nuova Interazione ─────────────────────────────────────────────────

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
    t = update.message.text.strip()
    ctx.user_data['ni']['detto'] = "" if t == "/salta" else t
    await update.message.reply_text("Cosa sai di lui/lei? (o /salta)")
    return NI_SO

async def ni_so(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    ctx.user_data['ni']['so'] = "" if t == "/salta" else t
    d = ctx.user_data['ni']
    db.create_interazione(d['persona_id'], date.today(), d.get('detto',''), d.get('so',''))
    await update.message.reply_text("✅ Interazione salvata!", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Conv: Nuovo Promemoria ───────────────────────────────────────────────────

async def nuova_prom_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    persona_id = int(q.data.split("_")[2])
    ctx.user_data['npm'] = {'persona_id': persona_id}
    p = db.get_persona(persona_id)
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    await q.edit_message_text(f"🔔 Nuovo promemoria per *{nome}*\n\nMessaggio:", parse_mode="Markdown")
    return NPM_MESSAGGIO

async def npm_messaggio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['npm']['messaggio'] = update.message.text.strip()
    await update.message.reply_text("📅 Data:\nFormato *GG/MM/AAAA* (es. 25/06/2026)", parse_mode="Markdown")
    return NPM_DATA

async def npm_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        datetime.strptime(t, "%d/%m/%Y")
        ctx.user_data['npm']['data'] = t
    except ValueError:
        await update.message.reply_text("❌ Formato non valido. Usa GG/MM/AAAA:")
        return NPM_DATA
    await update.message.reply_text("⏰ Orario:\nFormato *HH:MM* (es. 18:30)", parse_mode="Markdown")
    return NPM_ORA

async def npm_ora(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
        ctx.user_data['npm']['ora'] = t
    except ValueError:
        await update.message.reply_text("❌ Formato non valido. Usa HH:MM:")
        return NPM_ORA
    await update.message.reply_text("⭐ Priorità:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{p['emoji']} {p['nome']}", callback_data=f"npm_prio_{p['id']}")] for p in PRIORITA
    ]))
    return NPM_PRIORITA

async def npm_priorita_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    prio_id = q.data.split("_")[2]
    d = ctx.user_data['npm']
    dt = datetime.strptime(f"{d['data']} {d['ora']}", "%d/%m/%Y %H:%M")
    db.create_promemoria(d['persona_id'], None, d['messaggio'], dt.date())
    if 'scheduled' not in ctx.application.bot_data:
        ctx.application.bot_data['scheduled'] = []
    ctx.application.bot_data['scheduled'].append({
        'dt': dt, 'messaggio': d['messaggio'],
        'persona_id': d['persona_id'], 'priorita': prio_id,
    })
    p = db.get_persona(d['persona_id'])
    nome = f"{p['nome']} {p['cognome'] or ''}".strip()
    await q.edit_message_text(
        f"✅ *Promemoria salvato!*\n\n"
        f"👤 {nome}\n📅 {d['data']} alle {d['ora']}\n"
        f"⭐ {prio_label(prio_id)}\n📝 {d['messaggio']}\n\n"
        f"Riceverai la notifica all'orario impostato.",
        parse_mode="Markdown", reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# ─── Conv: Nuovo Tipo ────────────────────────────────────────────────────────

async def crea_tipo_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data['ntipo'] = {}
    await q.edit_message_text("🏷️ *Nuovo tipo*\n\nNome (es. Lavoro, Calcio, Amici):", parse_mode="Markdown")
    return NTIPO_NOME

async def ntipo_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['ntipo']['nome'] = update.message.text.strip()
    await update.message.reply_text("Colore HEX (es. #3498DB) o /salta per default:")
    return NTIPO_COLORE

async def ntipo_colore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    colore = "#5B5BFF" if t == "/salta" else t
    if t != "/salta" and (not colore.startswith('#') or len(colore) != 7):
        await update.message.reply_text("Formato non valido. Usa #RRGGBB o /salta:")
        return NTIPO_COLORE
    d = ctx.user_data['ntipo']
    db.create_tipo(d['nome'], colore)
    await update.message.reply_text(
        f"✅ Tipo *{d['nome']}* creato!\nOra puoi assegnarlo alle persone.",
        parse_mode="Markdown", reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# ─── Scheduler notifiche ─────────────────────────────────────────────────────

async def check_promemoria(context: ContextTypes.DEFAULT_TYPE):
    scheduled = context.bot_data.get('scheduled', [])
    now = datetime.now().replace(second=0, microsecond=0)
    da_inviare = [s for s in scheduled if s['dt'].replace(second=0, microsecond=0) == now]
    for pm in da_inviare:
        p = db.get_persona(pm['persona_id'])
        nome = f"{p['nome']} {p['cognome'] or ''}".strip() if p else "?"
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=(f"🔔 *PROMEMORIA* {prio_label(pm['priorita'])}\n\n"
                  f"👤 {nome}\n📝 {pm['messaggio']}\n"
                  f"⏰ {pm['dt'].strftime('%d/%m/%Y alle %H:%M')}"),
            parse_mode="Markdown"
        )
        scheduled.remove(pm)
    context.bot_data['scheduled'] = scheduled

# ─── Testo libero ─────────────────────────────────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    action = ctx.user_data.get('action')
    if action == 'cerca_nome':
        ctx.user_data['action'] = None
        persone = db.get_all_persone(search=update.message.text.strip())
        if not persone:
            await update.message.reply_text("Nessuna persona trovata.", reply_markup=main_keyboard())
            return
        buttons = []
        for p in persone[:15]:
            nome = f"{p['nome']} {p['cognome'] or ''}".strip()
            tipi = db.get_tipi_persona(p['id'])
            t_label = f" [{tipi[0]['nome']}]" if tipi else ""
            buttons.append([InlineKeyboardButton(f"{nome}{t_label}", callback_data=f"persona_{p['id']}")])
        buttons.append([InlineKeyboardButton("← Menu", callback_data="back_menu")])
        await update.message.reply_text(f"🔍 *{len(persone)} risultati:*",
                                         parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("Usa il menu:", reply_markup=main_keyboard())

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Annullato.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN non impostato!")
        return
    db.init_db()
    app = Application.builder().token(TOKEN).build()

    np_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(nuova_persona_start, pattern="^persone_nuova$")],
        states={
            NP_NOME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, np_nome)],
            NP_COGNOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, np_cognome)],
            NP_TIPO:    [CallbackQueryHandler(np_tipo, pattern="^sel_tipo_")],
            NP_NOTE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, np_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    mod_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(modifica_start, pattern="^modifica_\\d+$")],
        states={
            MOD_CAMPO:  [CallbackQueryHandler(mod_campo, pattern="^mod_campo_|^mod_salva$")],
            MOD_VALORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mod_valore)],
            MOD_TIPO:   [CallbackQueryHandler(mod_tipo, pattern="^mod_tipo_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    ni_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(nuova_inter_start, pattern="^nuova_inter_")],
        states={
            NI_DETTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ni_detto)],
            NI_SO:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ni_so)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    npm_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(nuova_prom_start, pattern="^nuova_prom_")],
        states={
            NPM_MESSAGGIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, npm_messaggio)],
            NPM_DATA:      [MessageHandler(filters.TEXT & ~filters.COMMAND, npm_data)],
            NPM_ORA:       [MessageHandler(filters.TEXT & ~filters.COMMAND, npm_ora)],
            NPM_PRIORITA:  [CallbackQueryHandler(npm_priorita_cb, pattern="^npm_prio_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    ntipo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(crea_tipo_start, pattern="^crea_tipo$")],
        states={
            NTIPO_NOME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ntipo_nome)],
            NTIPO_COLORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ntipo_colore)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(np_conv)
    app.add_handler(mod_conv)
    app.add_handler(ni_conv)
    app.add_handler(npm_conv)
    app.add_handler(ntipo_conv)
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.job_queue.run_repeating(check_promemoria, interval=60, first=10)

    threading.Thread(target=run_flask, daemon=True).start()
    print("🤖 Bot avviato!")
    app.run_polling()

if __name__ == "__main__":
    main()
