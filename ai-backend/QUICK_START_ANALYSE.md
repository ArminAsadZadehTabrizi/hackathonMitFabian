# 🚀 Quick Start: Quittungen analysieren

## ⚡ Schnellste Methode

```bash
cd ai-backend
./setup_and_test.sh
```

## 📋 Manuelle Installation (falls Script nicht funktioniert)

### 1. Dependencies installieren

```bash
cd ai-backend

# Option A: Mit venv (empfohlen)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Option B: Global (falls kein venv)
pip3 install --user sqlmodel
```

### 2. Testdaten generieren

```bash
# Im backend/ Verzeichnis
cd ../backend
python3 seed.py

# Sollte erzeugen: receipts.db
```

### 3. Analysieren

```bash
# Zurück ins ai-backend
cd ../ai-backend
python3 analyze_receipts.py
```

## 🎯 Was passiert?

1. **Seed generiert 50 Test-Quittungen:**
   - 35 saubere Quittungen
   - 5 mit verdächtigen Items (Alkohol/Tabak)
   - 5 mit Rechenfehlern
   - 5 ohne MwSt.

2. **Analyse zeigt:**
   - Gesamtbetrag, Durchschnitt
   - Audit-Flags Übersicht
   - Top Kategorien & Vendors

## 📤 Export-Optionen

```bash
# JSON für Weiterverarbeitung
python3 analyze_receipts.py --export-json receipts.json

# CSV für Excel
python3 analyze_receipts.py --export-csv receipts.csv

# Beides
python3 analyze_receipts.py --export-json receipts.json --export-csv receipts.csv
```

## 🔍 Beispiel-Output

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

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'sqlmodel'"

**Lösung:**
```bash
pip3 install sqlmodel
# oder mit venv:
pip install sqlmodel
```

### Problem: "Keine Quittungen gefunden"

**Lösung:**
```bash
cd ../backend
python3 seed.py
```

### Problem: "No such file or directory: receipts.db"

**Lösung:** Die DB wird beim ersten seed.py Aufruf erstellt. Stelle sicher, dass seed.py erfolgreich lief.

## 📚 Weitere Infos

- Vollständige Dokumentation: `ANALYSE_ANLEITUNG.md`
- API-Dokumentation: `INTEGRATION_PARTNER2.md`


