#!/usr/bin/env python3
"""
🧪 Interaktive Tests für das RAG System
Führt verschiedene Szenarien durch und zeigt die Ergebnisse
"""
import requests
import json
from typing import Dict, Any

API_BASE = "http://localhost:8000"


def print_section(title: str):
    """Druckt eine Sektion mit Trennlinie"""
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60)


def test_health():
    """Test 1: Health Check"""
    print_section("Health Check")
    
    r = requests.get(f"{API_BASE}/api/health")
    data = r.json()
    
    print(f"✅ Status: {data['status']}")
    print(f"✅ Ollama: {data['ollama']['status']}")
    print(f"✅ RAG Backend: {data['rag']['backend']}")
    print(f"✅ Dokumente in DB: {data['rag']['total_documents']}")
    
    return data['status'] == 'healthy'


def test_demo_data():
    """Test 2: Demo-Daten laden"""
    print_section("Demo-Daten laden")
    
    r = requests.post(f"{API_BASE}/api/ingest/demo")
    data = r.json()
    
    print(f"✅ {data['message']}")
    print(f"✅ Dokumente: {data['stats']['total_documents']}")
    
    return True


def test_search(query: str, limit: int = 3):
    """Test 3: Semantische Suche"""
    print_section(f"Suche: '{query}'")
    
    r = requests.get(f"{API_BASE}/api/search", params={
        "query": query,
        "limit": limit
    })
    data = r.json()
    
    print(f"📊 Gefunden: {data['total']} Ergebnisse\n")
    
    for i, result in enumerate(data['results'], 1):
        meta = result['metadata']
        print(f"{i}. {meta['vendor_name']}")
        print(f"   💰 {meta['total']}€ | 📅 {meta['date']} | 📂 {meta['category']}")
        print(f"   📈 Relevanz: {result['similarity']:.1%}")
        print()
    
    return len(data['results']) > 0


def test_chat(question: str):
    """Test 4: RAG Chat"""
    print_section(f"Chat: '{question}'")
    
    r = requests.post(
        f"{API_BASE}/api/chat",
        json={"message": question, "history": []},
        timeout=60
    )
    data = r.json()
    
    print(f"🤖 Antwort:\n{data['response']}\n")
    print(f"📚 Basierend auf {data['sources_used']} Quittungen")
    
    return True


def test_analytics():
    """Test 5: Analytics"""
    print_section("Analytics - Ausgaben nach Kategorie")
    
    r = requests.get(f"{API_BASE}/api/analytics/categories")
    data = r.json()
    
    categories = data.get('spending_by_category', {})
    
    print("📊 Ausgaben nach Kategorie:\n")
    for category, total in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category:20s}: {total:8.2f}€")
    
    return True


def test_rag_flow():
    """Test 6: Kompletter RAG Flow demonstrieren"""
    print_section("RAG Flow Demonstration")
    
    print("1️⃣  User fragt: 'Wie viel für Alkohol?'")
    print("2️⃣  System sucht relevante Quittungen...")
    
    # Suche
    r = requests.get(f"{API_BASE}/api/search", params={
        "query": "Alkohol",
        "limit": 3
    })
    search_results = r.json()
    
    print(f"\n   ✅ Gefunden: {len(search_results['results'])} relevante Quittungen")
    for i, result in enumerate(search_results['results'], 1):
        print(f"      {i}. {result['metadata']['vendor_name']} - {result['metadata']['total']}€")
    
    print("\n3️⃣  System formatiert Kontext für LLM...")
    print("4️⃣  LLM generiert Antwort...")
    
    # Chat
    r = requests.post(
        f"{API_BASE}/api/chat",
        json={"message": "Wie viel habe ich für Alkohol ausgegeben?", "history": []},
        timeout=60
    )
    chat_response = r.json()
    
    print(f"\n5️⃣  Antwort:\n   {chat_response['response'][:200]}...")
    
    return True


def main():
    """Hauptfunktion - Führt alle Tests durch"""
    print("\n" + "🚀" * 30)
    print("🧪 INTERAKTIVE RAG SYSTEM TESTS")
    print("🚀" * 30)
    
    tests = []
    
    # Test 1: Health
    tests.append(("Health Check", test_health()))
    
    # Test 2: Demo Daten
    tests.append(("Demo-Daten laden", test_demo_data()))
    
    # Test 3: Verschiedene Suchen
    print_section("Semantische Suche Tests")
    tests.append(("Suche: Restaurant", test_search("Restaurant", limit=2)))
    tests.append(("Suche: Alkohol", test_search("Alkohol", limit=2)))
    tests.append(("Suche: höchste Ausgaben", test_search("höchste Ausgaben", limit=3)))
    
    # Test 4: Chat
    print_section("RAG Chat Tests")
    tests.append(("Chat: Alkohol", test_chat("Wie viel habe ich für Alkohol ausgegeben?")))
    tests.append(("Chat: Top Ausgaben", test_chat("Was waren meine Top 3 Ausgaben?")))
    tests.append(("Chat: Kategorien", test_chat("In welchen Kategorien habe ich am meisten ausgegeben?")))
    
    # Test 5: Analytics
    tests.append(("Analytics", test_analytics()))
    
    # Test 6: RAG Flow
    tests.append(("RAG Flow Demo", test_rag_flow()))
    
    # Zusammenfassung
    print_section("Test-Zusammenfassung")
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n📊 {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("\n🎉 Alle Tests erfolgreich! Das RAG System funktioniert perfekt!")
    else:
        print("\n⚠️  Einige Tests fehlgeschlagen. Bitte prüfen.")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Fehler: Server läuft nicht!")
        print("   Starte den Server mit: python main.py")
    except Exception as e:
        print(f"❌ Fehler: {e}")


