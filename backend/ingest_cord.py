"""
Ingest real receipt data from CORD-v2 dataset into the API.

Loads the first 50 receipts from the CORD dataset and sends them
to the /api/ingest endpoint.
"""

import json
import requests
from datetime import datetime
from datasets import load_dataset


# Configuration
API_URL = "http://localhost:8000/api/ingest"
NUM_RECEIPTS = 200  # Import more receipts to get better data


def parse_date(date_str):
    """
    Parse date string from CORD dataset.
    
    Try multiple formats, return today's date if parsing fails.
    """
    if not date_str:
        return datetime.now().isoformat()
    
    # Common date formats in CORD dataset
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except (ValueError, AttributeError):
            continue
    
    # If all parsing fails, return current datetime
    print(f"  Warning: Could not parse date '{date_str}', using current date")
    return datetime.now().isoformat()


def extract_receipt_data(entry):
    """
    Extract receipt data from CORD dataset entry.
    
    Args:
        entry: Dataset entry with ground_truth field
        
    Returns:
        dict: Receipt data in API format, or None if extraction fails
    """
    try:
        # Parse ground_truth JSON
        if isinstance(entry['ground_truth'], str):
            gt = json.loads(entry['ground_truth'])
        else:
            gt = entry['ground_truth']
        
        # Extract vendor name
        vendor_name = "Unknown Vendor"
        if 'gt_parse' in gt and 'store_info' in gt['gt_parse']:
            store_info = gt['gt_parse']['store_info']
            if 'name' in store_info and 'text' in store_info['name']:
                vendor_name = store_info['name']['text']
        
        # Extract date
        date = None
        if 'gt_parse' in gt:
            # Try payment_info.date first
            if 'payment_info' in gt['gt_parse'] and 'date' in gt['gt_parse']['payment_info']:
                date_obj = gt['gt_parse']['payment_info']['date']
                if 'text' in date_obj:
                    date = date_obj['text']
            
            # Fallback to store_info.date
            if not date and 'store_info' in gt['gt_parse'] and 'date' in gt['gt_parse']['store_info']:
                date_obj = gt['gt_parse']['store_info']['date']
                if 'text' in date_obj:
                    date = date_obj['text']
        
        date = parse_date(date)
        
        # Extract total amount
        total_amount = 0.0
        if 'gt_parse' in gt and 'total' in gt['gt_parse']:
            total_info = gt['gt_parse']['total']
            if 'total_price' in total_info and 'price' in total_info['total_price']:
                try:
                    total_amount = float(total_info['total_price']['price'])
                except (ValueError, TypeError):
                    total_amount = 0.0
        
        # Extract tax amount
        tax_amount = 0.0
        if 'gt_parse' in gt and 'total' in gt['gt_parse']:
            total_info = gt['gt_parse']['total']
            if 'tax' in total_info and 'price' in total_info['tax']:
                try:
                    tax_amount = float(total_info['tax']['price'])
                except (ValueError, TypeError):
                    tax_amount = 0.0
        
        # Extract menu items
        items = []
        items_total = 0.0
        
        if 'gt_parse' in gt and 'menu' in gt['gt_parse']:
            for menu_item in gt['gt_parse']['menu']:
                description = "Unknown Item"
                amount = 0.0
                
                # Get item name
                if 'nm' in menu_item and 'text' in menu_item['nm']:
                    description = menu_item['nm']['text']
                elif 'name' in menu_item and 'text' in menu_item['name']:
                    description = menu_item['name']['text']
                
                # Get item price - try multiple paths
                if 'price' in menu_item:
                    price_obj = menu_item['price']
                    if isinstance(price_obj, dict):
                        if 'price' in price_obj:
                            try:
                                amount = float(price_obj['price'])
                            except (ValueError, TypeError):
                                pass
                        elif 'value' in price_obj:
                            try:
                                amount = float(price_obj['value'])
                            except (ValueError, TypeError):
                                pass
                    elif isinstance(price_obj, (int, float)):
                        amount = float(price_obj)
                
                # Also try 'cnt' (count) and 'price' separately
                if amount == 0.0 and 'cnt' in menu_item:
                    cnt_obj = menu_item['cnt']
                    if isinstance(cnt_obj, dict) and 'price' in cnt_obj:
                        try:
                            amount = float(cnt_obj['price'])
                        except (ValueError, TypeError):
                            pass
                
                # Only add items with valid data
                if description and amount > 0:
                    items.append({
                        "description": description,
                        "amount": amount
                    })
                    items_total += amount
        
        # If total_amount is 0 but we have items, use items total
        if total_amount == 0.0 and items_total > 0:
            total_amount = items_total
        
        # If no items found but we have a total, create a dummy item
        if not items and total_amount > 0:
            items.append({
                "description": "Total Purchase",
                "amount": total_amount
            })
        
        # Build receipt data
        receipt_data = {
            "vendor_name": vendor_name,
            "date": date,
            "total_amount": total_amount,
            "tax_amount": tax_amount,
            "currency": "USD",  # CORD dataset is mostly in USD
            "category": "Meals",  # Most CORD receipts are from restaurants
            "items": items
        }
        
        return receipt_data
        
    except Exception as e:
        print(f"  Error extracting receipt data: {e}")
        return None


def ingest_cord_data():
    """
    Load CORD dataset and ingest receipts into the API.
    """
    print("Loading CORD-v2 dataset...")
    print("(This may take a moment on first run)\n")
    
    # Load dataset
    try:
        dataset = load_dataset("naver-clova-ix/cord-v2", split="train")
        print(f"Dataset loaded: {len(dataset)} total receipts\n")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("Make sure you have installed: pip install datasets")
        return
    
    # Process first N receipts
    success_count = 0
    error_count = 0
    
    for i, entry in enumerate(dataset):
        if i >= NUM_RECEIPTS:
            break
        
        print(f"Processing receipt {i+1}/{NUM_RECEIPTS}...")
        
        # Extract receipt data
        receipt_data = extract_receipt_data(entry)
        
        if not receipt_data:
            print(f"  Skipped (extraction failed)")
            error_count += 1
            continue
        
        # Send to API
        try:
            response = requests.post(API_URL, json=receipt_data, timeout=10)
            print(f"  Imported Receipt {i+1}: [Status {response.status_code}]")
            
            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
                print(f"  Error response: {response.text[:100]}")
        except requests.exceptions.ConnectionError:
            print(f"  ERROR: Could not connect to API at {API_URL}")
            print(f"  Make sure the server is running: uvicorn main:app --reload")
            error_count += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            error_count += 1
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total processed: {NUM_RECEIPTS}")
    print(f"Successfully imported: {success_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    print("="*50)
    print("CORD Dataset Ingestion Script")
    print("="*50)
    print()
    
    ingest_cord_data()
    
    print("\nDone!")
