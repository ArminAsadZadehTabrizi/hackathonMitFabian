"""
Ollama Service - Local LLM for receipt extraction and chat responses.
"""
import ollama
import base64
import json
import re
from typing import Optional, Dict
from pathlib import Path

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_CHAT_MODEL
from constants import LLM_OPTIONS, VISION_OPTIONS, detect_language
from models.receipt import Receipt, LineItem
from services.receipt_validator import validate_receipt, fix_receipt

# Initialize Ollama client
client = ollama.Client(host=OLLAMA_HOST)


# =============================================================================
# PROMPTS
# =============================================================================

EXTRACTION_PROMPT = """Du bist ein Experte für das Auslesen von Quittungen und Rechnungen.
Analysiere dieses Bild einer Quittung sehr sorgfältig und extrahiere ALLE sichtbaren Informationen.

Antworte NUR mit einem gültigen JSON-Objekt in diesem EXAKTEN Format:
{
    "vendor_name": "Name des Geschäfts",
    "vendor_address": "Adresse oder null",
    "date": "YYYY-MM-DD",
    "total": 123.45,
    "subtotal": 100.00,
    "tax": 23.45,
    "tax_rate": 19.0,
    "currency": "EUR",
    "payment_method": "Karte/Bar oder null",
    "line_items": [
        {"description": "Produktname", "quantity": 1, "unit_price": 10.00, "total_price": 10.00, "category": "Kategorie"}
    ],
    "category": "Restaurant/Supermarkt/Tankstelle/Bürobedarf/Elektronik/Sonstiges"
}

REGELN:
1. Zahlen als Dezimalzahlen (12.50 nicht "12,50")
2. Datum im ISO-Format YYYY-MM-DD
3. Falls nicht lesbar, setze null
4. JSON muss gültig sein - keine Kommentare!

WICHTIG: Antworte NUR mit dem JSON-Objekt!
"""

SYSTEM_PROMPT_DE = """Du bist ein Experte für Finanz-Auditing und ein KI-Assistent für ein Buchhaltungssystem.

DEINE ROLLE: Beantworte Fragen zu Quittungen und Ausgaben präzise und hilfreich.

VERFÜGBARE DATEN:
{context}
{calculations}

ANWEISUNGEN:
1. SPRACHE: Antworte auf Deutsch
2. NUTZE VORBERECHNETE ZAHLEN: Der "Gesamtbetrag/Total" Wert wurde bereits von Python berechnet und ist 100% korrekt. NUTZE IHN DIREKT.
3. FORMAT: Beginne mit der Hauptantwort (Gesamtbetrag), dann Details
4. WÄHRUNG: Formatiere als X.XXX,XX€ (z.B. 11.456,97€)
5. SEI SPEZIFISCH: Nenne immer die genaue Anzahl und Beträge

BEISPIEL-ANTWORTEN:
- "Die Gesamtausgaben betragen 11.456,97€ aus 50 Quittungen."
- "Ich habe 6 Quittungen von Saturn gefunden mit einem Gesamtbetrag von 1.694,20€."

Wenn du "Gesamtbetrag/Total: 1234.56€" in den Berechnungen siehst, sollte deine Antwort "1.234,56€" enthalten - nicht selbst rechnen!
"""

SYSTEM_PROMPT_EN = """You are an expert financial auditor AI assistant for a small business bookkeeping system.

YOUR ROLE: Answer questions about receipts and expenses accurately and helpfully.

AVAILABLE DATA:
{context}
{calculations}

INSTRUCTIONS:
1. LANGUAGE: Respond in English
2. USE PRE-CALCULATED NUMBERS: The "Gesamtbetrag/Total" value is already calculated by Python and is 100% accurate. USE IT DIRECTLY.
3. FORMAT: Start with the main answer (total amount), then provide details
4. CURRENCY: Format as €X,XXX.XX (e.g., €11,456.97)
5. BE SPECIFIC: Always mention the exact count and amounts

EXAMPLE RESPONSES:
- "The total spending is €11,456.97 across 50 receipts."
- "I found 6 receipts from Saturn totaling €1,694.20."

If you see "Gesamtbetrag/Total: 1234.56€" in the calculations, your answer should include "€1,234.56" - do not recalculate!
"""


# =============================================================================
# EXTRACTION
# =============================================================================

async def extract_receipt_from_image(
    image_path: Optional[str] = None,
    image_base64: Optional[str] = None
) -> Receipt:
    """
    Extract receipt data from an image using Ollama Vision Model.
    
    Args:
        image_path: Path to image file
        image_base64: Base64-encoded image data
    
    Returns:
        Receipt object with extracted data
    """
    # Prepare image
    if image_path:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
    elif image_base64:
        image_data = image_base64
    else:
        raise ValueError("Either image_path or image_base64 must be provided")
    
    # Call Ollama with retry logic
    data = None
    response_text = None
    
    for attempt in range(3):
        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT, "images": [image_data]}],
                options=VISION_OPTIONS
            )
            
            response_text = response["message"]["content"]
            data = _parse_json_response(response_text)
            break
            
        except json.JSONDecodeError as e:
            if attempt < 2:
                print(f"⚠️  JSON Parse Error (attempt {attempt + 1}/3): {e}")
                continue
            raise
    
    if data is None:
        raise ValueError("Could not parse JSON after multiple attempts")
    
    return _create_receipt_from_data(data, image_path, response_text)


def _parse_json_response(response_text: str) -> dict:
    """Extract and parse JSON from LLM response."""
    # Try different JSON extraction methods
    patterns = [
        r'```json\s*(.*?)\s*```',  # Markdown code block
        r'```\s*(.*?)\s*```',       # Code block without language
        r'\{.*\}'                    # Raw JSON
    ]
    
    json_str = None
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            json_str = match.group(1) if '```' in pattern else match.group(0)
            break
    
    if not json_str:
        json_str = response_text
    
    # Clean up JSON string
    json_str = json_str.strip()
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)  # Remove comments
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    return json.loads(json_str)


def _create_receipt_from_data(data: dict, image_path: Optional[str], raw_text: str) -> Receipt:
    """Create Receipt object from parsed data."""
    try:
        line_items = [LineItem(**item) for item in data.get("line_items", [])]
        
        receipt = Receipt(
            vendor_name=data.get("vendor_name", "Unbekannt"),
            vendor_address=data.get("vendor_address"),
            date=data.get("date"),
            total=float(data.get("total", 0)) if data.get("total") else None,
            subtotal=float(data.get("subtotal")) if data.get("subtotal") else None,
            tax=float(data.get("tax")) if data.get("tax") else None,
            tax_rate=float(data.get("tax_rate")) if data.get("tax_rate") else None,
            currency=data.get("currency", "EUR"),
            payment_method=data.get("payment_method"),
            line_items=line_items,
            category=data.get("category"),
            image_path=image_path,
            raw_text=raw_text
        )
        
        # Validate and auto-fix
        validation = validate_receipt(receipt)
        if validation["warnings"]:
            print(f"⚠️  Validation warnings: {len(validation['warnings'])}")
        
        return fix_receipt(receipt, apply_corrections=True)
        
    except Exception as e:
        print(f"❌ Error processing receipt: {e}")
        return Receipt(vendor_name="Parse Error", total=0, raw_text=raw_text, image_path=image_path)


# =============================================================================
# CHAT
# =============================================================================

async def generate_chat_response(
    question: str,
    context: str,
    history: list = None,
    calculations: Optional[Dict] = None
) -> str:
    """
    Generate a chat response based on context (RAG).
    
    Args:
        question: User's question
        context: Relevant receipt data as context
        history: Chat history
        calculations: Pre-calculated precise numbers from Python
    
    Returns:
        Generated response text
    """
    history = history or []
    
    # Format calculations for prompt
    calc_text = _format_calculations(calculations) if calculations else ""
    
    # Select language-appropriate prompt
    lang = detect_language(question)
    prompt_template = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT_DE
    system_prompt = prompt_template.format(context=context, calculations=calc_text)
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})
    
    # Log request
    print(f"🤖 Ollama Request: {OLLAMA_CHAT_MODEL}")
    print(f"   Question: {question[:100]}...")
    print(f"   Context: {len(context)} chars, Calculations: {calculations is not None}")
    
    try:
        response = client.chat(model=OLLAMA_CHAT_MODEL, messages=messages, options=LLM_OPTIONS)
        answer = response["message"]["content"]
        print(f"✅ Ollama Response: {len(answer)} chars")
        return answer
    except Exception as e:
        print(f"❌ Ollama Error: {e}")
        raise


def _format_calculations(calculations: Dict) -> str:
    """Format calculations for inclusion in prompt."""
    result = calculations.get('result', {})
    
    lines = [
        "\n" + "=" * 60,
        "📊 PRECISE CALCULATIONS (Python - 100% correct!)",
        "=" * 60,
        "",
        "🎯 MAIN RESULTS (use EXACTLY these numbers!):",
        f"   Gesamtbetrag/Total: {result.get('total', 0)}€",
        f"   Anzahl/Count: {result.get('count', 0)} receipts",
        f"   Durchschnitt/Average: {result.get('average', 0)}€",
        f"   Filter: {result.get('filter', 'all receipts')}",
        ""
    ]
    
    # Min/Max
    min_data = result.get('min', {})
    max_data = result.get('max', {})
    if min_data.get('vendor'):
        lines.append(f"📉 Smallest: {min_data.get('total', 0)}€ ({min_data.get('vendor')})")
    if max_data.get('vendor'):
        lines.append(f"📈 Largest: {max_data.get('total', 0)}€ ({max_data.get('vendor')})")
    lines.append("")
    
    # Top Vendors
    if top_vendors := result.get('top_vendors', []):
        lines.append("🏪 Top Vendors:")
        for i, v in enumerate(top_vendors[:3], 1):
            lines.append(f"   {i}. {v.get('vendor')}: {v.get('total')}€")
        lines.append("")
    
    # Top Categories
    if top_cats := result.get('top_categories', []):
        lines.append("📁 Top Categories:")
        for i, c in enumerate(top_cats[:3], 1):
            lines.append(f"   {i}. {c.get('category')}: {c.get('total')}€")
        lines.append("")
    
    # Receipt details
    if receipts := result.get('receipts', []):
        lines.append(f"📄 Receipt Details (first {min(len(receipts), 10)}):")
        for i, r in enumerate(receipts[:10], 1):
            flags = []
            if r.get('flags', {}).get('duplicate'): flags.append('⚠️DUP')
            if r.get('flags', {}).get('suspicious'): flags.append('🚨SUS')
            if r.get('flags', {}).get('missing_vat'): flags.append('❌VAT')
            if r.get('flags', {}).get('math_error'): flags.append('🔢ERR')
            flag_str = ' '.join(flags) if flags else ''
            lines.append(f"   {i}. {r.get('vendor')}: {r.get('total')}€ ({r.get('category', '')}) {flag_str}")
        lines.append("")
    
    lines.extend([
        "=" * 60,
        "⚠️ USE THE NUMBER AFTER 'Gesamtbetrag/Total:' AS YOUR ANSWER!",
        "=" * 60
    ])
    
    return "\n".join(lines)


# =============================================================================
# STATUS
# =============================================================================

def check_ollama_status() -> dict:
    """Check if Ollama is running and which models are available."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            models = []
            for m in data.get("models", []):
                if isinstance(m, dict) and "name" in m:
                    models.append(m["name"])
                elif isinstance(m, str):
                    models.append(m)
            
            return {
                "status": "online",
                "models": models,
                "host": OLLAMA_HOST,
                "chat_model": OLLAMA_CHAT_MODEL,
                "vision_model": OLLAMA_MODEL
            }
        
        return {"status": "error", "error": f"HTTP {response.status_code}"}
        
    except Exception as e:
        return {"status": "offline", "error": str(e), "host": OLLAMA_HOST}
