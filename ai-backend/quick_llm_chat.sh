#!/bin/bash
# Quick-Start: Chat mit Quittungen via LLM

echo "🤖 Quick-Start: Chat mit lokalem LLM"
echo ""

# Prüfe Ollama
echo "🔍 Prüfe Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama läuft nicht!"
    echo ""
    echo "Starte Ollama in einem anderen Terminal:"
    echo "   ollama serve"
    echo ""
    read -p "Trotzdem fortfahren? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Ollama läuft"
fi

echo ""
echo "🚀 Starte Chat..."
echo ""

python3 chat_with_db_receipts.py --load-rag


