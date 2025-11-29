# 🚀 Small Business Auto-Bookkeeper - Setup Guide

> Hackathon 2 – Local AI Edition

## Schnellstart

```bash
# Im Projektverzeichnis:
./start.sh
```

Das startet automatisch:
- 🧠 AI-Backend auf http://localhost:8000
- 📊 Frontend auf http://localhost:8082
- 🤖 Prüft/startet Ollama

---

## Voraussetzungen

### 1. Node.js (>=20)
```bash
node --version  # Sollte v20+ zeigen
```

### 2. Python 3.11
```bash
python3.11 --version
# Falls nicht vorhanden:
brew install python@3.11
```

### 3. Ollama
```bash
# Installation
brew install ollama

# Starten
ollama serve

# Modelle laden (einmalig)
ollama pull llama3.2
ollama pull llama3.2-vision  # Optional, für Bild-Analyse
```

---

## Manuelle Installation

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### AI-Backend
```bash
cd ai-backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Datenbank mit Testdaten füllen
```bash
cd ai-backend
source venv/bin/activate
python seed_db.py
```

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    (Next.js + MUI)                          │
│                   http://localhost:8082                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ API Calls
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       AI-Backend                             │
│                   (FastAPI + Python)                         │
│                   http://localhost:8000                      │
├─────────────────────────┬───────────────────────────────────┤
│     SQLite Database     │         ChromaDB (RAG)            │
│    (receipts.db)        │        (chroma_db/)               │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                         Ollama                               │
│                   (Local LLM Server)                         │
│                   http://localhost:11434                     │
├─────────────────────────┬───────────────────────────────────┤
│    llama3.2 (Chat)      │     llama3.2-vision (OCR)         │
└─────────────────────────┴───────────────────────────────────┘
```

---

## API Endpoints

### Receipts
- `GET /api/receipts` - Alle Quittungen
- `GET /api/receipts?receiptId=1` - Einzelne Quittung
- `POST /api/ingest` - Neue Quittung erstellen

### Analytics
- `GET /api/analytics/summary` - Dashboard-Übersicht
- `GET /api/analytics/monthly` - Monatliche Daten
- `GET /api/analytics/vendors` - Vendor-Statistiken
- `GET /api/analytics/categories` - Kategorie-Ausgaben

### Audit
- `GET /api/audit` - Alle Audit-Findings

### Chat (AI Auditor)
- `POST /api/chat/query` - Frage an AI-Auditor
- `POST /api/chat` - Chat mit RAG-Kontext

### Bild-Extraktion
- `POST /api/extract` - Quittung aus Bild extrahieren
- `POST /api/extract/upload` - Bild hochladen und analysieren

---

## Features

### ✅ Pillar 1 - Auto-Bookkeeper Engine
- [x] Receipt Ingestion (JSON + Bild)
- [x] LLM-basierte Datenextraktion
- [x] Kategorisierung
- [x] Audit-Flags (Duplikate, MwSt, Rechenfehler, Verdächtige Items)

### ✅ Pillar 2 - Financial Command Center
- [x] Receipts Page (Tabelle + Details)
- [x] Analytics Dashboard
- [x] Vendor Analytics
- [x] Audit Findings

### ✅ Pillar 3 - AI Auditor Chat
- [x] Natural Language Queries
- [x] RAG mit ChromaDB
- [x] Präzise Berechnungen (Python)
- [x] LLM-formulierte Antworten

---

## Technologien

### Frontend
- Next.js 15
- React 19
- MUI v7 (Premium Template)
- TypeScript

### Backend
- FastAPI
- SQLModel + SQLite
- ChromaDB (Vector DB)
- Sentence Transformers (Embeddings)

### Local AI
- Ollama
- llama3.2 (Chat)
- llama3.2-vision (Bild-Analyse)

---

## Troubleshooting

### Port bereits belegt
```bash
# Backend Port 8000
lsof -i :8000
kill -9 <PID>

# Frontend Port 8082
lsof -i :8082
kill -9 <PID>
```

### Ollama nicht erreichbar
```bash
# Prüfen ob Ollama läuft
pgrep -f ollama

# Manuell starten
ollama serve
```

### Dependency-Probleme
```bash
# Frontend
cd frontend && rm -rf node_modules && npm install

# Backend
cd ai-backend && rm -rf venv
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Team

Hackathon 2 - 2025

