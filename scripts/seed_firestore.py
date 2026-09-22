"""Seed Firestore with sample pantry inventory items for Smart Chef & Pantry Concierge."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-0b819a9381db"
COLLECTION_NAME = "pantry_inventory"

SEEDED_ITEMS = [
    {"item_name": "eggs", "category": "dairy", "quantity": 12, "unit": "count", "expiry_days": 14},
    {"item_name": "baby spinach", "category": "produce", "quantity": 1, "unit": "bag", "expiry_days": 4},
    {"item_name": "cheddar cheese", "category": "dairy", "quantity": 8, "unit": "oz", "expiry_days": 20},
    {"item_name": "extra virgin olive oil", "category": "pantry", "quantity": 1, "unit": "bottle", "expiry_days": 90},
    {"item_name": "garlic", "category": "produce", "quantity": 3, "unit": "heads", "expiry_days": 30},
    {"item_name": "chicken breasts", "category": "protein", "quantity": 2, "unit": "lbs", "expiry_days": 3},
    {"item_name": "canned chickpeas", "category": "pantry", "quantity": 2, "unit": "cans", "expiry_days": 180},
    {"item_name": "jasmine rice", "category": "pantry", "quantity": 2, "unit": "lbs", "expiry_days": 180},
]

def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    coll = db.collection(COLLECTION_NAME)

    for item in SEEDED_ITEMS:
        doc_id = item["item_name"].lower().replace(" ", "_")
        coll.document(doc_id).set(item)
        print(f"Seeded: {item['item_name']} ({item['quantity']} {item['unit']})")

    print(f"Successfully seeded {len(SEEDED_ITEMS)} pantry items into '{COLLECTION_NAME}'!")

if __name__ == "__main__":
    seed()
