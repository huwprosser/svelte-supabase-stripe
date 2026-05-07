import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

ROOT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")
sys.path.insert(0, str(SERVER_DIR))

from config import MONGODB_DB, MONGODB_URI

COLLECTIONS = ["users", "stripe_events", "telemetry_actions"]
INDEXES = {
    "users": [
        ([("email", ASCENDING)], {"name": "email_1"}),
        (
            [("stripe_customer_id", ASCENDING)],
            {
                "name": "stripe_customer_id_1",
                "sparse": True,
            },
        ),
        (
            [("stripe_subscription_id", ASCENDING)],
            {
                "name": "stripe_subscription_id_1",
                "sparse": True,
            },
        ),
    ],
    "stripe_events": [
        ([("type", ASCENDING)], {"name": "type_1"}),
        ([("processed", ASCENDING)], {"name": "processed_1"}),
        ([("created", DESCENDING)], {"name": "created_-1"}),
    ],
    "telemetry_actions": [
        ([("action", ASCENDING)], {"name": "action_1"}),
        ([("user_id", ASCENDING)], {"name": "user_id_1"}),
        ([("session_id", ASCENDING)], {"name": "session_id_1"}),
        ([("timestamp", DESCENDING)], {"name": "timestamp_-1"}),
        (
            [("user_id", ASCENDING), ("action", ASCENDING), ("timestamp", DESCENDING)],
            {"name": "user_id_1_action_1_timestamp_-1"},
        ),
        (
            [("user_id", ASCENDING), ("session_id", ASCENDING), ("timestamp", DESCENDING)],
            {"name": "user_id_1_session_id_1_timestamp_-1"},
        ),
    ],
}


def ensure_collections(db):
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            db.create_collection(name)
            print(f"created collection: {name}")
        else:
            print(f"collection exists: {name}")


def ensure_indexes(db):
    for collection_name, indexes in INDEXES.items():
        collection = db[collection_name]
        for keys, options in indexes:
            name = collection.create_index(keys, **options)
            print(f"ensured index: {collection_name}.{name}")


def main():
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]
    ensure_collections(db)
    ensure_indexes(db)
    print(f"MongoDB initialized: {MONGODB_DB}")


if __name__ == "__main__":
    main()
