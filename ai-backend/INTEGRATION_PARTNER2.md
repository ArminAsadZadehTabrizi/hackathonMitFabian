# Integration von Partner 2's Backend

## ✅ Was wurde integriert?

Partner 2 hat ein vollständiges Datenbank-Backend mit SQLModel erstellt. Diese Komponenten wurden erfolgreich in das bestehende `ai-backend` integriert.

## 🎯 Neue Features

### 1. **SQLite Datenbank mit SQLModel**
- Persistente Speicherung aller Quittungen
- Strukturierte Queries mit SQL
- Relationship-Management (Receipts ↔ Line Items)

### 2. **Automatisches Audit-System**
Jede Quittung wird automatisch geprüft auf:
- ✅ **Fehlende MwSt.** (`flag_missing_vat`)
- ✅ **Rechenfehler** (`flag_math_error`) - Summe der Items ≠ Gesamtbetrag
- ✅ **Verdächtige Items** (`flag_suspicious`) - Alkohol, Tabak, etc.
- ✅ **Duplikate** (`flag_duplicate`) - Gleicher Vendor, Datum, Betrag

### 3. **Analytics mit SQL-Aggregationen**
- Monatliche Ausgaben-Übersicht
- Kategorie-basierte Analyse
- Präzise Berechnungen (kein LLM-Raten mehr!)

## 📁 Neue Dateien

```
ai-backend/
├── models/
│   ├── db_models.py       # SQLModel-Datenbankmodelle (ReceiptDB, LineItemDB)
│   └── db_schemas.py      # Pydantic-Schemas für API-Validierung
├── services/
│   ├── database.py        # Datenbank-Initialisierung & Session-Management
│   └── audit.py           # Audit-Logik für Quittungs-Checks
└── requirements.txt       # ✨ Ergänzt mit sqlmodel==0.0.14
```

## 🔌 Neue API-Endpoints

### Datenbank-Endpoints

#### `GET /api/receipts`
Holt alle Quittungen aus der Datenbank mit Audit-Flags.

```bash
curl http://localhost:8000/api/receipts
```

**Response:**
```json
{
  "count": 42,
  "receipts": [
    {
      "id": 1,
      "vendor_name": "REWE",
      "date": "2024-01-15T10:30:00",
      "total_amount": 45.67,
      "tax_amount": 7.32,
      "flag_duplicate": false,
      "flag_suspicious": false,
      "flag_missing_vat": false,
      "flag_math_error": false,
      ...
    }
  ]
}
```

#### `GET /api/audit`
Zeigt nur geflaggte Quittungen (mindestens ein Flag gesetzt).

```bash
curl http://localhost:8000/api/audit
```

**Use Case:** Audit-Dashboard im Frontend

#### `POST /api/ingest/db`
Speichert eine Quittung mit Line Items in der Datenbank.

```bash
curl -X POST http://localhost:8000/api/ingest/db \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "REWE",
    "date": "2024-01-15T10:30:00",
    "total_amount": 45.67,
    "tax_amount": 7.32,
    "currency": "EUR",
    "category": "Lebensmittel",
    "items": [
      {"description": "Brot", "amount": 2.99},
      {"description": "Milch", "amount": 1.29}
    ]
  }'
```

### Analytics-Endpoints (erweitert)

#### `GET /api/analytics/monthly`
Monatliche Ausgaben-Übersicht.

```bash
curl http://localhost:8000/api/analytics/monthly
```

**Response:**
```json
{
  "monthly_totals": [
    {"month": "2024-01", "total": 1234.56},
    {"month": "2024-02", "total": 987.65}
  ]
}
```

#### `GET /api/analytics/categories`
Ausgaben pro Kategorie (nutzt jetzt SQL statt RAG).

```bash
curl http://localhost:8000/api/analytics/categories
```

## 🔄 Angepasste Endpoints

### `POST /api/extract/upload` (erweitert)

**Neu:** Speichert extrahierte Quittungen automatisch auch in der SQL-Datenbank!

**Workflow:**
1. 📸 Bild hochladen
2. 🧠 LLM extrahiert Daten
3. 📊 Speicherung in RAG (für semantische Suche)
4. 💾 **NEU:** Speicherung in SQL-DB (für strukturierte Queries)
5. ✅ **NEU:** Automatische Audit-Checks

**Response:**
```json
{
  "id": "upload_receipt.jpg",
  "vendor_name": "REWE",
  "total": 45.67,
  "validation": {
    "status": "valid",
    "warnings_count": 0
  },
  "db_id": 123,
  "audit_flags": {
    "duplicate": false,
    "suspicious": false,
    "missing_vat": false,
    "math_error": false
  }
}
```

## 🗄️ Datenbank-Schema

### Tabelle: `receipts`
```sql
CREATE TABLE receipts (
    id INTEGER PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    date DATETIME NOT NULL,
    total_amount REAL NOT NULL,
    tax_amount REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    category TEXT,
    -- Audit Flags
    flag_duplicate BOOLEAN DEFAULT FALSE,
    flag_suspicious BOOLEAN DEFAULT FALSE,
    flag_missing_vat BOOLEAN DEFAULT FALSE,
    flag_math_error BOOLEAN DEFAULT FALSE
);
```

### Tabelle: `line_items`
```sql
CREATE TABLE line_items (
    id INTEGER PRIMARY KEY,
    receipt_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (receipt_id) REFERENCES receipts(id)
);
```

## 🚀 Installation & Setup

### 1. Dependencies installieren

```bash
cd ai-backend
# Aktiviere dein venv (falls vorhanden)
pip install -r requirements.txt
```

Die `requirements.txt` wurde aktualisiert mit:
- `sqlmodel==0.0.14`

### 2. Backend starten

```bash
python main.py
```

Die Datenbank (`receipts.db`) wird automatisch beim Start erstellt.

## 🧪 Testing

### Test 1: Quittung manuell hinzufügen

```bash
curl -X POST http://localhost:8000/api/ingest/db \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "Test Shop",
    "date": "2024-01-15T10:30:00",
    "total_amount": 100.00,
    "tax_amount": 19.00,
    "currency": "EUR",
    "category": "Test",
    "items": [
      {"description": "Item 1", "amount": 50.00},
      {"description": "Item 2", "amount": 50.00}
    ]
  }'
```

### Test 2: Alle Quittungen abrufen

```bash
curl http://localhost:8000/api/receipts
```

### Test 3: Audit-Quittungen anzeigen

```bash
curl http://localhost:8000/api/audit
```

### Test 4: Duplikat erstellen (sollte geflaggt werden)

Führe Test 1 zweimal aus - die zweite Quittung sollte `flag_duplicate: true` haben.

### Test 5: Verdächtige Items (Alkohol)

```bash
curl -X POST http://localhost:8000/api/ingest/db \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "Bar",
    "date": "2024-01-15T22:00:00",
    "total_amount": 25.00,
    "tax_amount": 4.75,
    "currency": "EUR",
    "category": "Bar",
    "items": [
      {"description": "Beer", "amount": 5.00},
      {"description": "Wine", "amount": 20.00}
    ]
  }'
```

Sollte `flag_suspicious: true` haben.

## 🎨 Frontend-Integration

### Beispiel: Audit-Dashboard

```typescript
// Geflaggte Quittungen laden
const response = await fetch('http://localhost:8000/api/audit');
const data = await response.json();

// Anzeigen
data.flagged_receipts.forEach(receipt => {
  if (receipt.flag_duplicate) {
    console.log('⚠️ Duplikat:', receipt.vendor_name);
  }
  if (receipt.flag_suspicious) {
    console.log('🚨 Verdächtig:', receipt.vendor_name);
  }
  if (receipt.flag_missing_vat) {
    console.log('📋 Fehlende MwSt:', receipt.vendor_name);
  }
  if (receipt.flag_math_error) {
    console.log('🧮 Rechenfehler:', receipt.vendor_name);
  }
});
```

## 🔧 Architektur

```
┌─────────────────┐
│   Frontend      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                  │
│  ┌───────────────┐  ┌─────────────────┐ │
│  │ AI Services   │  │ DB Services     │ │
│  │               │  │                 │ │
│  │ - Ollama LLM  │  │ - SQLModel ORM  │ │
│  │ - ChromaDB    │  │ - Audit System  │ │
│  │   (RAG)       │  │ - Analytics     │ │
│  └───────┬───────┘  └────────┬────────┘ │
└──────────┼──────────────────┬┼──────────┘
           │                  ││
           ▼                  ▼▼
    ┌─────────────┐    ┌─────────────┐
    │  ChromaDB   │    │  SQLite     │
    │  (Vector)   │    │  (receipts) │
    └─────────────┘    └─────────────┘
```

### Datenfluß beim Upload:

1. **Bild hochladen** → `/api/extract/upload`
2. **LLM-Extraktion** → Ollama Vision Model
3. **Duale Speicherung:**
   - 📊 **ChromaDB** (für semantische Suche, Chat)
   - 💾 **SQLite** (für strukturierte Queries, Audit)
4. **Audit-Checks** → Automatisch durchgeführt
5. **Response** → Enthält Extraktionsdaten + Audit-Flags

## 📝 Nächste Schritte

### Frontend-Seite (Person 3):
1. ✅ Audit-Dashboard erstellen
2. ✅ Geflaggte Quittungen anzeigen
3. ✅ Analytics-Charts (monatlich, Kategorien)

### Backend-Optimierungen:
1. 🔄 Batch-Import für mehrere Quittungen
2. 📊 Erweiterte Analytics (Trends, Vergleiche)
3. 🔍 Filter & Sortierung für `/api/receipts`
4. 💡 Machine Learning für Kategorie-Vorschläge

## 🐛 Troubleshooting

### Problem: `sqlmodel` nicht gefunden
```bash
pip install sqlmodel
```

### Problem: Datenbank-Fehler beim Start
```bash
# Lösche alte DB und starte neu
rm receipts.db
python main.py
```

### Problem: Audit-Checks funktionieren nicht
- Stelle sicher, dass `tax_amount` gesetzt ist (sonst `flag_missing_vat`)
- Prüfe, ob Line Items vorhanden sind (für `flag_math_error`)

## 🎉 Erfolgreiche Integration!

- ✅ Beide Backends verschmolzen
- ✅ Alle Endpoints funktional
- ✅ Datenbank-Schema implementiert
- ✅ Audit-System aktiv
- ✅ Analytics erweitert
- ✅ Dokumentation erstellt

**Das System ist produktionsbereit!** 🚀

