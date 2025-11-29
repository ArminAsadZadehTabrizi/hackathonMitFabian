"""
Seed script to populate the database with test data.

Generates 50 receipts with realistic data and audit cases:
- 10% Suspicious items (alcohol/tobacco)
- 10% Math errors
- 10% Missing VAT
- Rest are clean receipts
"""

from datetime import datetime, timedelta
import random
from sqlmodel import Session, delete, select

from database import engine, init_db
from models import Receipt, LineItem
from audit import run_audit


# Configuration
VENDORS = ["Amazon", "Deutsche Bahn", "Lufthansa", "Rewe", "Shell", "MediaMarkt", "Pub Express"]
CATEGORIES = ["Travel", "Meals", "Office Supplies", "Hardware", "Software"]

CLEAN_ITEMS = [
    "Office Chair", "Desk Lamp", "Notebook", "Pen Set", "Coffee",
    "Sandwich", "Water Bottle", "USB Cable", "Monitor", "Keyboard",
    "Mouse Pad", "Printer Paper", "Stapler", "File Folders", "Headphones",
    "Train Ticket", "Taxi Fare", "Hotel Stay", "Flight Ticket", "Fuel"
]

SUSPICIOUS_ITEMS = [
    "Beer", "Wine", "Vodka", "Whiskey", "Cigarettes", 
    "Tobacco", "Rum", "Champagne"
]


def random_date_last_90_days() -> datetime:
    """Generate a random datetime in the last 90 days."""
    days_ago = random.randint(0, 90)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    return datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


def generate_clean_receipt() -> tuple[Receipt, list[LineItem]]:
    """Generate a clean receipt with correct math and no suspicious items."""
    num_items = random.randint(1, 5)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(5.0, 150.0), 2)
        total += amount
        items.append(LineItem(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    tax_amount = round(total * 0.19, 2)  # 19% German VAT
    
    receipt = Receipt(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=tax_amount,
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def generate_suspicious_receipt() -> tuple[Receipt, list[LineItem]]:
    """Generate a receipt with suspicious items (alcohol/tobacco)."""
    num_items = random.randint(2, 4)
    items = []
    total = 0.0
    
    # Add at least one suspicious item
    suspicious_amount = round(random.uniform(10.0, 50.0), 2)
    total += suspicious_amount
    items.append(LineItem(
        description=random.choice(SUSPICIOUS_ITEMS),
        amount=suspicious_amount
    ))
    
    # Add some clean items
    for _ in range(num_items - 1):
        amount = round(random.uniform(5.0, 30.0), 2)
        total += amount
        items.append(LineItem(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    tax_amount = round(total * 0.19, 2)
    
    receipt = Receipt(
        vendor_name=random.choice(["Rewe", "Shell", "Pub Express"]),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=tax_amount,
        currency="EUR",
        category="Meals"
    )
    
    return receipt, items


def generate_math_error_receipt() -> tuple[Receipt, list[LineItem]]:
    """Generate a receipt where line items don't add up to total."""
    num_items = random.randint(2, 5)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(10.0, 100.0), 2)
        total += amount
        items.append(LineItem(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    # Introduce math error by changing total
    wrong_total = round(total + random.uniform(5.0, 20.0), 2)
    tax_amount = round(wrong_total * 0.19, 2)
    
    receipt = Receipt(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=wrong_total,
        tax_amount=tax_amount,
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def generate_missing_vat_receipt() -> tuple[Receipt, list[LineItem]]:
    """Generate a receipt with missing VAT (tax_amount = 0)."""
    num_items = random.randint(1, 4)
    items = []
    total = 0.0
    
    for _ in range(num_items):
        amount = round(random.uniform(10.0, 100.0), 2)
        total += amount
        items.append(LineItem(
            description=random.choice(CLEAN_ITEMS),
            amount=amount
        ))
    
    receipt = Receipt(
        vendor_name=random.choice(VENDORS),
        date=random_date_last_90_days(),
        total_amount=round(total, 2),
        tax_amount=0.0,  # Missing VAT!
        currency="EUR",
        category=random.choice(CATEGORIES)
    )
    
    return receipt, items


def create_random_data():
    """
    Create 50 random receipts with various audit scenarios.
    
    Distribution:
    - 10% Suspicious items
    - 10% Math errors
    - 10% Missing VAT
    - 70% Clean receipts
    """
    # Initialize database
    init_db()
    
    with Session(engine) as session:
        # Delete all existing data
        print("Deleting existing data...")
        session.exec(delete(LineItem))
        session.exec(delete(Receipt))
        session.commit()
        print("Existing data deleted")
        
        # Generate receipts
        print("\nGenerating 50 receipts...")
        
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
                print(f"  Created {receipts_created}/50 receipts...")
        
        # Commit all changes
        session.commit()
        
        print(f"\nSuccessfully created {receipts_created} receipts!")
        
        # Print statistics
        print("\nStatistics:")
        
        # Query all receipts properly
        all_receipts = session.exec(select(Receipt)).all()
        
        # Count flags
        flagged_suspicious = len([r for r in all_receipts if r.flag_suspicious])
        flagged_math = len([r for r in all_receipts if r.flag_math_error])
        flagged_vat = len([r for r in all_receipts if r.flag_missing_vat])
        flagged_duplicate = len([r for r in all_receipts if r.flag_duplicate])
        
        print(f"  Total Receipts: {len(all_receipts)}")
        print(f"  Suspicious Items: {flagged_suspicious}")
        print(f"  Math Errors: {flagged_math}")
        print(f"  Missing VAT: {flagged_vat}")
        print(f"  Duplicates: {flagged_duplicate}")


if __name__ == "__main__":
    print("Seeding database with test data...\n")
    create_random_data()
    print("\nDatabase seeding complete!")
