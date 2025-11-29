#!/bin/bash
# Quick-Start Script: Quittungen generieren und analysieren

echo "🚀 Quick-Start: Quittungs-Analyse"
echo ""

# 1. Seed-Daten generieren
echo "📊 Schritt 1: Generiere Testdaten..."
python seed_database.py

if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Generieren der Daten"
    exit 1
fi

echo ""
echo "📊 Schritt 2: Analysiere Quittungen..."
echo ""

# 2. Analysieren
python analyze_receipts.py

echo ""
echo "✅ Fertig!"
echo ""
echo "💡 Weitere Optionen:"
echo "   python analyze_receipts.py --export-json receipts.json"
echo "   python analyze_receipts.py --export-csv receipts.csv"
echo ""


