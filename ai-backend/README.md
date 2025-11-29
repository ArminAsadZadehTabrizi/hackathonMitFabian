# 🧠 Finanz AI Backend

**Local LLM + RAG System für Quittungs-Analyse**

Dieses Backend nutzt:
- **Ollama** (lokales LLM) für Bild-Extraktion und Chat
- **ChromaDB** (Vektor-DB) für semantische Suche
- **FastAPI** für die REST API

---

## 🚀 Quick Start

### 1. Ollama installieren

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download von https://ollama.com/download
```

### 2. Ollama starten

```bash
ollama serve
```

### 3. Setup ausführen

```bash
cd ai-backend
chmod +x setup.sh
./setup.sh
```

### 4. Server starten

```bash
source venv/bin/activate
python main.py
```

Der Server läuft dann auf `http://localhost:8000`

---

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```

### Quittung extrahieren (Bild → JSON)
```bash
POST /api/extract/upload
Content-Type: multipart/form-data

file: <receipt_image.jpg>
```

### Chat mit RAG
```bash
POST /api/chat
Content-Type: application/json

{
    "message": "Wie viel habe ich für Essen ausgegeben?",
    "history": []
}
```

### Semantische Suche
```bash
GET /api/search?query=Tankstelle&limit=5
```

### Demo-Daten laden
```bash
POST /api/ingest/demo
```

---

## 🔧 Konfiguration

Alle Einstellungen in `.env`:

```env
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2-vision      # Für Bild-Analyse
OLLAMA_CHAT_MODEL=llama3.2        # Für Chat

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db

# API
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 🏗️ Architektur

```
┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI       │
│   (React/MUI)   │     │   Backend       │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
           ┌──────────────┐ ┌──────────┐ ┌──────────┐
           │   Ollama     │ │ ChromaDB │ │ SQLite   │
           │   (LLM)      │ │ (Vector) │ │ (Person2)│
           └──────────────┘ └──────────┘ └──────────┘
```

---

## 📁 Ordnerstruktur

```
ai-backend/
├── main.py              # FastAPI Server
├── config.py            # Konfiguration
├── requirements.txt     # Dependencies
├── setup.sh            # Setup Script
├── models/
│   └── receipt.py      # Pydantic Models
├── services/
│   ├── ollama_service.py    # LLM Integration
│   ├── rag_service.py       # ChromaDB RAG
│   └── cord_ingestion.py    # Dataset Loader
├── data/
│   └── cord/           # CORD Dataset (optional)
└── chroma_db/          # Vektor-Datenbank
```

---

## 🎯 Features

### 1. Receipt Extraction (Bild → JSON)
Das Vision-Model analysiert Quittungsbilder und extrahiert:
- Vendor Name & Adresse
- Datum
- Einzelpositionen mit Preisen
- Gesamtbetrag, MwSt, etc.

### 2. RAG Chat
Nutzer können Fragen stellen wie:
- "Wie viel habe ich für Alkohol ausgegeben?"
- "Zeige mir alle Restaurant-Belege"
- "Was waren meine Top 5 Ausgaben?"

Das System:
1. Sucht relevante Quittungen via Vector Search
2. Übergibt diese als Kontext an das LLM
3. Generiert eine natürlichsprachliche Antwort

### 3. CORD Dataset Integration
Unterstützt das CORD Dataset für Demo-Daten:
- https://github.com/clovaai/cord

---

## 🤝 Integration mit Person 2 (Backend)

Person 2 sollte diese Endpoints aufrufen:

```python
import requests

# Neue Quittung in RAG speichern
requests.post("http://localhost:8000/api/receipt", json={
    "vendor_name": "REWE",
    "date": "2024-01-15",
    "total": 47.89,
    "category": "Supermarkt",
    "line_items": [...]
})

# Chat-Anfrage weiterleiten
response = requests.post("http://localhost:8000/api/chat", json={
    "message": "Wie viel für Essen?",
    "history": []
})
```

---

## 🐛 Troubleshooting

### Ollama läuft nicht
```bash
# Prüfen
curl http://localhost:11434/api/tags

# Neu starten
ollama serve
```

### Modell nicht gefunden
```bash
# Modelle auflisten
ollama list

# Modell laden
ollama pull llama3.2-vision
ollama pull llama3.2
```

### ChromaDB Fehler
```bash
# Datenbank löschen und neu starten
rm -rf chroma_db/
python main.py
```

---

## 📊 Performance Tipps

1. **Kleinere Modelle nutzen** für schnellere Inference:
   - `llama3.2:1b` statt `llama3.2` für Chat
   - `llava:7b` statt `llama3.2-vision` für Bilder

2. **Batch Processing** für viele Quittungen:
   ```python
   from services.rag_service import add_receipts_batch
   add_receipts_batch([(id1, r1), (id2, r2), ...])
   ```

3. **GPU nutzen** (falls verfügbar):
   Ollama nutzt automatisch die GPU wenn vorhanden.

---

Made with 🧠 für den Hackathon!


