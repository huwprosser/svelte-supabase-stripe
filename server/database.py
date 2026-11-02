from pymongo import MongoClient

from config import MONGODB_DB, MONGODB_URI

mongo = MongoClient(MONGODB_URI)
db = mongo[MONGODB_DB]
users = db["users"]
stripe_events = db["stripe_events"]
telemetry_actions = db["telemetry_actions"]

config = db["config"]
