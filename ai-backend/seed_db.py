"""
Seed Script - Generates test data for the AI-Backend database.
Creates 50 receipts with various audit scenarios.
"""
from datetime import datetime, timedelta
from sqlmodel import Session, delete, select
import random

from services.database import engine, init_db
from models.db_models import ReceiptDB, LineItemDB
from services.audit import run_audit
from constants import VENDOR_CATEGORIES, SUSPICIOUS_ITEMS, get_category_for_vendor


# =============================================================================
# CONFIGURATION
# =============================================================================

VENDORS = list(VENDOR_CATEGORIES.keys())

CLEAN_ITEMS = [
    "Office Chair", "Desk Lamp", "Notebook", "Pen Set", "Coffee",
    "Sandwich", "Water Bottle", "USB Cable", "Monitor", "Keyboard",
    "Mouse Pad", "Printer Paper", "Stapler", "File Folders", "Headphones",
    "Train Ticket", "Taxi Fare", "Hotel Stay", "Flight Ticket", "Fuel",
    "Laptop Stand", "Webcam", "Extension Cord", "Backpack", "Desk Organizer"
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def random_date_last_90_days() -> datetime:
    """Generate a random datetime in the last 90 days."""
    days_ago = random.randint(0, 90)
    hours_ago = random.randint(0, 23)
    return datetime.now() - timedelta(days=days_ago, hours=hours_ago)


def create_line_items(count: int, items_list: list) -> tuple[list, float]:
    """Create random line items and return total."""
    items = []
    total = 0.0
    
    for _ in range(count):
        amount = round(random.uniform(5.0, 150.0), 2)
        total += amount
        items.append(LineItemDB(description=random.choice(items_list), amount=amount))
    
    return items, total


# =============================================================================
# RECEIPT GENERATORS
# =============================================================================

def generate_clean_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a clean receipt with correct math and no suspicious items."""
    vendor = random.choice(VENDORS)
    items, total = create_line_items(random.randint(1, 5), CLEAN_ITEMS)
    tax_amount = round(total * 0.19, 2)
    
    receipt = ReceiptDB(
        vendor_name=vendor,
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=tax_amount,
        currency="EUR",
        category=get_category_for_vendor(vendor)
    )
    return receipt, items


def generate_suspicious_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt with suspicious items (alcohol/tobacco)."""
    # Suspicious items typically come from grocery stores, gas stations, or bars
    suspicious_vendors = ["Rewe", "Shell", "Pub Express", "Aldi"]
    vendor = random.choice(suspicious_vendors)
    
    items = []
    total = 0.0
    
    # Add suspicious item
    suspicious_amount = round(random.uniform(10.0, 50.0), 2)
    total += suspicious_amount
    items.append(LineItemDB(description=random.choice(SUSPICIOUS_ITEMS), amount=suspicious_amount))
    
    # Add clean items
    for _ in range(random.randint(1, 3)):
        amount = round(random.uniform(5.0, 30.0), 2)
        total += amount
        items.append(LineItemDB(description=random.choice(CLEAN_ITEMS), amount=amount))
    
    receipt = ReceiptDB(
        vendor_name=vendor,
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=round(total * 0.19, 2),
        currency="EUR",
        category=get_category_for_vendor(vendor)
    )
    return receipt, items


def generate_math_error_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt where line items don't add up to total."""
    vendor = random.choice(VENDORS)
    items, total = create_line_items(random.randint(2, 5), CLEAN_ITEMS)
    
    # Introduce math error
    wrong_total = round(total + random.uniform(5.0, 20.0), 2)
    
    receipt = ReceiptDB(
        vendor_name=vendor,
        date=random_date_last_90_days(),
        total_amount=wrong_total,
        tax_amount=round(wrong_total * 0.19, 2),
        currency="EUR",
        category=get_category_for_vendor(vendor)
    )
    return receipt, items


def generate_missing_vat_receipt() -> tuple[ReceiptDB, list[LineItemDB]]:
    """Generate a receipt with missing VAT (tax_amount = 0)."""
    vendor = random.choice(VENDORS)
    items, total = create_line_items(random.randint(1, 4), CLEAN_ITEMS)
    
    receipt = ReceiptDB(
        vendor_name=vendor,
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=0.0,  # Missing VAT!
        currency="EUR",
        category=get_category_for_vendor(vendor)
    )
    return receipt, items


# =============================================================================
# MAIN SEEDING FUNCTION
# =============================================================================

def seed_database():
    """
    Create 50 random receipts with various audit scenarios.
    
    Distribution:
    - 10% Suspicious items
    - 10% Math errors
    - 10% Missing VAT
    - 70% Clean receipts
    """
    print("📊 Initializing database...")
    init_db()
    
    with Session(engine) as session:
        # Clear existing data
        if session.exec(select(ReceiptDB)).first():
            print("⚠️  Database has existing data. Clearing...")
            session.exec(delete(LineItemDB))
            session.exec(delete(ReceiptDB))
            session.commit()
        
        print("\n🌱 Generating 50 receipts...")
        
        # Receipt generators by type
        generators = {
            "suspicious": (generate_suspicious_receipt, 0.10),
            "math_error": (generate_math_error_receipt, 0.20),
            "missing_vat": (generate_missing_vat_receipt, 0.30),
            "clean": (generate_clean_receipt, 1.0)
        }
        
        for i in range(50):
            # Select generator based on probability
            rand = random.random()
            for gen_name, (gen_func, threshold) in generators.items():
                if rand < threshold:
                    receipt, items = gen_func()
                    break
            
            # Save receipt
            session.add(receipt)
            session.flush()
            
            # Link and save line items
            for item in items:
                item.receipt_id = receipt.id
                session.add(item)
            
            # Run audit
            receipt = run_audit(receipt, items, session)
            
            if (i + 1) % 10 == 0:
                print(f"  ✓ {i + 1}/50 receipts created...")
        
        session.commit()
        
        # Print statistics
        all_receipts = session.exec(select(ReceiptDB)).all()
        total_amount = sum(r.total_amount for r in all_receipts)
        
        print(f"\n✅ Successfully created {len(all_receipts)} receipts!")
        print(f"\n📈 Statistics:")
        print(f"  💰 Total: {total_amount:.2f} EUR")
        print(f"  🍺 Suspicious: {sum(1 for r in all_receipts if r.flag_suspicious)}")
        print(f"  🔢 Math errors: {sum(1 for r in all_receipts if r.flag_math_error)}")
        print(f"  📋 Missing VAT: {sum(1 for r in all_receipts if r.flag_missing_vat)}")
        print(f"  📑 Duplicates: {sum(1 for r in all_receipts if r.flag_duplicate)}")


if __name__ == "__main__":
    print("=" * 50)
    print("🌱 Small Business Auto-Bookkeeper - Seed Script")
    print("=" * 50)
    seed_database()
    print("\n✅ Database seeding complete!")
    print("=" * 50)
