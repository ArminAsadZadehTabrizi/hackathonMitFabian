#!/usr/bin/env python3
"""
🧪 Test Script für die AI Pipeline
Führe dieses Script aus um alle Komponenten zu testen.
"""
import asyncio
import requests
import json

API_BASE = "http://localhost:8000"


def test_health():
    """Testet den Health Endpoint"""
    print("\n🏥 Test: Health Check")
    print("-" * 40)
    
    try:
        r = requests.get(f"{API_BASE}/api/health")
        data = r.json()
        
        print(f"Status: {data['status']}")
        print(f"Ollama: {data['ollama']['status']}")
        
        if data['ollama']['status'] == 'online':
            print(f"Verfügbare Modelle: {', '.join(data['ollama']['models'])}")
        
        print(f"RAG Dokumente: {data['rag']['total_documents']}")
        
        return data['ollama']['status'] == 'online'
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False


def test_demo_data():
    """Lädt Demo-Daten"""
    print("\n📦 Test: Demo-Daten laden")
    print("-" * 40)
    
    try:
        r = requests.post(f"{API_BASE}/api/ingest/demo")
        data = r.json()
        print(f"✅ {data['message']}")
        print(f"Dokumente in DB: {data['stats']['total_documents']}")
        return True
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False


def test_search():
    """Testet die semantische Suche"""
    print("\n🔍 Test: Semantische Suche")
    print("-" * 40)
    
    queries = [
        "Restaurant Essen",
        "Tankstelle Benzin",
        "Bürobedarf Elektronik"
    ]
    
    for query in queries:
        try:
            r = requests.get(f"{API_BASE}/api/search", params={"query": query, "limit": 3})
            data = r.json()
            print(f"\nSuche: '{query}'")
            for result in data['results'][:2]:
                print(f"  → {result['metadata']['vendor_name']}: {result['metadata']['total']}€")
        except Exception as e:
            print(f"❌ Fehler: {e}")
            return False
    
    return True


def test_chat():
    """Testet den Chat mit RAG"""
    print("\n💬 Test: Chat mit RAG")
    print("-" * 40)
    
    questions = [
        "Wie viel habe ich insgesamt für Essen ausgegeben?",
        "Zeige mir die höchsten Ausgaben",
        "Wo habe ich Alkohol gekauft?"
    ]
    
    for question in questions:
        print(f"\n❓ Frage: {question}")
        try:
            r = requests.post(
                f"{API_BASE}/api/chat",
                json={"message": question, "history": []},
                timeout=60  # LLM kann dauern
            )
            data = r.json()
            print(f"🤖 Antwort: {data['response'][:200]}...")
            print(f"   (Basierend auf {data['sources_used']} Quittungen)")
        except Exception as e:
            print(f"❌ Fehler: {e}")
            return False
    
    return True


def test_extraction():
    """Testet die Bild-Extraktion (benötigt ein Testbild)"""
    print("\n📸 Test: Bild-Extraktion")
    print("-" * 40)
    print("⚠️  Übersprungen - benötigt ein Testbild")
    print("   Nutze: POST /api/extract/upload mit einem Quittungsbild")
    return True


def main():
    print("=" * 50)
    print("🧪 AI Pipeline Test Suite")
    print("=" * 50)
    
    # Tests ausführen
    results = []
    
    # 1. Health Check
    if not test_health():
        print("\n❌ Health Check fehlgeschlagen!")
        print("   Stelle sicher, dass:")
        print("   1. Der Server läuft: python main.py")
        print("   2. Ollama läuft: ollama serve")
        return
    results.append(("Health Check", True))
    
    # 2. Demo Daten
    results.append(("Demo Data", test_demo_data()))
    
    # 3. Search
    results.append(("Search", test_search()))
    
    # 4. Chat
    results.append(("Chat", test_chat()))
    
    # 5. Extraction
    results.append(("Extraction", test_extraction()))
    
    # Zusammenfassung
    print("\n" + "=" * 50)
    print("📊 Zusammenfassung")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    passed = sum(1 for _, p in results if p)
    print(f"\n{passed}/{len(results)} Tests bestanden")


if __name__ == "__main__":
    main()

