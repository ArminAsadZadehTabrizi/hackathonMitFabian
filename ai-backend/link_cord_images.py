"""
Verknüpft CORD Bilder mit Receipts in der Datenbank.
"""
from pathlib import Path
from sqlmodel import Session, select
from services.database import engine
from models.db_models import ReceiptDB

CORD_IMAGE_DIR = Path("./data/cord/images")

def link_cord_images():
    """Verknüpft CORD Bilder mit Receipts basierend auf der ID."""
    print("🖼️  Verknüpfe CORD Bilder mit Receipts...")
    
    with Session(engine) as session:
        # Alle Receipts holen
        receipts = session.exec(select(ReceiptDB)).all()
        print(f"📊 Gefunden: {len(receipts)} Receipts")
        
        linked_count = 0
        for receipt in receipts:
            # Versuche CORD Bild zu finden (basierend auf ID)
            # CORD Bilder sind: cord_0.png, cord_1.png, etc.
            # Wir nehmen die ersten 10 IDs und verknüpfen sie mit cord_0 bis cord_9
            if receipt.id and receipt.id <= 10:
                image_filename = f"cord_{receipt.id - 1}.png"
                image_path = CORD_IMAGE_DIR / image_filename
                
                if image_path.exists():
                    # Kopiere Bild in uploads Ordner
                    from shutil import copy2
                    upload_dir = Path("./data/uploads")
                    upload_dir.mkdir(exist_ok=True)
                    
                    dest_filename = f"receipt_{receipt.id}_{image_filename}"
                    dest_path = upload_dir / dest_filename
                    copy2(image_path, dest_path)
                    
                    # Aktualisiere Receipt
                    receipt.image_path = dest_filename
                    session.add(receipt)
                    linked_count += 1
                    print(f"  ✅ Receipt {receipt.id} → {dest_filename}")
        
        session.commit()
        print(f"\n✅ {linked_count} Bilder verknüpft!")

if __name__ == "__main__":
    link_cord_images()

