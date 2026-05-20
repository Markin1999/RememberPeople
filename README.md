# 👥 RememberPeople

> Un sistema personale per ricordare le persone che conosci, cosa ti hanno detto, come le conosci e quando ricontattarle — accessibile sia da desktop (app Mac) che da qualsiasi luogo tramite Telegram.

---

## 🎯 Obiettivo

RememberPeople nasce come CRM personale: uno strumento privato per tenere traccia di persone, relazioni e interazioni nel tempo. Non è pensato per team o aziende, ma per uso individuale — per non dimenticare mai chi hai incontrato, cosa ti ha detto e quando è il momento di risentirlo.

---

## 🏗️ Architettura generale

```
┌─────────────────────────┐         ┌──────────────────────────────────┐
│   App Desktop (Mac)     │         │                                  │
│   PyQt6 — main.py       │────────►│   PostgreSQL su Neon (cloud)     │
│   Interfaccia grafica   │         │   Database condiviso             │
└─────────────────────────┘         │                                  │
                                    └──────────────────────────────────┘
┌─────────────────────────┐                        ▲
│   Bot Telegram          │                        │
│   bot.py su Render      │────────────────────────┘
│   Sempre attivo 24/7    │
└─────────────────────────┘
         ▲
         │ ping ogni 5 min
┌─────────────────────────┐
│   UptimeRobot           │
│   Monitor gratuito      │
└─────────────────────────┘
```

**Tutto converge sullo stesso database.** Aggiungi una persona dall'app desktop e la vedi subito su Telegram, e viceversa.

---

## ☁️ Servizi utilizzati (tutti gratuiti)

### 1. Neon.tech — Database PostgreSQL
- **Cosa è:** PostgreSQL hosted sul cloud, gratuito per sempre
- **Perché:** Sostituisce il database locale Docker, rende i dati accessibili sia dall'app desktop che dal bot Telegram
- **URL progetto:** `ep-silent-river-abdaxr9t-pooler.eu-west-2.aws.neon.tech`
- **Database:** `neondb`
- **Regione:** Europe West (eu-west-2)
- **Connessione:** stringa PostgreSQL con SSL obbligatorio (`sslmode=require`)
- **Piano:** Free tier — 500MB storage, nessun limite di tempo

### 2. Render.com — Hosting del Bot Telegram
- **Cosa è:** Piattaforma cloud per deployare applicazioni Python
- **Perché:** Fa girare `bot.py` 24/7 senza bisogno di tenere il Mac acceso
- **Piano:** Free tier (Web Service)
- **Comportamento:** Si "addormenta" dopo 15 minuti di inattività → risolto con UptimeRobot
- **Deploy:** Automatico ad ogni `git push` sul branch `main`
- **Variabili d'ambiente configurate su Render:**
  - `TELEGRAM_TOKEN` — token del bot Telegram
  - `DATABASE_URL` — stringa di connessione Neon
  - `PYTHON_VERSION` — `3.12.0` (forzato perché il default 3.14 è incompatibile)

### 3. UptimeRobot — Monitor anti-sleep
- **Cosa è:** Servizio gratuito che pinga un URL a intervalli regolari
- **Perché:** Render spegne i servizi gratuiti dopo 15 minuti senza richieste. UptimeRobot pinga l'endpoint `/ping` del bot ogni 5 minuti, tenendolo sempre sveglio
- **URL monitorato:** `https://<nome-servizio>.onrender.com/ping`
- **Intervallo:** 5 minuti
- **Piano:** Free tier — fino a 50 monitor

### 4. GitHub — Versionamento e deploy
- **Repository:** privato (`Markin1999/RememberPeople`)
- **Branch principale:** `main`
- **Flusso deploy:** `git push` → Render rileva il push → ribuildo automatico → nuovo deploy

### 5. Telegram BotFather — Token bot
- **Bot username:** configurato via `@BotFather`
- **Token:** salvato come variabile d'ambiente su Render (mai nel codice)
- **Chat ID proprietario:** `395777047` (hardcoded in `bot.py` — usato per inviare notifiche schedulate)

---

## 🗄️ Struttura del Database

Il database PostgreSQL su Neon contiene 6 tabelle:

```sql
persone          -- le persone che conosci
tipi             -- categorie create da te (es. Lavoro, Calcio, Amici)
persone_tipi     -- relazione molti-a-molti: una persona può avere più tipi
interazioni      -- storico di cosa ti ha detto / cosa sai di ogni persona
promemoria       -- avvisi manuali con data, ora e priorità
priorita         -- (tabella legacy, non più usata attivamente nel bot)
```

### Dettaglio tabelle

**`persone`**
| Campo | Tipo | Descrizione |
|---|---|---|
| id | SERIAL PK | Identificativo univoco |
| nome | VARCHAR | Nome (obbligatorio) |
| cognome | VARCHAR | Cognome (opzionale) |
| note_generali | TEXT | Note libere sulla persona |
| priorita_id | FK | Riferimento a priorita (opzionale) |
| data_creazione | DATE | Data inserimento |

**`tipi`**
| Campo | Tipo | Descrizione |
|---|---|---|
| id | SERIAL PK | Identificativo univoco |
| nome | VARCHAR | Nome del tipo (es. "Lavoro") |
| colore | VARCHAR(7) | Colore HEX (es. "#3498DB") |

**`persone_tipi`** — tabella di giunzione
| Campo | Tipo | Descrizione |
|---|---|---|
| persona_id | FK | Riferimento a persone |
| tipo_id | FK | Riferimento a tipi |

**`interazioni`**
| Campo | Tipo | Descrizione |
|---|---|---|
| id | SERIAL PK | Identificativo univoco |
| persona_id | FK | Riferimento a persone |
| data | DATE | Data dell'interazione |
| cosa_ha_detto | TEXT | Cosa ti ha detto |
| cosa_so | TEXT | Cosa sai di lui/lei |
| data_creazione | TIMESTAMP | Timestamp inserimento |

**`promemoria`**
| Campo | Tipo | Descrizione |
|---|---|---|
| id | SERIAL PK | Identificativo univoco |
| persona_id | FK | Riferimento a persone |
| priorita_id | FK | Riferimento a priorita (opzionale) |
| messaggio | TEXT | Testo del promemoria |
| data_scadenza | DATE | Data scadenza |
| completato | BOOLEAN | Se è stato segnato come fatto |
| data_creazione | TIMESTAMP | Timestamp inserimento |

---

## 📁 Struttura dei file

```
RememberPeople/
│
├── main.py                  # Entry point app desktop
├── bot.py                   # Bot Telegram completo
├── db.py                    # Tutte le query al database
│
├── ui/                      # Interfaccia grafica desktop (PyQt6)
│   ├── main_window.py       # Finestra principale, sidebar, banner notifiche
│   ├── persone.py           # Lista persone, scheda persona, interazioni
│   ├── promemoria.py        # Pagina promemoria (manuali + automatici)
│   ├── statistiche.py       # Grafici e statistiche con matplotlib
│   └── impostazioni.py      # Gestione tipi e priorità
│
├── utils/
│   └── colors.py            # Color picker e utilità colori HEX
│
├── requirements.txt         # Dipendenze Python per Render (bot)
├── Procfile                 # Comando avvio per Render: `web: python bot.py`
├── runtime.txt              # Versione Python per Render: 3.12.0
├── build.sh                 # Script per compilare l'app Mac (.app)
└── README.md                # Questo file
```

### Dettaglio file principali

#### `db.py`
Il cuore del sistema. Contiene **tutte le funzioni di accesso al database** — nessun'altra parte del codice scrive SQL direttamente. Si connette a Neon tramite la stringa `DATABASE_URL` letta dalla variabile d'ambiente (su Render) o dal valore di default hardcoded (per uso locale/desktop).

Funzioni principali:
- `init_db()` — crea le tabelle se non esistono
- `get_all_persone(search, tipo_id)` — lista con filtri
- `create_persona / update_persona / delete_persona`
- `get_tipi_persona(persona_id)` — tipi associati a una persona
- `create_interazione / get_interazioni`
- `create_promemoria / complete_promemoria`
- `get_promemoria_automatici()` — persone con priorità che non contatti da troppo tempo
- `stats_*` — funzioni per le statistiche

#### `bot.py`
Il bot Telegram. Gira su Render 24/7. Contiene:
- **Menu interattivo** con bottoni inline per navigare tra persone, promemoria, statistiche e tipi
- **Conversazioni guidate** (ConversationHandler) per creare persone, interazioni, promemoria e tipi
- **Modifica persona** — cambia nome, cognome, tipi (multipli), note
- **Priorità fisse** — 🔴 Alta / 🟡 Media / 🟢 Bassa (non modificabili, hardcoded)
- **Scheduler notifiche** — controlla ogni minuto se ci sono promemoria da inviare e manda un messaggio Telegram all'orario preciso
- **Flask keep-alive** — un mini server HTTP gira in parallelo su un thread separato; risponde a `/` e `/ping` per UptimeRobot

#### `main.py`
Entry point dell'app desktop. Controlla la connessione al database prima di aprire la finestra; se il database non è raggiungibile mostra un errore chiaro.

#### `ui/main_window.py`
La finestra principale dell'app desktop. Gestisce:
- La sidebar con i 4 bottoni di navigazione
- Il banner notifiche in cima (promemoria attivi + avvisi automatici)
- Lo stack di pagine (persone / promemoria / statistiche / impostazioni)
- Il refresh automatico del banner ogni 60 secondi

#### `ui/persone.py`
La pagina più complessa. Gestisce:
- Lista persone con ricerca e filtro per tipo
- Card cliccabili per ogni persona
- Vista dettaglio con storico interazioni e promemoria
- Dialog per creare/modificare persone e interazioni
- Possibilità di creare tipi e priorità al volo durante la creazione

#### `build.sh`
Script bash per compilare l'app desktop in un `.app` Mac tramite PyInstaller. Da eseguire con il virtual environment attivo.

---

## 🔄 Flusso di deploy (bot Telegram)

```
1. Modifica bot.py in locale
2. git add bot.py
3. git commit -m "descrizione"
4. git push
      ↓
5. Render rileva il push automaticamente
6. Rebuild (pip install -r requirements.txt)
7. Nuovo deploy attivo in ~2 minuti
```

---

## 🖥️ Flusso di avvio (app desktop)

```
1. Apri Docker Desktop (non più necessario con Neon — legacy)
2. Doppio click su avvia_rememberpeople.sh
      ↓
3. Lo script attiva il virtual environment ~/mypeople-env
4. Avvia python3.12 main.py
5. main.py chiama db.init_db() → connessione a Neon
6. Si apre la finestra PyQt6
```

---

## 📱 Funzionalità Bot Telegram

| Sezione | Funzione |
|---|---|
| 👥 Persone | Lista, cerca per nome, filtra per tipo |
| ➕ Nuova persona | Nome, cognome, tipo (obbligatorio, multiplo), note |
| ✏️ Modifica persona | Cambia nome, cognome, tipi, note |
| 💬 Interazioni | Storico delle ultime 5 interazioni |
| ➕ Nuova interazione | Cosa ti ha detto + cosa sai |
| 🔔 Promemoria | Lista promemoria attivi con tasto "Fatto" |
| ➕ Nuovo promemoria | Messaggio + data + ora + priorità (🔴🟡🟢) |
| ⚡ Avvisi automatici | Persone non contattate da troppo tempo |
| 📊 Statistiche | Totali, top contatti, persone per tipo |
| 🏷️ Tipi | Lista tipi esistenti, crea nuovo tipo |

---

## 🖥️ Funzionalità App Desktop

| Sezione | Funzione |
|---|---|
| 👤 Persone | Lista con ricerca e filtro tipo, card cliccabili |
| Scheda persona | Dati, tipi, note, storico interazioni, promemoria |
| 📊 Statistiche | Grafici matplotlib: torta per tipo, barre per mese, top 5, rischio silenzio |
| 🔔 Promemoria | Tab manuali + tab automatici con banner in cima |
| ⚙️ Impostazioni | Gestione tipi e priorità con color picker |

---

## 🔧 Dipendenze

### App Desktop (virtual environment `~/mypeople-env`)
```
PyQt6              # interfaccia grafica
psycopg2-binary    # connessione PostgreSQL
matplotlib         # grafici statistiche
pyinstaller        # compilazione .app Mac
```

### Bot Telegram (requirements.txt per Render)
```
python-telegram-bot[job-queue]==20.7   # bot + scheduler
psycopg2-binary==2.9.9                 # connessione PostgreSQL
flask==3.0.3                           # keep-alive HTTP
```

---

## ⚠️ Note importanti

- **Il token Telegram non va mai nel codice** — è salvato come variabile d'ambiente su Render
- **La stringa DATABASE_URL** contiene credenziali — non pushare mai su repository pubblici
- **Il repository GitHub deve essere privato**
- **Chat ID `395777047`** è hardcoded in `bot.py` — è l'unico utente che può usare il bot e ricevere notifiche
- **I promemoria schedulati** sono in memoria (bot_data) — se Render riavvia il bot, i promemoria non ancora inviati vanno reinseriti
- **Python 3.12.0** è obbligatorio su Render (impostato come variabile d'ambiente `PYTHON_VERSION`) — la versione default 3.14 è incompatibile con psycopg2-binary
