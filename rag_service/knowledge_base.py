"""
Knowledge Base Manager — Loads, manages, and ingests agricultural data into the RAG pipeline.
"""

import os
import json
from typing import Optional


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

CATEGORIES = [
    "crop_diseases",
    "fertilizers",
    "government_schemes",
    "weather_advisory",
    "market_prices",
    "farming_practices",
]


def load_initial_data() -> list[dict]:
    """Load all JSON data files from the data directory."""
    all_documents = []

    if not os.path.exists(DATA_DIR):
        print(f"[KB] Data directory not found: {DATA_DIR}")
        return all_documents

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                docs = json.load(f)

            if isinstance(docs, list):
                # Validate each document has required fields
                valid_docs = []
                for doc in docs:
                    if _validate_document(doc):
                        valid_docs.append(doc)
                    else:
                        print(f"[KB] Skipping invalid document in {filename}: {doc.get('id', 'unknown')}")

                all_documents.extend(valid_docs)
                print(f"[KB] Loaded {len(valid_docs)} documents from {filename}")
            else:
                print(f"[KB] Warning: {filename} does not contain a JSON array")

        except json.JSONDecodeError as e:
            print(f"[KB] JSON parse error in {filename}: {e}")
        except Exception as e:
            print(f"[KB] Error loading {filename}: {e}")

    print(f"[KB] Total documents loaded: {len(all_documents)}")
    return all_documents


def _validate_document(doc: dict) -> bool:
    """Validate that a document has the minimum required fields."""
    required_fields = ["id", "content"]
    for field in required_fields:
        if field not in doc or not doc[field]:
            return False
    return True


def add_custom_data(data: list[dict], category: str = "custom") -> tuple[int, list[str]]:
    """
    Validate and prepare custom data for ingestion.

    Args:
        data: List of documents to add
        category: Category for the new documents

    Returns:
        Tuple of (valid_count, list of error messages)
    """
    errors = []
    valid_docs = []

    for i, doc in enumerate(data):
        # Ensure required fields
        if "content" not in doc or not doc["content"].strip():
            errors.append(f"Document {i}: missing 'content' field")
            continue

        # Auto-generate ID if not provided
        if "id" not in doc:
            doc["id"] = f"custom_{category}_{i}"

        # Set category
        doc["category"] = doc.get("category", category)

        # Set title if not provided
        if "title" not in doc:
            doc["title"] = doc["content"][:80] + "..."

        valid_docs.append(doc)

    # Save to file
    if valid_docs:
        save_path = os.path.join(DATA_DIR, f"{category}_custom.json")
        try:
            # Load existing if present
            existing = []
            if os.path.exists(save_path):
                with open(save_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing.extend(valid_docs)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            print(f"[KB] Saved {len(valid_docs)} custom documents to {save_path}")
        except Exception as e:
            errors.append(f"Failed to save custom data: {str(e)}")

    return len(valid_docs), errors


def get_categories() -> list[dict]:
    """Get all available knowledge categories with document counts."""
    category_info = []

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                docs = json.load(f)

            cat_name = filename.replace(".json", "").replace("_", " ").title()
            category_info.append({
                "filename": filename,
                "category": cat_name,
                "document_count": len(docs) if isinstance(docs, list) else 0,
            })
        except Exception:
            pass

    return category_info


def get_sample_data() -> dict:
    """Return sample data format for the /upload-data endpoint."""
    return {
        "description": "Upload agricultural knowledge data to enhance the AI assistant",
        "format": {
            "category": "string (e.g., 'crop_diseases', 'fertilizers', 'farming_practices')",
            "documents": [
                {
                    "id": "string (unique identifier, auto-generated if not provided)",
                    "title": "string (short title, auto-generated from content if not provided)",
                    "content": "string (REQUIRED - the main knowledge content, should be detailed)",
                    "category": "string (optional, defaults to parent category)",
                }
            ],
        },
        "example": {
            "category": "crop_diseases",
            "documents": [
                {
                    "id": "cd_custom_001",
                    "title": "Papaya Ring Spot Virus",
                    "content": "Papaya Ring Spot Virus (PRSV) is transmitted by aphids and causes ring-shaped spots on fruits. Leaves show mosaic pattern and distortion. No cure exists. Remove infected plants. Use resistant varieties like Arka Surya. Control aphids with neem oil spray.",
                }
            ],
        },
    }
