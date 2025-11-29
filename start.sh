#!/bin/bash
#
# 🚀 Small Business Auto-Bookkeeper - Start Script
# Startet alle Services für das Hackathon-Projekt
#

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/Users/tolga/Desktop/Propjects/Finanz"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🚀 Small Business Auto-Bookkeeper${NC}"
echo -e "${BLUE}  Hackathon 2 - Local AI Edition${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Funktion zum Beenden aller Prozesse beim Exit
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹  Beende alle Services...${NC}"
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    echo -e "${GREEN}✅ Alle Services beendet${NC}"
}
trap cleanup EXIT

# 1. Prüfe ob Ollama läuft
echo -e "${BLUE}1️⃣  Prüfe Ollama...${NC}"
if pgrep -f "ollama" > /dev/null; then
    echo -e "   ${GREEN}✅ Ollama läuft bereits${NC}"
else
    echo -e "   ${YELLOW}⏳ Starte Ollama...${NC}"
    ollama serve &>/dev/null &
    sleep 3
    echo -e "   ${GREEN}✅ Ollama gestartet${NC}"
fi

# Prüfe ob Modelle verfügbar sind
echo -e "   ${BLUE}Prüfe Modelle...${NC}"
if ollama list 2>/dev/null | grep -q "llama3.2-vision"; then
    echo -e "   ${GREEN}✅ llama3.2-vision verfügbar${NC}"
else
    echo -e "   ${YELLOW}⚠️  llama3.2-vision nicht gefunden - Bild-Analyse deaktiviert${NC}"
fi

if ollama list 2>/dev/null | grep -q "llama3.2:latest"; then
    echo -e "   ${GREEN}✅ llama3.2 verfügbar${NC}"
else
    echo -e "   ${RED}❌ llama3.2 nicht gefunden - Lade Modell...${NC}"
    ollama pull llama3.2
fi

echo ""

# 2. Starte AI-Backend
echo -e "${BLUE}2️⃣  Starte AI-Backend (Port 8000)...${NC}"
cd "$PROJECT_DIR/ai-backend"
source venv/bin/activate

# Prüfe ob Port frei ist
if lsof -i :8000 > /dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠️  Port 8000 bereits belegt - beende existierenden Prozess${NC}"
    pkill -f "uvicorn main:app.*8000" 2>/dev/null || true
    sleep 2
fi

# Starte Backend im Hintergrund
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
sleep 3

# Prüfe ob Backend läuft
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ AI-Backend läuft auf http://localhost:8000${NC}"
    echo -e "   ${GREEN}   📚 API Docs: http://localhost:8000/docs${NC}"
else
    echo -e "   ${YELLOW}⏳ AI-Backend startet noch...${NC}"
fi

echo ""

# 3. Starte Frontend
echo -e "${BLUE}3️⃣  Starte Frontend (Port 8082)...${NC}"
cd "$PROJECT_DIR/frontend"

# Prüfe ob Port frei ist
if lsof -i :8082 > /dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠️  Port 8082 bereits belegt - beende existierenden Prozess${NC}"
    pkill -f "next dev.*8082" 2>/dev/null || true
    sleep 2
fi

# Starte Frontend im Hintergrund
npm run dev &
FRONTEND_PID=$!
sleep 5

echo -e "   ${GREEN}✅ Frontend läuft auf http://localhost:8082${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Alle Services gestartet!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  📊 ${GREEN}Dashboard:${NC}     http://localhost:8082"
echo -e "  🧠 ${GREEN}AI-Backend:${NC}    http://localhost:8000"
echo -e "  📚 ${GREEN}API Docs:${NC}      http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}Drücke Ctrl+C zum Beenden aller Services${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Warte auf Services
wait

