# 🤖 Quittungen mit lokalem LLM analysieren

## 🎯 Übersicht

Mit diesem Tool kannst du deine Testdaten aus der Datenbank mit dem **lokalen LLM** (Ollama) analysieren und Fragen dazu stellen.

## 🚀 Schnellstart

### 1. Ollama starten (falls nicht läuft)

```bash
ollama serve
```

In einem **anderen Terminal**:

```bash
# Modelle installieren (falls noch nicht vorhanden)
ollama pull llama3.2
```

### 2. Chat starten

```bash
cd ai-backend
python3 chat_with_db_receipts.py
```

## 📋 Verwendung

### Einfacher Chat-Modus

```bash
python3 chat_with_db_receipts.py
```

- Lädt alle Quittungen aus der Datenbank
- Formatiert sie als Kontext für das LLM
- Startet interaktiven Chat

### Mit RAG-Integration (empfohlen)

```bash
python3 chat_with_db_receipts.py --load-rag
```

- Lädt Quittungen auch in ChromaDB (RAG-System)
- Ermöglicht **semantische Suche**
- Bessere Kontext-Erkennung

### Limitierte Anzahl (für Tests)

```bash
python3 chat_with_db_receipts.py --limit 10
```

Nur die ersten 10 Quittungen laden.

## 💬 Beispiel-Fragen

### Finanz-Fragen:

```
❓ Wie viel habe ich insgesamt ausgegeben?
❓ Was ist der Durchschnittsbetrag pro Quittung?
❓ Zeige mir meine Top-5 Ausgaben
❓ Wie viel für Kategorie "Meals"?
```

### Audit-Fragen:

```
❓ Welche Quittungen haben Rechenfehler?
❓ Zeige mir alle verdächtigen Quittungen
❓ Gibt es Duplikate?
❓ Welche Quittungen fehlt die MwSt?
```

### Detail-Fragen:

```
❓ Was habe ich bei Deutsche Bahn gekauft?
❓ Zeige mir alle Alkohol-Käufe
❓ Was waren die teuersten Quittungen?
❓ Wie viel habe ich in Oktober ausgegeben?
```

## 🔧 Wie es funktioniert

### 1. Datenbank → Kontext

```
SQLite DB
  ↓
Quittungen laden
  ↓
Als strukturierten Text formatieren
  ↓
An LLM als Kontext senden
```

### 2. LLM-Verarbeitung

```
Deine Frage
  ↓
LLM erhält:
  - Deine Frage
  - Alle Quittungen als Kontext
  - Chat-History
  ↓
Generiert natürliche Antwort
```

### 3. RAG-Modus (--load-rag)

```
SQLite DB
  ↓
Quittungen → RAG-Format konvertieren
  ↓
In ChromaDB speichern (Vektoren)
  ↓
Semantische Suche möglich
  ↓
Nur relevante Quittungen als Kontext
```

## 📊 Was wird angezeigt?

### Beispiel-Output:

```
💬 CHAT MIT LOKALEM LLM
============================================================
📊 50 Quittungen geladen

❓ Deine Frage: Wie viel habe ich insgesamt ausgegeben?

🤔 Denke nach...

🤖 Antwort:
Basierend auf den Daten aus den 50 Quittungen habe ich 
einen Gesamtbetrag von 9.484,42 EUR ausgegeben.

Die durchschnittliche Quittung beträgt 189,69 EUR.

Die Quittungen decken einen Zeitraum vom 31. August 2025 
bis zum 28. November 2025 ab.
------------------------------------------------------------
```

## 🎯 Unterschiede: Mit vs. Ohne RAG

### Ohne RAG (`--load-rag` nicht verwendet):
- ✅ Alle Quittungen werden als Kontext gesendet
- ✅ LLM sieht komplette Daten
- ⚠️  Bei vielen Quittungen → längerer Kontext
- ⚠️  LLM muss selbst filtern/suchen

### Mit RAG (`--load-rag`):
- ✅ Semantische Suche findet relevante Quittungen
- ✅ Nur passende Quittungen als Kontext
- ✅ Schneller, präziser
- ✅ Bessere Ergebnisse bei spezifischen Fragen

## 🐛 Troubleshooting

### Problem: "Ollama ist nicht verfügbar"

**Lösung:**
```bash
# Terminal 1: Ollama starten
ollama serve

# Terminal 2: Modelle prüfen
ollama list

# Falls nötig: Modell installieren
ollama pull llama3.2
```

### Problem: "Keine Quittungen gefunden"

**Lösung:**
```bash
# Testdaten generieren
cd backend
python3 seed.py
```

### Problem: LLM antwortet nicht richtig

**Mögliche Ursachen:**
1. **Falsches Modell:** Stelle sicher, dass `llama3.2` installiert ist
2. **Zu viele Quittungen:** Nutze `--limit 10` für Tests
3. **Unklare Frage:** Stelle spezifische Fragen

## 💡 Tipps

### 1. Spezifische Fragen stellen

**Besser:**
- "Wie viel habe ich bei Deutsche Bahn ausgegeben?"
- "Zeige mir Quittungen mit Rechenfehlern"

**Weniger gut:**
- "Zeig mir Quittungen" (zu allgemein)
- "Was ist hier?" (unklar)

### 2. Schrittweise Fragen

```
1. "Wie viele Quittungen habe ich?"
2. "Wie viel insgesamt?"
3. "Was war die teuerste?"
```

### 3. Kombiniere mit Analyse-Tool

```bash
# Erst: Statistiken anzeigen
python3 analyze_receipts.py

# Dann: Spezifische Fragen stellen
python3 chat_with_db_receipts.py --load-rag
```

## 🔄 Workflow-Beispiel

```bash
# 1. Testdaten generieren
cd backend && python3 seed.py

# 2. Statistiken anzeigen
cd ../ai-backend && python3 analyze_receipts.py

# 3. Ollama starten (Terminal 1)
ollama serve

# 4. Chat starten (Terminal 2)
cd ai-backend
python3 chat_with_db_receipts.py --load-rag

# 5. Fragen stellen
❓ Wie viel insgesamt?
❓ Zeige mir verdächtige Quittungen
❓ Was war meine größte Ausgabe?
```

## 📚 Weitere Ressourcen

- `ANALYSE_ANLEITUNG.md` - Datenbank-Analyse
- `INTEGRATION_PARTNER2.md` - API-Dokumentation
- `LLM_TEST_ANLEITUNG.md` - LLM-Testing Details

---

**Viel Spaß beim Chatten mit deinen Quittungen! 🤖💬**


