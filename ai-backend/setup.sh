#!/bin/bash

# ===========================================
# 🧠 AI Backend Setup Script
# ===========================================

echo "🚀 Finanz AI Backend Setup"
echo "=========================="

# 1. Python Virtual Environment
echo ""
echo "📦 Erstelle Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Dependencies installieren
echo ""
echo "📥 Installiere Python Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Ordner erstellen
echo ""
echo "📁 Erstelle notwendige Ordner..."
mkdir -p data/cord
mkdir -p data/uploads
mkdir -p chroma_db

# 4. Ollama prüfen
echo ""
echo "🦙 Prüfe Ollama Installation..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama ist installiert"
    
    # Modelle prüfen/installieren
    echo ""
    echo "📥 Lade benötigte Modelle..."
    
    # Vision Model für Bild-Analyse
    if ! ollama list | grep -q "llama3.2-vision"; then
        echo "⬇️  Lade llama3.2-vision (für Bild-Extraktion)..."
        ollama pull llama3.2-vision
    else
        echo "✅ llama3.2-vision bereits vorhanden"
    fi
    
    # Chat Model für RAG
    if ! ollama list | grep -q "llama3.2"; then
        echo "⬇️  Lade llama3.2 (für Chat)..."
        ollama pull llama3.2
    else
        echo "✅ llama3.2 bereits vorhanden"
    fi
else
    echo "❌ Ollama nicht gefunden!"
    echo ""
    echo "Bitte installiere Ollama:"
    echo "  macOS:   brew install ollama"
    echo "  Linux:   curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Windows: https://ollama.com/download"
    echo ""
    echo "Dann starte Ollama mit: ollama serve"
    exit 1
fi

# 5. Environment File
echo ""
echo "📝 Erstelle .env Datei..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Ollama Konfiguration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2-vision
OLLAMA_CHAT_MODEL=llama3.2

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db

# CORD Dataset (optional)
CORD_DATA_PATH=./data/cord

# API
API_HOST=0.0.0.0
API_PORT=8000
EOF
    echo "✅ .env Datei erstellt"
else
    echo "✅ .env Datei existiert bereits"
fi

# 6. Fertig!
echo ""
echo "=========================================="
echo "✅ Setup abgeschlossen!"
echo "=========================================="
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. Starte Ollama (falls noch nicht läuft):"
echo "   ollama serve"
echo ""
echo "2. Starte den AI Backend Server:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. Öffne die API Docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. Lade Demo-Daten:"
echo "   curl -X POST http://localhost:8000/api/ingest/demo"
echo ""
echo "5. Teste den Chat:"
echo '   curl -X POST http://localhost:8000/api/chat \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '\''{"message": "Wie viel habe ich für Essen ausgegeben?"}'\'''
echo ""


