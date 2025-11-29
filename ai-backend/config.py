"""
Konfiguration für den AI-Backend
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Ollama Konfiguration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2-vision")  # Für Bild-Analyse
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")  # Für Chat

# ChromaDB Konfiguration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = "receipts"

# Embedding Model (läuft lokal!)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Schnell und gut für Deutsch/Englisch

# CORD Dataset Pfad
CORD_DATA_PATH = os.getenv("CORD_DATA_PATH", "./data/cord")

# API Settings
API_HOST = "0.0.0.0"
API_PORT = 8000

