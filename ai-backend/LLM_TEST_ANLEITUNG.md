# 🧠 Anleitung: Lokales LLM testen

## 🚀 Schnellstart - LLM einmal durchlaufen lassen

### **Option 1: Direkt mit Ollama (Einfachster Test)**

```bash
# Test 1: Einfache Frage stellen
ollama run llama3.2 "Was ist RAG?"

# Test 2: Chat-Gespräch
ollama run llama3.2
# Dann kannst du direkt Fragen stellen:
# > Was ist Machine Learning?
# > Erkläre mir Vector Search
# > exit (zum Beenden)
```

---

### **Option 2: Über dein AI-Backend (Empfohlen für Demo)**

#### **Schritt 1: Server starten (falls nicht läuft)**
```bash
cd ai-backend
source venv/bin/activate
python main.py
```

#### **Schritt 2: Demo-Daten laden**
```bash
curl -X POST http://localhost:8000/api/ingest/demo
```

#### **Schritt 3: LLM testen - Chat**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel habe ich für Alkohol ausgegeben?", "history": []}' \
  | python3 -m json.tool
```

**Was passiert:**
1. System sucht relevante Quittungen (Vector Search)
2. Formatiert Kontext
3. **LLM generiert Antwort** ← Hier läuft dein lokales LLM!

---

## 📋 Detaillierte Test-Szenarien

### **Szenario 1: Einfacher Chat-Test**

```bash
# Frage stellen
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hallo! Kannst du mir helfen?",
    "history": []
  }' \
  | python3 -m json.tool
```

**Erwartung:** LLM antwortet auf Deutsch

---

### **Szenario 2: RAG Chat (Mit Kontext)**

```bash
# 1. Demo-Daten laden (falls noch nicht)
curl -X POST http://localhost:8000/api/ingest/demo

# 2. Frage mit Kontext
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Was waren meine höchsten Ausgaben?",
    "history": []
  }' \
  | python3 -m json.tool
```

**Was passiert:**
- System findet relevante Quittungen
- **LLM bekommt Kontext** → Generiert präzise Antwort

---

### **Szenario 3: Bild-Extraktion (Vision Model)**

```bash
# Quittungsbild hochladen
curl -X POST http://localhost:8000/api/extract/upload \
  -F "file=@/path/to/receipt.jpg" \
  | python3 -m json.tool
```

**Was passiert:**
- **Vision Model (llama3.2-vision) analysiert Bild**
- Extrahiert strukturierte Daten
- Gibt JSON zurück

---

## 🔬 Interaktive Tests

### **Test 1: Python Script**

Erstelle `test_llm.py`:

```python
import requests
import json

API_BASE = "http://localhost:8000"

# Test 1: Health Check
print("1. Health Check...")
r = requests.get(f"{API_BASE}/api/health")
print(json.dumps(r.json(), indent=2))

# Test 2: Demo-Daten laden
print("\n2. Demo-Daten laden...")
r = requests.post(f"{API_BASE}/api/ingest/demo")
print(r.json()["message"])

# Test 3: Chat
print("\n3. LLM Chat Test...")
r = requests.post(
    f"{API_BASE}/api/chat",
    json={"message": "Wie viel für Alkohol?", "history": []},
    timeout=60
)
print(f"Frage: Wie viel für Alkohol?")
print(f"Antwort: {r.json()['response']}")
```

**Ausführen:**
```bash
cd ai-backend
source venv/bin/activate
python test_llm.py
```

---

### **Test 2: Mit dem interaktiven Test-Script**

```bash
cd ai-backend
source venv/bin/activate
python test_interactive.py
```

**Das Script testet:**
- ✅ Health Check
- ✅ Demo-Daten laden
- ✅ Semantische Suche
- ✅ **RAG Chat (LLM)**
- ✅ Analytics

---

## 🎯 Einfachster Test (Copy & Paste)

### **Kompletter Durchlauf in 3 Commands:**

```bash
# 1. Server starten (in neuem Terminal)
cd ai-backend
source venv/bin/activate
python main.py

# 2. Demo-Daten laden (in neuem Terminal)
curl -X POST http://localhost:8000/api/ingest/demo

# 3. LLM testen (in neuem Terminal)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel habe ich für Alkohol ausgegeben?", "history": []}' \
  | python3 -m json.tool
```

**Das war's!** Dein LLM hat gerade eine Frage beantwortet! 🎉

---

## 🔍 Was passiert im Hintergrund?

### **Wenn du `/api/chat` aufrufst:**

```
1. Request kommt an
   ↓
2. System sucht relevante Quittungen (Vector Search)
   ↓
3. Kontext wird formatiert:
   "--- Quittung 1 ---
    Restaurant La Piazza
    Wein: 28€
    ..."
   ↓
4. Ollama LLM wird aufgerufen:
   ollama.chat(
     model="llama3.2",
     messages=[
       {"role": "system", "content": "Du bist..."},
       {"role": "user", "content": "Frage + Kontext"}
     ]
   )
   ↓
5. LLM generiert Antwort (lokal auf deinem PC!)
   ↓
6. Antwort wird zurückgegeben
```

**Alles läuft lokal - keine Cloud!**

---

## 🧪 Verschiedene Fragen testen

### **Einfache Fragen:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Was ist Machine Learning?", "history": []}'
```

### **Fragen zu Quittungen:**
```bash
# Nach Alkohol fragen
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie viel für Alkohol?", "history": []}'

# Nach höchsten Ausgaben fragen
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Was waren meine Top 3 Ausgaben?", "history": []}'

# Nach Kategorien fragen
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "In welchen Kategorien habe ich am meisten ausgegeben?", "history": []}'
```

---

## 🐛 Troubleshooting

### **Problem: LLM antwortet nicht**

**Prüfe ob Ollama läuft:**
```bash
curl http://localhost:11434/api/tags
```

**Ollama starten:**
```bash
ollama serve
```

**Modelle prüfen:**
```bash
ollama list
```

**Sollte zeigen:**
```
llama3.2:latest
llama3.2-vision:latest
```

---

### **Problem: Timeout**

LLM kann 30-60 Sekunden dauern. Erhöhe Timeout:
```bash
curl --max-time 120 -X POST http://localhost:8000/api/chat ...
```

---

### **Problem: Server läuft nicht**

```bash
cd ai-backend
source venv/bin/activate
python main.py
```

---

## 📊 Performance-Monitoring

### **LLM-Aufruf beobachten:**

```bash
# In einem Terminal: Server-Logs ansehen
tail -f ai-backend/server.log

# In anderem Terminal: Request senden
curl -X POST http://localhost:8000/api/chat ...
```

**Du siehst:**
- Wann LLM aufgerufen wird
- Wie lange es dauert
- Eventuelle Fehler

---

## 🎤 Für die Demo

### **Live-Demo Flow:**

1. **"Zeigen Sie Health Check"**
   ```bash
   curl http://localhost:8000/api/health
   ```
   → Zeigt: Ollama online, Server läuft

2. **"Laden Sie Demo-Daten"**
   ```bash
   curl -X POST http://localhost:8000/api/ingest/demo
   ```
   → Zeigt: 6 Quittungen geladen

3. **"Stellen Sie eine Frage"**
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -d '{"message": "Wie viel für Alkohol?"}'
   ```
   → **LLM generiert Antwort live!**

4. **"Erklären Sie was passiert"**
   - Vector Search findet Quittungen
   - Kontext wird formatiert
   - **LLM läuft lokal auf PC**
   - Antwort wird generiert

---

## ✅ Checkliste

- [ ] Ollama läuft (`ollama list`)
- [ ] Server läuft (`curl http://localhost:8000/api/health`)
- [ ] Demo-Daten geladen
- [ ] Chat funktioniert
- [ ] LLM antwortet (kann 30-60 Sekunden dauern)

---

## 🚀 Quick Test (30 Sekunden)

```bash
# Alles in einem:
cd ai-backend && \
source venv/bin/activate && \
curl -X POST http://localhost:8000/api/ingest/demo && \
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "history": []}' \
  | python3 -m json.tool
```

**Wenn du eine Antwort siehst → LLM funktioniert! ✅**

---

**Viel Erfolg beim Testen! 🎉**

