#!/bin/bash
# Setup und Test Script für die Analyse-Tools

set -e

echo "🔧 Setup und Test für Quittungs-Analyse"
echo ""

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "requirements.txt" ]; then
    echo "❌ Fehler: Bitte aus dem ai-backend/ Verzeichnis ausführen"
    exit 1
fi

# 1. Dependencies installieren
echo "📦 Schritt 1: Installiere Dependencies..."
echo ""

# Prüfe ob venv aktiviert ist
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Kein virtuelles Environment aktiv!"
    echo "   Empfehlung: Erstelle und aktiviere ein venv:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo ""
    read -p "   Trotzdem fortfahren? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    PIP_CMD="pip3 --user"
else
    PIP_CMD="pip"
fi

echo "Installiere SQLModel..."
$PIP_CMD install sqlmodel > /dev/null 2>&1 || {
    echo "❌ Installation fehlgeschlagen. Versuche es manuell:"
    echo "   $PIP_CMD install sqlmodel"
    exit 1
}

echo "✅ Dependencies installiert"
echo ""

# 2. Testdaten generieren
echo "📊 Schritt 2: Generiere Testdaten..."
echo ""

cd ../backend
python3 seed.py || {
    echo "⚠️  Seed fehlgeschlagen. Prüfe ob SQLModel installiert ist."
    exit 1
}

cd ../ai-backend

echo ""
echo "📊 Schritt 3: Analysiere Quittungen..."
echo ""

# 3. Analysieren
python3 analyze_receipts.py || {
    echo "⚠️  Analyse fehlgeschlagen."
    exit 1
}

echo ""
echo "✅ Alles erfolgreich durchgeführt!"
echo ""
echo "💡 Weitere Optionen:"
echo "   python3 analyze_receipts.py --export-json receipts.json"
echo "   python3 analyze_receipts.py --export-csv receipts.csv"
echo ""


