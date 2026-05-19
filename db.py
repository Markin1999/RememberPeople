import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date

# Legge da variabile d'ambiente (Render) o usa il valore di default (locale)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_BO9FIlqeC1Td@ep-silent-river-abdaxr9t-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS priorita (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            colore VARCHAR(7) NOT NULL DEFAULT '#FF0000',
            soglia_giorni INTEGER NOT NULL DEFAULT 30
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipi (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            colore VARCHAR(7) NOT NULL DEFAULT '#0000FF'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS persone (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            cognome VARCHAR(100),
            note_generali TEXT,
            priorita_id INTEGER REFERENCES priorita(id) ON DELETE SET NULL,
            data_creazione DATE NOT NULL DEFAULT CURRENT_DATE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS persone_tipi (
            persona_id INTEGER REFERENCES persone(id) ON DELETE CASCADE,
            tipo_id INTEGER REFERENCES tipi(id) ON DELETE CASCADE,
            PRIMARY KEY (persona_id, tipo_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS interazioni (
            id SERIAL PRIMARY KEY,
            persona_id INTEGER REFERENCES persone(id) ON DELETE CASCADE,
            data DATE NOT NULL DEFAULT CURRENT_DATE,
            cosa_ha_detto TEXT,
            cosa_so TEXT,
            data_creazione TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS promemoria (
            id SERIAL PRIMARY KEY,
            persona_id INTEGER REFERENCES persone(id) ON DELETE CASCADE,
            priorita_id INTEGER REFERENCES priorita(id) ON DELETE SET NULL,
            messaggio TEXT NOT NULL,
            data_scadenza DATE,
            completato BOOLEAN DEFAULT FALSE,
            data_creazione TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ─── PRIORITA ───────────────────────────────────────────────────────────────

def get_all_priorita():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM priorita ORDER BY nome")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def create_priorita(nome, colore, soglia_giorni):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO priorita (nome, colore, soglia_giorni) VALUES (%s, %s, %s) RETURNING *",
        (nome, colore, soglia_giorni)
    )
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row

def update_priorita(id, nome, colore, soglia_giorni):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE priorita SET nome=%s, colore=%s, soglia_giorni=%s WHERE id=%s",
        (nome, colore, soglia_giorni, id)
    )
    conn.commit(); cur.close(); conn.close()

def delete_priorita(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM priorita WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

# ─── TIPI ────────────────────────────────────────────────────────────────────

def get_all_tipi():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tipi ORDER BY nome")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def create_tipo(nome, colore):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO tipi (nome, colore) VALUES (%s, %s) RETURNING *",
        (nome, colore)
    )
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row

def update_tipo(id, nome, colore):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tipi SET nome=%s, colore=%s WHERE id=%s", (nome, colore, id))
    conn.commit(); cur.close(); conn.close()

def delete_tipo(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tipi WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

# ─── PERSONE ─────────────────────────────────────────────────────────────────

def get_all_persone(search="", tipo_id=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        SELECT DISTINCT p.*, pr.nome as priorita_nome, pr.colore as priorita_colore,
               MAX(i.data) as ultima_interazione
        FROM persone p
        LEFT JOIN priorita pr ON p.priorita_id = pr.id
        LEFT JOIN persone_tipi pt ON p.id = pt.persona_id
        LEFT JOIN tipi t ON pt.tipo_id = t.id
        LEFT JOIN interazioni i ON p.id = i.persona_id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (LOWER(p.nome) LIKE %s OR LOWER(p.cognome) LIKE %s)"
        params += [f"%{search.lower()}%", f"%{search.lower()}%"]
    if tipo_id:
        query += " AND pt.tipo_id = %s"
        params.append(tipo_id)
    query += " GROUP BY p.id, pr.nome, pr.colore ORDER BY p.nome"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_persona(id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.*, pr.nome as priorita_nome, pr.colore as priorita_colore
        FROM persone p
        LEFT JOIN priorita pr ON p.priorita_id = pr.id
        WHERE p.id = %s
    """, (id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def create_persona(nome, cognome, note_generali, priorita_id, tipo_ids):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO persone (nome, cognome, note_generali, priorita_id) VALUES (%s, %s, %s, %s) RETURNING *",
        (nome, cognome or None, note_generali or None, priorita_id or None)
    )
    persona = cur.fetchone()
    for tid in tipo_ids:
        cur.execute("INSERT INTO persone_tipi (persona_id, tipo_id) VALUES (%s, %s)", (persona['id'], tid))
    conn.commit(); cur.close(); conn.close()
    return persona

def update_persona(id, nome, cognome, note_generali, priorita_id, tipo_ids):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE persone SET nome=%s, cognome=%s, note_generali=%s, priorita_id=%s WHERE id=%s",
        (nome, cognome or None, note_generali or None, priorita_id or None, id)
    )
    cur.execute("DELETE FROM persone_tipi WHERE persona_id=%s", (id,))
    for tid in tipo_ids:
        cur.execute("INSERT INTO persone_tipi (persona_id, tipo_id) VALUES (%s, %s)", (id, tid))
    conn.commit(); cur.close(); conn.close()

def delete_persona(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM persone WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

def get_tipi_persona(persona_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.* FROM tipi t
        JOIN persone_tipi pt ON t.id = pt.tipo_id
        WHERE pt.persona_id = %s
    """, (persona_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ─── INTERAZIONI ─────────────────────────────────────────────────────────────

def get_interazioni(persona_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM interazioni WHERE persona_id=%s ORDER BY data DESC, data_creazione DESC
    """, (persona_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def create_interazione(persona_id, data, cosa_ha_detto, cosa_so):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO interazioni (persona_id, data, cosa_ha_detto, cosa_so) VALUES (%s, %s, %s, %s) RETURNING *",
        (persona_id, data, cosa_ha_detto or None, cosa_so or None)
    )
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row

def update_interazione(id, data, cosa_ha_detto, cosa_so):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE interazioni SET data=%s, cosa_ha_detto=%s, cosa_so=%s WHERE id=%s",
        (data, cosa_ha_detto or None, cosa_so or None, id)
    )
    conn.commit(); cur.close(); conn.close()

def delete_interazione(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM interazioni WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

# ─── PROMEMORIA ──────────────────────────────────────────────────────────────

def get_promemoria_attivi():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT pm.*, p.nome as persona_nome, p.cognome as persona_cognome,
               pr.nome as priorita_nome, pr.colore as priorita_colore
        FROM promemoria pm
        LEFT JOIN persone p ON pm.persona_id = p.id
        LEFT JOIN priorita pr ON pm.priorita_id = pr.id
        WHERE pm.completato = FALSE
        ORDER BY pm.data_scadenza ASC NULLS LAST
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_promemoria_automatici():
    """Persone con priorità che non vengono contattate da troppo tempo."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.id, p.nome, p.cognome,
               pr.nome as priorita_nome, pr.colore as priorita_colore, pr.soglia_giorni,
               MAX(i.data) as ultima_interazione,
               COALESCE(CURRENT_DATE - MAX(i.data), CURRENT_DATE - p.data_creazione) as giorni_silenzio
        FROM persone p
        JOIN priorita pr ON p.priorita_id = pr.id
        LEFT JOIN interazioni i ON p.id = i.persona_id
        GROUP BY p.id, p.nome, p.cognome, pr.nome, pr.colore, pr.soglia_giorni, p.data_creazione
        HAVING COALESCE(CURRENT_DATE - MAX(i.data), CURRENT_DATE - p.data_creazione) >= pr.soglia_giorni
        ORDER BY giorni_silenzio DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_promemoria_persona(persona_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT pm.*, pr.nome as priorita_nome, pr.colore as priorita_colore
        FROM promemoria pm
        LEFT JOIN priorita pr ON pm.priorita_id = pr.id
        WHERE pm.persona_id = %s
        ORDER BY pm.completato ASC, pm.data_scadenza ASC NULLS LAST
    """, (persona_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def create_promemoria(persona_id, priorita_id, messaggio, data_scadenza):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO promemoria (persona_id, priorita_id, messaggio, data_scadenza) VALUES (%s, %s, %s, %s) RETURNING *",
        (persona_id, priorita_id or None, messaggio, data_scadenza or None)
    )
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row

def complete_promemoria(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE promemoria SET completato=TRUE WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

def delete_promemoria(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM promemoria WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()

# ─── STATISTICHE ─────────────────────────────────────────────────────────────

def stats_persone_per_tipo():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.nome, t.colore, COUNT(pt.persona_id) as totale
        FROM tipi t
        LEFT JOIN persone_tipi pt ON t.id = pt.tipo_id
        GROUP BY t.id, t.nome, t.colore
        ORDER BY totale DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def stats_interazioni_per_mese():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT TO_CHAR(data, 'YYYY-MM') as mese, COUNT(*) as totale
        FROM interazioni
        WHERE data >= CURRENT_DATE - INTERVAL '12 months'
        GROUP BY mese ORDER BY mese
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def stats_top_persone():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.nome, p.cognome, COUNT(i.id) as totale_interazioni
        FROM persone p
        LEFT JOIN interazioni i ON p.id = i.persona_id
        GROUP BY p.id, p.nome, p.cognome
        ORDER BY totale_interazioni DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def stats_persone_per_priorita():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT pr.nome, pr.colore, COUNT(p.id) as totale
        FROM priorita pr
        LEFT JOIN persone p ON p.priorita_id = pr.id
        GROUP BY pr.id, pr.nome, pr.colore
        ORDER BY totale DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows
