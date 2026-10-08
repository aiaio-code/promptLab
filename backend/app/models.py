"""Pydantic models for PromptLab"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_id() -> str:
    """Generate a unique identifier for a new entity.

    Returns:
        A random UUID4 string suitable for use as a primary key.
    """
    return str(uuid4())


def get_current_time() -> datetime:
    """Get the current timestamp for record keeping.

    Returns:
        The current UTC date and time as a naive datetime.
    """
    return datetime.utcnow()


# ============== Prompt Models ==============

class PromptBase(BaseModel):
    """Shared fields for prompt payloads and the stored Prompt.

    Attributes:
        title: Short human-readable name of the prompt (1-200 characters).
        content: The prompt template text; may contain {{variable}}
            placeholders.
        description: Optional summary of the prompt's purpose
            (max 500 characters).
        collection_id: Optional id of the collection this prompt belongs to.
    """
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    collection_id: Optional[str] = None


class PromptCreate(PromptBase):
    """Payload for creating a new prompt (POST /prompts)."""


class PromptUpdate(PromptBase):
    """Payload for fully replacing a prompt (PUT /prompts/{prompt_id})."""


class PromptPatch(BaseModel):
    """Fields eligible for partial update (PATCH /prompts/{prompt_id}).

    All fields are optional: only fields explicitly provided in the
    request body are applied; omitted fields are left unchanged, while an
    explicit null clears the field.

    Attributes:
        title: New title, if provided (1-200 characters).
        content: New prompt template text, if provided.
        description: New description, or null to clear it.
        collection_id: New collection assignment, or null to unassign.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    collection_id: Optional[str] = None


class Prompt(PromptBase):
    """A stored prompt as returned by the API.

    Attributes:
        id: Unique identifier, generated automatically at creation.
        created_at: Timestamp of creation (UTC).
        updated_at: Timestamp of the last modification (UTC).
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: datetime = Field(default_factory=get_current_time)

    class Config:
        from_attributes = True


# ============== Collection Models ==============

class CollectionBase(BaseModel):
    """Shared fields for collection payloads and the stored Collection.

    Attributes:
        name: Display name of the collection (1-100 characters).
        description: Optional summary of the collection's purpose
            (max 500 characters).
    """
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CollectionCreate(CollectionBase):
    """Payload for creating a new collection (POST /collections)."""


class Collection(CollectionBase):
    """A stored collection as returned by the API.

    Attributes:
        id: Unique identifier, generated automatically at creation.
        created_at: Timestamp of creation (UTC).
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)

    class Config:
        from_attributes = True


# ============== Response Models ==============

class PromptList(BaseModel):
    """Envelope for GET /prompts responses.

    Attributes:
        prompts: The prompts matching the request's filters.
        total: The number of prompts in the response.
    """
    prompts: List[Prompt]
    total: int


class CollectionList(BaseModel):
    """Envelope for GET /collections responses.

    Attributes:
        collections: All stored collections.
        total: The number of collections in the response.
    """
    collections: List[Collection]
    total: int


class HealthResponse(BaseModel):
    """Envelope for the GET /health response.

    Attributes:
        status: Operational status of the service (e.g. "healthy").
        version: The running application version.
    """
    status: str
    version: str
