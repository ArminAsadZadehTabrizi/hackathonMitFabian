# 🧭 Navigations-Hilfe

## 📍 Projekt-Struktur

Das Projekt liegt hier:
```
/Users/tolga/.cursor/worktrees/Finanz/SbkgK/
├── ai-backend/      ← AI-Backend mit LLM
├── backend/         ← Datenbank-Backend
└── ...
```

## 🚀 Schnellstart-Befehle

### 1. Zum Projekt navigieren

```bash
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK
```

**Oder** mit relativer Navigation (vom Home):
```bash
cd .cursor/worktrees/Finanz/SbkgK
```

### 2. Testdaten generieren

```bash
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/backend
python3 seed.py
```

### 3. Quittungen analysieren

```bash
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/ai-backend
python3 analyze_receipts.py
```

### 4. Chat mit LLM starten

```bash
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/ai-backend
python3 chat_with_db_receipts.py --load-rag
```

## 💡 Tipp: Alias erstellen

Füge zu deiner `~/.zshrc` hinzu:

```bash
alias finanz='cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK'
alias finanz-backend='cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/backend'
alias finanz-ai='cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/ai-backend'
```

Dann einfach:
```bash
finanz          # Zum Projekt
finanz-backend  # Zum Backend
finanz-ai       # Zum AI-Backend
```

## 📋 Vollständiger Workflow

```bash
# 1. Zum Projekt
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK

# 2. Testdaten generieren
cd backend && python3 seed.py

# 3. Analysieren
cd ../ai-backend && python3 analyze_receipts.py

# 4. Ollama starten (Terminal 1)
ollama serve

# 5. Chat starten (Terminal 2)
cd /Users/tolga/.cursor/worktrees/Finanz/SbkgK/ai-backend
python3 chat_with_db_receipts.py --load-rag
```

