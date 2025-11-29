"""
Seed Script - Generiert Testdaten für die Datenbank.

Adaptiert von backend/seed.py für das integrierte ai-backend.
Generiert 50 Quittungen mit verschiedenen Audit-Szenarien.
"""

import sys
from pathlib import Path

# Füge backend/ zum Path hinzu um die Seed-Funktionen zu nutzen
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from seed import create_random_data
    print("🌱 Starte Datenbank-Seeding...")
    print("   (Dies kann einen Moment dauern)\n")
    
    create_random_data()
    
    print("\n✅ Datenbank erfolgreich mit Testdaten gefüllt!")
    print("\n📊 Nächste Schritte:")
    print("   1. Analysiere die Daten:")
    print("      python analyze_receipts.py")
    print("   2. Oder exportiere als JSON/CSV:")
    print("      python analyze_receipts.py --export-json receipts.json")
    print("      python analyze_receipts.py --export-csv receipts.csv")
    print("   3. Oder nutze die API:")
    print("      curl http://localhost:8000/api/receipts")
    
except ImportError as e:
    print(f"❌ Fehler: Konnte seed.py nicht importieren")
    print(f"   Details: {e}")
    print("\n💡 Alternative: Nutze das Backend direkt:")
    print(f"   cd {backend_path}")
    print("   python seed.py")
    sys.exit(1)


