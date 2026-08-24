# CRUD_Python_Module.py
# CS 499 Milestone Four
# Enhancement Three: Databases
# Samari Robinson Camacho

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Iterable, Optional
from urllib.parse import quote_plus

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError


class CRUD:
    """Secure, validated CRUD access for the AAC animal shelter database."""

    REQUIRED_CREATE_FIELDS = {"animal_id", "animal_type", "breed"}
    IMMUTABLE_FIELDS = {"_id", "animal_id"}
    ALLOWED_UPDATE_FIELDS = {
        "age_upon_outcome",
        "age_upon_outcome_in_weeks",
        "animal_type",
        "breed",
        "color",
        "date_of_birth",
        "datetime",
        "location_lat",
        "location_long",
        "monthyear",
        "name",
        "outcome_subtype",
        "outcome_type",
        "sex_upon_outcome",
    }
    BLOCKED_QUERY_OPERATORS = {"$where", "$function", "$accumulator"}

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        auth_source: Optional[str] = None,
        create_indexes: bool = True,
    ) -> None:
        """Initialize MongoDB from arguments or environment variables.

        Environment variables keep credentials out of source code:
        MONGODB_USERNAME, MONGODB_PASSWORD, MONGODB_HOST, MONGODB_PORT,
        MONGODB_DATABASE, MONGODB_COLLECTION, and MONGODB_AUTH_SOURCE.
        """
        username = username if username is not None else os.getenv("MONGODB_USERNAME")
        password = password if password is not None else os.getenv("MONGODB_PASSWORD")
        host = host or os.getenv("MONGODB_HOST", "localhost")
        port = port if port is not None else int(os.getenv("MONGODB_PORT", "27017"))
        database_name = database_name or os.getenv("MONGODB_DATABASE", "aac")
        collection_name = collection_name or os.getenv("MONGODB_COLLECTION", "animals")
        auth_source = auth_source or os.getenv("MONGODB_AUTH_SOURCE", "admin")

        if bool(username) != bool(password):
            raise ValueError("Username and password must both be supplied or both omitted.")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("Port must be an integer from 1 through 65535.")
        for label, value in (("host", host), ("database_name", database_name), ("collection_name", collection_name)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} cannot be empty.")

        if username and password:
            uri = (
                f"mongodb://{quote_plus(username)}:{quote_plus(password)}@"
                f"{host}:{port}/?authSource={quote_plus(auth_source)}"
            )
        else:
            uri = f"mongodb://{host}:{port}/"

        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
            self.client.admin.command("ping")
            self.database = self.client[database_name]
            self.collection: Collection = self.database[collection_name]
            if create_indexes:
                self.ensure_indexes()
        except PyMongoError as error:
            raise ConnectionError(f"MongoDB connection failed: {error}") from error

    def ensure_indexes(self) -> list[str]:
        """Create indexes that improve integrity and common dashboard queries."""
        try:
            return [
                self.collection.create_index([("animal_id", ASCENDING)], unique=True, sparse=True, name="uq_animal_id"),
                self.collection.create_index([("breed", ASCENDING)], name="idx_breed"),
                self.collection.create_index([("sex_upon_outcome", ASCENDING), ("age_upon_outcome_in_weeks", ASCENDING)], name="idx_rescue_profile"),
            ]
        except PyMongoError as error:
            raise RuntimeError(f"Unable to create database indexes: {error}") from error

    @staticmethod
    def _require_dict(value: Any, name: str, allow_empty: bool = False) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError(f"{name} must be a dictionary.")
        if not allow_empty and not value:
            raise ValueError(f"{name} cannot be empty.")
        return value

    @classmethod
    def _reject_unsafe_operators(cls, value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in cls.BLOCKED_QUERY_OPERATORS:
                    raise ValueError(f"The query operator {key} is not allowed.")
                cls._reject_unsafe_operators(nested)
        elif isinstance(value, list):
            for item in value:
                cls._reject_unsafe_operators(item)

    @classmethod
    def _validate_create_document(cls, document: dict[str, Any]) -> dict[str, Any]:
        clean = deepcopy(cls._require_dict(document, "data"))
        missing = [field for field in cls.REQUIRED_CREATE_FIELDS if not str(clean.get(field, "")).strip()]
        if missing:
            raise ValueError("Missing required fields: " + ", ".join(sorted(missing)))
        clean.pop("_id", None)
        return clean

    @classmethod
    def _validate_update_fields(cls, new_values: dict[str, Any]) -> dict[str, Any]:
        clean = deepcopy(cls._require_dict(new_values, "new_values"))
        if any(str(key).startswith("$") for key in clean):
            raise ValueError("Pass field values only; update operators are not accepted.")
        forbidden = set(clean) & cls.IMMUTABLE_FIELDS
        unknown = set(clean) - cls.ALLOWED_UPDATE_FIELDS
        if forbidden:
            raise ValueError("Immutable fields cannot be updated: " + ", ".join(sorted(forbidden)))
        if unknown:
            raise ValueError("Unsupported update fields: " + ", ".join(sorted(unknown)))
        return clean

    def create(self, data: dict[str, Any]) -> bool:
        """Insert one validated animal document."""
        try:
            document = self._validate_create_document(data)
            return self.collection.insert_one(document).acknowledged
        except DuplicateKeyError:
            print("Create database error: animal_id already exists.")
            return False
        except (TypeError, ValueError, PyMongoError) as error:
            print(f"Create error: {error}")
            return False

    def read(
        self,
        query: Optional[dict[str, Any]] = None,
        projection: Optional[dict[str, Any]] = None,
        *,
        sort: Optional[Iterable[tuple[str, int]]] = None,
        skip: int = 0,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Read documents with optional projection, sorting, and pagination."""
        try:
            query = {} if query is None else self._require_dict(query, "query", allow_empty=True)
            self._reject_unsafe_operators(query)
            if projection is not None:
                self._require_dict(projection, "projection", allow_empty=True)
            if not isinstance(skip, int) or skip < 0:
                raise ValueError("skip must be a nonnegative integer.")
            if not isinstance(limit, int) or limit < 0 or limit > 5000:
                raise ValueError("limit must be between 0 and 5000.")

            cursor = self.collection.find(query, projection).skip(skip)
            if sort:
                cursor = cursor.sort(list(sort))
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        except (TypeError, ValueError, PyMongoError) as error:
            print(f"Read error: {error}")
            return []

    def update(self, query: dict[str, Any], new_values: dict[str, Any], *, update_many: bool = False) -> int:
        """Safely update one document by default; bulk update requires explicit opt-in."""
        try:
            query = self._require_dict(query, "query")
            self._reject_unsafe_operators(query)
            clean_values = self._validate_update_fields(new_values)
            operation = self.collection.update_many if update_many else self.collection.update_one
            return operation(query, {"$set": clean_values}).modified_count
        except (TypeError, ValueError, PyMongoError) as error:
            print(f"Update error: {error}")
            return 0

    def delete(self, query: dict[str, Any], *, delete_many: bool = False, confirmation: Optional[str] = None) -> int:
        """Safely delete one record; bulk deletion requires an explicit confirmation phrase."""
        try:
            query = self._require_dict(query, "query")
            self._reject_unsafe_operators(query)
            if delete_many and confirmation != "DELETE MULTIPLE RECORDS":
                raise ValueError("Bulk deletion requires confirmation='DELETE MULTIPLE RECORDS'.")
            operation = self.collection.delete_many if delete_many else self.collection.delete_one
            return operation(query).deleted_count
        except (TypeError, ValueError, PyMongoError) as error:
            print(f"Delete error: {error}")
            return 0

    def count(self, query: Optional[dict[str, Any]] = None) -> int:
        """Count matching records without loading them into memory."""
        try:
            query = {} if query is None else self._require_dict(query, "query", allow_empty=True)
            self._reject_unsafe_operators(query)
            return self.collection.count_documents(query)
        except (TypeError, ValueError, PyMongoError) as error:
            print(f"Count error: {error}")
            return 0

    def summarize_by_field(self, field: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most common values for an approved field using aggregation."""
        approved = {"animal_type", "breed", "outcome_type", "sex_upon_outcome"}
        if field not in approved:
            raise ValueError(f"field must be one of: {', '.join(sorted(approved))}")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")
        pipeline = [
            {"$match": {field: {"$nin": [None, ""]}}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0, field: "$_id", "count": 1}},
        ]
        try:
            return list(self.collection.aggregate(pipeline))
        except PyMongoError as error:
            print(f"Aggregation error: {error}")
            return []

    def close(self) -> None:
        """Close the MongoDB client connection."""
        if hasattr(self, "client"):
            self.client.close()

    def __enter__(self) -> "CRUD":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
