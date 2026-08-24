# CRUD_Python_Module.py
# CS 499 Milestone Two
# Enhancement One: Software Design and Engineering
# Samari Robinson Camacho

from typing import Any, Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class CRUD:
    """
    Provides create, read, update, and delete operations
    for the AAC animal shelter MongoDB database.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: str = "localhost",
        port: int = 27017,
        database_name: str = "aac",
        collection_name: str = "animals"
    ):
        """
        Initialize and verify the MongoDB connection.

        Authentication is optional so this module can connect to the
        local MongoDB Community Server on the new development computer.

        Args:
            username: Optional MongoDB username.
            password: Optional MongoDB password.
            host: MongoDB server hostname.
            port: MongoDB server port.
            database_name: MongoDB database name.
            collection_name: MongoDB collection name.

        Raises:
            ValueError: If configuration values are invalid.
            ConnectionError: If MongoDB cannot be reached.
        """

        if bool(username) != bool(password):
            raise ValueError(
                "Username and password must both be provided or both omitted."
            )

        if not isinstance(port, int) or port <= 0:
            raise ValueError("Port must be a positive integer.")

        if not isinstance(database_name, str) or not database_name.strip():
            raise ValueError("Database name cannot be empty.")

        if not isinstance(collection_name, str) or not collection_name.strip():
            raise ValueError("Collection name cannot be empty.")

        if username and password:
            uri = (
                f"mongodb://{username}:{password}"
                f"@{host}:{port}/?authSource=admin"
            )
        else:
            uri = f"mongodb://{host}:{port}/"

        try:
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000
            )

            # Verify that MongoDB is running immediately.
            self.client.admin.command("ping")

            self.database = self.client[database_name]
            self.collection = self.database[collection_name]

            print(
                f"Connected to MongoDB database '{database_name}' "
                f"and collection '{collection_name}'."
            )

        except PyMongoError as error:
            raise ConnectionError(
                f"MongoDB connection failed: {error}"
            ) from error

    # ---------------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------------

    @staticmethod
    def _validate_document(
        document: dict[str, Any],
        argument_name: str
    ) -> None:
        """Verify that an argument is a dictionary."""

        if not isinstance(document, dict):
            raise TypeError(
                f"{argument_name} must be a dictionary."
            )

    @staticmethod
    def _validate_nonempty_document(
        document: dict[str, Any],
        argument_name: str
    ) -> None:
        """Verify that an argument is a nonempty dictionary."""

        CRUD._validate_document(document, argument_name)

        if not document:
            raise ValueError(
                f"{argument_name} cannot be empty."
            )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(self, data: dict[str, Any]) -> bool:
        """
        Insert one document into the animal collection.

        Returns:
            True if the insert is acknowledged; otherwise False.
        """

        try:
            self._validate_nonempty_document(data, "data")

            result = self.collection.insert_one(data)

            return result.acknowledged

        except (TypeError, ValueError) as error:
            print(f"Create validation error: {error}")
            return False

        except PyMongoError as error:
            print(f"Create database error: {error}")
            return False

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------

    def read(
        self,
        query: Optional[dict[str, Any]] = None,
        projection: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve documents matching a MongoDB query.

        Args:
            query: MongoDB filter. An empty query returns all records.
            projection: Optional fields to include or exclude.

        Returns:
            A list containing the matching documents.
        """

        if query is None:
            query = {}

        try:
            self._validate_document(query, "query")

            if projection is not None:
                self._validate_document(
                    projection,
                    "projection"
                )

            cursor = self.collection.find(
                query,
                projection
            )

            return list(cursor)

        except (TypeError, ValueError) as error:
            print(f"Read validation error: {error}")
            return []

        except PyMongoError as error:
            print(f"Read database error: {error}")
            return []

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        query: dict[str, Any],
        new_values: dict[str, Any],
        update_many: bool = False
    ) -> int:
        """
        Update one matching document by default.

        Set update_many=True only when multiple matching documents
        should intentionally be changed.

        Returns:
            The number of modified documents.
        """

        try:
            self._validate_nonempty_document(
                query,
                "query"
            )

            self._validate_nonempty_document(
                new_values,
                "new_values"
            )

            update_document = {
                "$set": new_values
            }

            if update_many:
                result = self.collection.update_many(
                    query,
                    update_document
                )
            else:
                result = self.collection.update_one(
                    query,
                    update_document
                )

            return result.modified_count

        except (TypeError, ValueError) as error:
            print(f"Update validation error: {error}")
            return 0

        except PyMongoError as error:
            print(f"Update database error: {error}")
            return 0

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        query: dict[str, Any],
        delete_many: bool = False
    ) -> int:
        """
        Delete one matching document by default.

        Set delete_many=True only when multiple matching documents
        should intentionally be deleted.

        Returns:
            The number of deleted documents.
        """

        try:
            self._validate_nonempty_document(
                query,
                "query"
            )

            if delete_many:
                result = self.collection.delete_many(query)
            else:
                result = self.collection.delete_one(query)

            return result.deleted_count

        except (TypeError, ValueError) as error:
            print(f"Delete validation error: {error}")
            return 0

        except PyMongoError as error:
            print(f"Delete database error: {error}")
            return 0

    # ---------------------------------------------------------
    # CONNECTION CLEANUP
    # ---------------------------------------------------------

    def close(self) -> None:
        """Close the MongoDB client connection."""

        if hasattr(self, "client"):
            self.client.close()