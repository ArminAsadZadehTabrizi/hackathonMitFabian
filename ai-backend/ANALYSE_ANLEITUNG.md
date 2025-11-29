# 📊 Quittungen analysieren - Anleitung

## 🎯 Übersicht

Mit diesem Tool kannst du:
- ✅ Quittungen aus der Datenbank extrahieren
- ✅ Statistiken und Reports generieren
- ✅ Daten als JSON/CSV exportieren
- ✅ Audit-Flags analysieren

## 🚀 Schnellstart

### 1. Testdaten generieren (falls noch nicht vorhanden)

```bash
cd ai-backend

# Option A: Nutze das integrierte Script
python seed_database.py

# Option B: Nutze das Backend direkt
cd ../backend
python seed.py
```

Dies generiert **50 Test-Quittungen** mit verschiedenen Audit-Szenarien.

### 2. Quittungen analysieren

```bash
# Einfache Analyse (zeigt Statistiken)
python analyze_receipts.py
```

**Output:**
```
📊 QUITTUNGS-ANALYSE REPORT
============================================================
📈 Grundstatistiken:
   Gesamtanzahl Quittungen: 50
   Gesamtbetrag: 2847.35 EUR
   Gesamte MwSt: 541.00 EUR
   Durchschnitt pro Quittung: 56.95 EUR
   
✅ Audit-Flags:
   ✓ Saubere Quittungen: 35
   ⚠️  Duplikate: 0
   🚨 Verdächtige Items: 5
   📋 Fehlende MwSt: 5
   🧮 Rechenfehler: 5
```

## 📤 Daten exportieren

### JSON Export

```bash
python analyze_receipts.py --export-json receipts.json
```

**Format:**
```json
[
  {
    "id": 1,
    "vendor_name": "Amazon",
    "date": "2024-01-15T10:30:00",
    "total_amount": 125.50,
    "tax_amount": 23.85,
    "currency": "EUR",
    "category": "Office Supplies",
    "audit_flags": {
      "duplicate": false,
      "suspicious": false,
      "missing_vat": false,
      "math_error": false
    },
    "line_items": [
      {
        "id": 1,
        "description": "Office Chair",
        "amount": 125.50
      }
    ]
  }
]
```

### CSV Export

```bash
python analyze_receipts.py --export-csv receipts.csv
```

**Format:** Tabellarisch mit allen Feldern + Audit-Flags

## 🔌 API-Modus

Falls das Backend läuft, kannst du auch die API nutzen:

```bash
# Starte Backend (in einem Terminal)
python main.py

# Analysiere über API (in einem anderen Terminal)
python analyze_receipts.py --api
```

## 📊 Detaillierte Statistiken

### Nur JSON-Output (für Scripts)

```bash
python analyze_receipts.py --stats-only
```

Gibt nur die Statistiken als JSON aus (maschinenlesbar).

### Kombiniert: Export + Statistiken

```bash
python analyze_receipts.py --export-json receipts.json --export-csv receipts.csv
```

## 🎯 Beispiel-Workflows

### Workflow 1: Neue Daten analysieren

```bash
# 1. Neue Daten generieren
python seed_database.py

# 2. Analysieren
python analyze_receipts.py

# 3. Exportieren für weiteres Processing
python analyze_receipts.py --export-json analysis.json
```

### Workflow 2: Geflaggte Quittungen finden

```bash
# Analysieren
python analyze_receipts.py --export-json receipts.json

# In Python/JavaScript weiterverarbeiten:
# Gefilterte Liste nur mit geflaggten Quittungen
```

### Workflow 3: API-Integration

```bash
# Terminal 1: Backend starten
python main.py

# Terminal 2: Daten über API abrufen
python analyze_receipts.py --api --export-json receipts.json
```

## 📋 Verfügbare Optionen

```bash
python analyze_receipts.py --help
```

**Optionen:**
- `--api` - Nutze API statt direkten DB-Zugriff
- `--api-url URL` - API Base URL (Standard: http://localhost:8000)
- `--export-json FILE` - Exportiere als JSON
- `--export-csv FILE` - Exportiere als CSV
- `--stats-only` - Zeige nur JSON-Statistiken

## 🔍 Was wird analysiert?

### Grundstatistiken
- Gesamtanzahl Quittungen
- Gesamtbetrag (Summe)
- Gesamte MwSt.
- Durchschnitt pro Quittung
- Zeitraum (frühester/spätestes Datum)

### Audit-Flags
- **Duplikate:** Gleiche Quittung mehrfach vorhanden?
- **Verdächtig:** Enthält Alkohol/Tabak?
- **MwSt fehlt:** Keine oder 0% MwSt.?
- **Rechenfehler:** Summe Items ≠ Gesamtbetrag?

### Gruppierungen
- **Nach Kategorie:** Wie viele Quittungen pro Kategorie?
- **Nach Vendor:** Wie viele Quittungen pro Händler?

## 🐛 Troubleshooting

### Problem: "Keine Quittungen gefunden"

**Lösung:**
```bash
# Generiere Testdaten
python seed_database.py

# Oder
cd ../backend && python seed.py
```

### Problem: "requests nicht installiert" (API-Modus)

**Lösung:**
```bash
pip install requests
```

Oder nutze den DB-Modus ohne `--api` Flag.

### Problem: Datenbank-Fehler

**Lösung:**
```bash
# Lösche alte DB und starte neu
rm receipts.db
python seed_database.py
```

## 💡 Tipps

1. **JSON für Weiterverarbeitung:** Nutze `--export-json` für Python/JavaScript Scripts
2. **CSV für Excel:** Nutze `--export-csv` für Tabellenkalkulation
3. **API für Live-Daten:** Nutze `--api` wenn Backend läuft
4. **Statistiken filtern:** JSON-Export kann mit `jq` gefiltert werden:
   ```bash
   python analyze_receipts.py --export-json receipts.json
   jq '.[] | select(.audit_flags.suspicious == true)' receipts.json
   ```

## 📚 Weiterführende Links

- `INTEGRATION_PARTNER2.md` - Vollständige API-Dokumentation
- `backend/seed.py` - Seed-Script Details
- FastAPI Docs: http://localhost:8000/docs

---

**Viel Erfolg beim Analysieren! 🚀**


