#!/bin/bash
# Quick-Start Script für die Integration von Partner 2's Backend

echo "🚀 Installation der Integration..."
echo ""

# Prüfen, ob wir im richtigen Verzeichnis sind
if [ ! -f "requirements.txt" ]; then
    echo "❌ Fehler: Bitte aus dem ai-backend/ Verzeichnis ausführen"
    exit 1
fi

echo "📦 Installiere Dependencies..."
echo ""

# Prüfen, ob venv aktiviert ist
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Kein virtuelles Environment aktiv!"
    echo "   Empfehlung: source venv/bin/activate"
    echo ""
    read -p "   Trotzdem fortfahren? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Dependencies installieren
pip install -r requirements.txt

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo ""
echo "1. Backend starten:"
echo "   python main.py"
echo ""
echo "2. In einem anderen Terminal testen:"
echo "   curl http://localhost:8000/api/health"
echo "   curl http://localhost:8000/api/receipts"
echo ""
echo "3. Dokumentation lesen:"
echo "   cat INTEGRATION_PARTNER2.md"
echo ""
echo "🎉 Integration erfolgreich!"


