"""
Seed Script - Generiert Testdaten für die AI-Backend Datenbank.
Generiert 50 Quittungen mit verschiedenen Audit-Szenarien.
"""

from datetime import datetime, timedelta
import random
from sqlmodel import Session, delete, select

from services.database import engine, init_db
from models.db_models import ReceiptDB, LineItemDB
from services.audit import run_audit


# Configuration
VENDORS = ["Amazon", "Deutsche Bahn", "Lufthansa", "Rewe", "Shell", "MediaMarkt", "Pub Express", "IKEA", "Saturn", "Aldi"]
CATEGORIES = ["Travel", "Meals", "Office Supplies", "Hardware", "Software", "Groceries", "Fuel", "Electronics"]

CLEAN_ITEMS = [
    "Office Chair", "Desk Lamp", "Notebook", "Pen Set", "Coffee",
    "Sandwich", "Water Bottle", "USB Cable", "Monitor", "Keyboard",
    "Mouse Pad", "Printer Paper", "Stapler", "File Folders", "Headphones",
    "Train Ticket", "Taxi Fare", "Hotel Stay", "Flight Ticket", "Fuel",
    "Laptop Stand", "Webcam", "Extension Cord", "Backpack", "Desk Organizer"
]

SUSPICIOUS_ITEMS = [
    "Beer", "Wine", "Vodka", "Whiskey", "Cigarettes", 
    "Tobacco", "Rum", "Champagne", "Gin", "Tequila"
]


def random_date_last_90_days() -> datetime:
    """Generate a random datetime in the last 90 days."""
    days_ago = random.randint(0, 90)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    return datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


def generate_clean_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a clean receipt with correct math and no suspicious items."""
    num_items = random.randint(1, 5)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(5.0, 150.0), 2)
        total += amount
        items.append(LineItemDB(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    tax_amount = round(total * 0.19, 2)  # 19% German VAT
    
    receipt = ReceiptDB(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=tax_amount,
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def generate_suspicious_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt with suspicious items (alcohol/tobacco)."""
    num_items = random.randint(2, 4)
    items = []
    total = 0.0
    
    # Add at least one suspicious item
    suspicious_amount = round(random.uniform(10.0, 50.0), 2)
    total += suspicious_amount
    items.append(LineItemDB(
        description=random.choice(SUSPICIOUS_ITEMS),
        amount=suspicious_amount
    ))
    
    # Add some clean items
    for _ in range(num_items - 1):
        amount = round(random.uniform(5.0, 30.0), 2)
        total += amount
        items.append(LineItemDB(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    tax_amount = round(total * 0.19, 2)
    
    receipt = ReceiptDB(
        vendor_name=random.choice(["Rewe", "Shell", "Pub Express", "Aldi"]),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=tax_amount,
        currency="EUR",
        category="Meals"
    )
    
    return receipt, items


def generate_math_error_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt where line items don't add up to total."""
    num_items = random.randint(2, 5)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(10.0, 100.0), 2)
        total += amount
        items.append(LineItemDB(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    # Introduce math error by changing total
    wrong_total = round(total + random.uniform(5.0, 20.0), 2)
    tax_amount = round(wrong_total * 0.19, 2)
    
    receipt = ReceiptDB(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=wrong_total,
        tax_amount=tax_amount,
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def generate_missing_vat_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt with missing VAT (tax_amount = 0)."""
    num_items = random.randint(1, 4)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(10.0, 100.0), 2)
        total += amount
        items.append(LineItemDB(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    receipt = ReceiptDB(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=0.0,  # Missing VAT!
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def seed_database():
    """
    Create 50 random receipts with various audit scenarios.
    
    Distribution:
    - 10% Suspicious items
    - 10% Math errors
    - 10% Missing VAT
    - 70% Clean receipts
    """
    # Initialize database
    print("📊 Initialisiere Datenbank...")
    init_db()
    
    with Session(engine) as session:
        # Check if data already exists
        existing = session.exec(select(ReceiptDB)).first()
        if existing:
            print("⚠️  Datenbank enthält bereits Daten. Lösche alte Daten...")
            session.exec(delete(LineItemDB))
            session.exec(delete(ReceiptDB))
            session.commit()
            print("✅ Alte Daten gelöscht")
        
        # Generate receipts
        print("\n🌱 Generiere 50 Quittungen...")
        
        receipts_created = 0
        
        # Create receipts with different audit scenarios
        for i in range(50):
            # Determine receipt type based on distribution
            rand = random.random()
            
            if rand < 0.10:  # 10% suspicious
                receipt, items = generate_suspicious_receipt()
                receipt_type = "Suspicious"
            elif rand < 0.20:  # 10% math error
                receipt, items = generate_math_error_receipt()
                receipt_type = "Math Error"
            elif rand < 0.30:  # 10% missing VAT
                receipt, items = generate_missing_vat_receipt()
                receipt_type = "Missing VAT"
            else:  # 70% clean
                receipt, items = generate_clean_receipt()
                receipt_type = "Clean"
            
            # Add receipt to session and flush to get ID
            session.add(receipt)
            session.flush()
            
            # Link line items to receipt
            for item in items:
                item.receipt_id = receipt.id
                session.add(item)
            
            # Run audit to set flags
            receipt = run_audit(receipt, items, session)
            
            receipts_created += 1
            
            # Print progress every 10 receipts
            if receipts_created % 10 == 0:
                print(f"  ✓ {receipts_created}/50 Quittungen erstellt...")
        
        # Commit all changes
        session.commit()
        
        print(f"\n✅ Erfolgreich {receipts_created} Quittungen erstellt!")
        
        # Print statistics
        print("\n📈 Statistiken:")
        
        # Query all receipts properly
        all_receipts = session.exec(select(ReceiptDB)).all()
        
        # Count flags
        flagged_suspicious = len([r for r in all_receipts if r.flag_suspicious])
        flagged_math = len([r for r in all_receipts if r.flag_math_error])
        flagged_vat = len([r for r in all_receipts if r.flag_missing_vat])
        flagged_duplicate = len([r for r in all_receipts if r.flag_duplicate])
        
        # Calculate totals
        total_amount = sum(r.total_amount for r in all_receipts)
        
        print(f"  📝 Gesamt Quittungen: {len(all_receipts)}")
        print(f"  💰 Gesamtbetrag: {total_amount:.2f} EUR")
        print(f"  🍺 Verdächtige Items: {flagged_suspicious}")
        print(f"  🔢 Rechenfehler: {flagged_math}")
        print(f"  📋 Fehlende MwSt: {flagged_vat}")
        print(f"  📑 Duplikate: {flagged_duplicate}")


if __name__ == "__main__":
    print("=" * 50)
    print("🌱 Small Business Auto-Bookkeeper - Seed Script")
    print("=" * 50)
    print()
    seed_database()
    print()
    print("=" * 50)
    print("✅ Datenbank-Seeding abgeschlossen!")
    print("=" * 50)

