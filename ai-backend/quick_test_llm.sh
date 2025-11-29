#!/bin/bash
# 🧠 Quick Test für lokales LLM

echo "🧪 LLM Quick Test"
echo "=================="
echo ""

# 1. Health Check
echo "1️⃣  Health Check..."
curl -s http://localhost:8000/api/health | python3 -m json.tool | head -10
echo ""

# 2. Demo-Daten laden
echo "2️⃣  Demo-Daten laden..."
curl -s -X POST http://localhost:8000/api/ingest/demo | python3 -m json.tool
echo ""

# 3. LLM Chat Test
echo "3️⃣  LLM Chat Test..."
echo "   Frage: 'Wie viel für Alkohol?'"
echo "   ⏳ LLM generiert Antwort (kann 30-60 Sekunden dauern)..."
echo ""

curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel habe ich für Alkohol ausgegeben?", "history": []}' \
  --max-time 120 | python3 -m json.tool

echo ""
echo "✅ Test abgeschlossen!"
