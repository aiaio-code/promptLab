"""In-memory storage for PromptLab

This module provides simple in-memory storage for prompts and collections.
In a production environment, this would be replaced with a database.
"""

from typing import Dict, List, Optional
from app.models import Prompt, Collection, get_current_time


# System collection that catches prompts whose collection is deleted
UNASSIGNED_COLLECTION_NAME = "Unassigned"


class Storage:
    """In-memory data store for prompts and collections.

    Entities are keyed by their UUID strings in plain dictionaries. All data
    is lost when the process exits; swap this class for a database-backed
    repository before deploying to production.

    Attributes:
        _prompts: Mapping of prompt id to Prompt.
        _collections: Mapping of collection id to Collection.
    """

    def __init__(self):
        """Initialize empty prompt and collection stores."""
        self._prompts: Dict[str, Prompt] = {}
        self._collections: Dict[str, Collection] = {}
    
    # ============== Prompt Operations ==============
    
    def create_prompt(self, prompt: Prompt) -> Prompt:
        """Store a new prompt.

        Args:
            prompt: The fully populated Prompt to persist.

        Returns:
            The stored Prompt, unchanged.
        """
        self._prompts[prompt.id] = prompt
        return prompt
    
    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Retrieve a prompt by its unique identifier.

        Args:
            prompt_id: The unique identifier of the prompt to retrieve.

        Returns:
            The Prompt if found, None otherwise.
        """
        return self._prompts.get(prompt_id)
    
    def get_all_prompts(self) -> List[Prompt]:
        """Retrieve every stored prompt.

        Returns:
            A list of all Prompts in insertion order (empty if none exist).
        """
        return list(self._prompts.values())
    
    def update_prompt(self, prompt_id: str, prompt: Prompt) -> Optional[Prompt]:
        """Replace a stored prompt with a new version.

        Args:
            prompt_id: The unique identifier of the prompt to replace.
            prompt: The new Prompt state to store under prompt_id.

        Returns:
            The stored Prompt if prompt_id exists, None otherwise.
        """
        if prompt_id not in self._prompts:
            return None
        self._prompts[prompt_id] = prompt
        return prompt
    
    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt by its unique identifier.

        Args:
            prompt_id: The unique identifier of the prompt to delete.

        Returns:
            True if the prompt existed and was removed, False otherwise.
        """
        if prompt_id in self._prompts:
            del self._prompts[prompt_id]
            return True
        return False
    
    # ============== Collection Operations ==============
    
    def create_collection(self, collection: Collection) -> Collection:
        """Store a new collection.

        Args:
            collection: The fully populated Collection to persist.

        Returns:
            The stored Collection, unchanged.
        """
        self._collections[collection.id] = collection
        return collection
    
    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Retrieve a collection by its unique identifier.

        Args:
            collection_id: The unique identifier of the collection to retrieve.

        Returns:
            The Collection if found, None otherwise.
        """
        return self._collections.get(collection_id)
    
    def get_all_collections(self) -> List[Collection]:
        """Retrieve every stored collection.

        Returns:
            A list of all Collections in insertion order (empty if none
            exist).
        """
        return list(self._collections.values())
    
    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection by its unique identifier.

        Prompts referencing the deleted collection are NOT modified here;
        callers are responsible for reassigning them first (see
        reassign_prompts).

        Args:
            collection_id: The unique identifier of the collection to delete.

        Returns:
            True if the collection existed and was removed, False otherwise.
        """
        if collection_id in self._collections:
            del self._collections[collection_id]
            return True
        return False
    
    def get_prompts_by_collection(self, collection_id: str) -> List[Prompt]:
        """Retrieve all prompts assigned to a collection.

        Args:
            collection_id: The unique identifier of the collection whose
                prompts should be returned.

        Returns:
            A list of Prompts whose collection_id matches (empty if none).
        """
        return [p for p in self._prompts.values() if p.collection_id == collection_id]
    
    def get_collection_by_name(self, name: str) -> Optional[Collection]:
        """Retrieve a collection by its exact display name.

        Args:
            name: The exact, case-sensitive collection name to look up.

        Returns:
            The first Collection with that name if found, None otherwise.
        """
        for collection in self._collections.values():
            if collection.name == name:
                return collection
        return None

    def get_or_create_unassigned_collection(self) -> Collection:
        """Get the system "Unassigned" collection, creating it if necessary.

        The Unassigned collection is the safety net for prompts whose own
        collection is deleted with action="unassign", so it must always
        exist and must never be deleted.

        Returns:
            The existing Unassigned Collection, or a newly created one if
            it did not exist yet.
        """
        existing = self.get_collection_by_name(UNASSIGNED_COLLECTION_NAME)
        if existing:
            return existing
        return self.create_collection(Collection(
            name=UNASSIGNED_COLLECTION_NAME,
            description="Prompts that are not assigned to a collection"
        ))

    def reassign_prompts(self, from_collection_id: str, to_collection_id: str) -> int:
        """Move all prompts from one collection to another.

        Each moved prompt's updated_at timestamp is refreshed.

        Args:
            from_collection_id: Id of the collection prompts are moved out of.
            to_collection_id: Id of the collection prompts are moved into.

        Returns:
            The number of prompts reassigned.
        """
        moved = 0
        for prompt in self._prompts.values():
            if prompt.collection_id == from_collection_id:
                prompt.collection_id = to_collection_id
                prompt.updated_at = get_current_time()
                moved += 1
        return moved

    # ============== Utility ==============
    
    def clear(self):
        """Remove all prompts and collections from the store.

        Intended for test isolation so every test starts from an empty
        state.

        Returns:
            None.
        """
        self._prompts.clear()
        self._collections.clear()


# Global storage instance
storage = Storage()
