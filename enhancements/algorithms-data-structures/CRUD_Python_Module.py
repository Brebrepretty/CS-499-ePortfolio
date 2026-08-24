# CRUD_Python_Module.py
# CS-340 Module Four, Five & Six CRUD Python Module

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class CRUD:
    """CRUD operations for AAC database"""

    def __init__(self, username=None, password=None):
        """
        Initialize MongoDB connection.
        Uses credentials if provided to meet CS-340 authentication requirements.
        Falls back to local connection if credentials are not required.
        """
        try:
            if username and password:
                uri = f"mongodb://{username}:{password}@localhost:27017/"
            else:
                uri = "mongodb://localhost:27017/"

            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.database = self.client["aac"]
            self.collection = self.database["animals"]

            print("CRUD object created")

        except PyMongoError as e:
            print("Connection Error:", e)

    # -----------------------------
    # CREATE
    # -----------------------------
    def create(self, data):
        """Insert a document into the collection"""
        if data is not None:
            try:
                self.collection.insert_one(data)
                return True
            except PyMongoError as e:
                print("Insert Error:", e)
                return False
        return False

    # -----------------------------
    # READ
    # -----------------------------
    def read(self, query):
        """Query documents from the collection"""
        try:
            return list(self.collection.find(query))
        except PyMongoError as e:
            print("Read Error:", e)
            return []

    # -----------------------------
    # UPDATE
    # -----------------------------
    def update(self, query, new_values):
        """Update documents in the collection"""
        try:
            result = self.collection.update_many(query, {"$set": new_values})
            return result.modified_count
        except PyMongoError as e:
            print("Update Error:", e)
            return 0

    # -----------------------------
    # DELETE
    # -----------------------------
    def delete(self, query):
        """Delete documents from the collection"""
        try:
            result = self.collection.delete_many(query)
            return result.deleted_count
        except PyMongoError as e:
            print("Delete Error:", e)
            return 0
