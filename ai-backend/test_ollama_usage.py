"""
Test Script um zu zeigen, dass Ollama verwendet wird
"""
import requests
import json

def test_ollama_usage():
    """Testet ob Ollama korrekt verwendet wird."""
    print("="*60)
    print("🔍 Test: Wird Ollama verwendet?")
    print("="*60)
    
    # 1. Prüfe Ollama Status
    print("\n1️⃣  Ollama Status prüfen...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"   ✅ Ollama läuft auf localhost:11434")
            print(f"   ✅ Verfügbare Models: {[m.get('name', 'unknown') for m in models]}")
        else:
            print(f"   ❌ Ollama nicht erreichbar (HTTP {response.status_code})")
            return
    except Exception as e:
        print(f"   ❌ Ollama nicht erreichbar: {e}")
        return
    
    # 2. Prüfe Backend Health
    print("\n2️⃣  Backend Health prüfen...")
    try:
        response = requests.get("http://localhost:8000/api/health")
        health = response.json()
        ollama_status = health.get("ollama", {})
        print(f"   ✅ Backend läuft")
        print(f"   ✅ Ollama Status: {ollama_status.get('status')}")
        print(f"   ✅ Chat Model: {ollama_status.get('chat_model')}")
        print(f"   ✅ Vision Model: {ollama_status.get('vision_model')}")
    except Exception as e:
        print(f"   ❌ Backend nicht erreichbar: {e}")
        return
    
    # 3. Test Chat Query (mit Logging)
    print("\n3️⃣  Test Chat Query...")
    print("   Sende Query an /api/chat/query...")
    print("   (Prüfe Backend-Logs für Ollama-Details)")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/chat/query",
            json={"query": "Wie viel habe ich insgesamt ausgegeben?"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Antwort erhalten:")
            print(f"   {data.get('answer', '')[:200]}...")
            print(f"   💰 Total Amount: {data.get('totalAmount', 0)} EUR")
        else:
            print(f"   ❌ Fehler: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
    
    print("\n" + "="*60)
    print("💡 Tipp: Schau in die Backend-Logs für detaillierte")
    print("   Ollama-Request/Response-Informationen!")
    print("="*60)

if __name__ == "__main__":
    test_ollama_usage()

