# 🧪 Testing Guide - RAG System

## ✅ Schnelltest (Alles auf einmal)

```bash
cd ai-backend
source venv/bin/activate
python test_interactive.py
```

---

## 🔍 Einzelne Tests

### 1. Health Check
```bash
curl http://localhost:8000/api/health | python3 -m json.tool
```

**Erwartetes Ergebnis:**
```json
{
    "status": "healthy",
    "ollama": {
        "status": "online",
        "models": []
    },
    "rag": {
        "total_documents": 6,
        "backend": "in_memory_fallback"
    }
}
```

---

### 2. Demo-Daten laden
```bash
curl -X POST http://localhost:8000/api/ingest/demo | python3 -m json.tool
```

**Erwartetes Ergebnis:**
```json
{
    "message": "Demo-Daten geladen!",
    "stats": {
        "total_documents": 6
    }
}
```

---

### 3. Semantische Suche

#### Test 3a: Suche nach "Alkohol"
```bash
curl "http://localhost:8000/api/search?query=Alkohol&limit=3" | python3 -m json.tool
```

**Was passiert:**
- System berechnet Embedding für "Alkohol"
- Findet ähnliche Quittungen (z.B. Restaurant mit Wein, Supermarkt mit Wein)
- Gibt Top 3 mit Relevanz-Scores zurück

#### Test 3b: Suche nach "Restaurant"
```bash
curl "http://localhost:8000/api/search?query=Restaurant&limit=2" | python3 -m json.tool
```

#### Test 3c: Suche nach "höchste Ausgaben"
```bash
curl "http://localhost:8000/api/search?query=höchste%20Ausgaben&limit=3" | python3 -m json.tool
```

**Erwartetes Ergebnis:**
```json
{
    "query": "höchste Ausgaben",
    "results": [
        {
            "id": "demo_2",
            "document": "Quittung von IKEA...",
            "metadata": {
                "vendor_name": "IKEA",
                "total": 234.9,
                "category": "Möbel"
            },
            "similarity": 0.89
        }
    ]
}
```

---

### 4. RAG Chat

#### Test 4a: Einfache Frage
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel habe ich für Alkohol ausgegeben?", "history": []}' \
  | python3 -m json.tool
```

**Was passiert:**
1. System sucht relevante Quittungen (Vector Search)
2. Formatiert Kontext
3. LLM generiert Antwort basierend auf Kontext

**Erwartetes Ergebnis:**
```json
{
    "response": "Basierend auf den Quittungen haben Sie insgesamt 43.98€ für Alkohol ausgegeben...",
    "sources_used": 5
}
```

#### Test 4b: Top Ausgaben
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Was waren meine Top 3 Ausgaben?", "history": []}' \
  | python3 -m json.tool
```

#### Test 4c: Kategorien-Frage
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "In welchen Kategorien habe ich am meisten ausgegeben?", "history": []}' \
  | python3 -m json.tool
```

---

### 5. Analytics
```bash
curl http://localhost:8000/api/analytics/categories | python3 -m json.tool
```

**Erwartetes Ergebnis:**
```json
{
    "spending_by_category": {
        "Restaurant": 89.5,
        "Supermarkt": 47.89,
        "Tankstelle": 72.5,
        "Online Shopping": 159.97,
        "Möbel": 234.9,
        "Café": 12.4
    }
}
```

---

## 🎯 Test-Szenarien für die Demo

### Szenario 1: "Alkohol-Ausgaben finden"
```bash
# 1. Suche
curl "http://localhost:8000/api/search?query=Alkohol&limit=5"

# 2. Chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel für Alkohol?", "history": []}'
```

**Erwartung:** Findet Restaurant (Wein 28€) und REWE (Wein 15.98€)

---

### Szenario 2: "Höchste Ausgaben"
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Was waren meine höchsten Ausgaben?", "history": []}'
```

**Erwartung:** IKEA (234.90€), Amazon (159.97€), Restaurant (89.50€)

---

### Szenario 3: "Kategorien-Analyse"
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Zeige mir alle Ausgaben nach Kategorie", "history": []}'
```

---

## 🐛 Troubleshooting

### Problem: Server läuft nicht
```bash
# Server starten
cd ai-backend
source venv/bin/activate
python main.py
```

### Problem: Ollama nicht erreichbar
```bash
# Ollama prüfen
curl http://localhost:11434/api/tags

# Ollama starten (falls nicht läuft)
ollama serve
```

### Problem: Keine Demo-Daten
```bash
# Demo-Daten laden
curl -X POST http://localhost:8000/api/ingest/demo
```

### Problem: Chat antwortet nicht
- Prüfe ob Ollama läuft: `ollama list`
- Prüfe Server-Logs: `tail -f ai-backend/server.log`
- Timeout erhöhen (Chat kann 30-60 Sekunden dauern)

---

## 📊 Was die Tests prüfen

### ✅ Vector Search funktioniert
- Semantische Suche findet relevante Quittungen
- Relevanz-Scores sind sinnvoll
- Filter funktionieren

### ✅ RAG funktioniert
- System findet relevante Quittungen für Fragen
- LLM bekommt Kontext
- Antworten sind präzise und basieren auf Daten

### ✅ Embeddings funktionieren
- Ähnliche Texte haben ähnliche Vektoren
- "Alkohol" findet "Wein", "Bier", etc.
- "Restaurant" findet Essens-Quittungen

---

## 🎤 Für die Präsentation

### Live-Demo Flow:

1. **"Zeigen Sie uns die Demo-Daten"**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **"Suchen Sie nach Alkohol"**
   ```bash
   curl "http://localhost:8000/api/search?query=Alkohol"
   ```
   → Zeigt: Vector Search findet relevante Quittungen

3. **"Fragen Sie das System"**
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -d '{"message": "Wie viel für Alkohol?"}'
   ```
   → Zeigt: RAG generiert intelligente Antwort

4. **"Analytics"**
   ```bash
   curl http://localhost:8000/api/analytics/categories
   ```
   → Zeigt: Datenvisualisierung

---

## 🔬 Erweiterte Tests

### Test: Embedding-Qualität
```python
from services.rag_service import search_receipts

# Test verschiedene Formulierungen
queries = [
    "Alkohol",
    "Wein",
    "Getränke mit Alkohol",
    "Spirituosen"
]

for query in queries:
    results = search_receipts(query, n_results=3)
    print(f"{query}: {[r['metadata']['vendor_name'] for r in results]}")
```

### Test: RAG-Kontext
```python
from services.rag_service import get_context_for_query

context = get_context_for_query("Alkohol", n_results=3)
print(context)
# → Zeigt formatierten Kontext, der an LLM geht
```

---

## ✅ Checkliste

- [ ] Server läuft (`/api/health`)
- [ ] Demo-Daten geladen (6 Quittungen)
- [ ] Suche funktioniert (findet relevante Quittungen)
- [ ] Chat funktioniert (generiert Antworten)
- [ ] Analytics funktioniert (Kategorien)
- [ ] Ollama läuft (Modelle verfügbar)

---

**Viel Erfolg beim Testen! 🚀**

