"""FastAPI routes for PromptLab"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal, Optional

from app.models import (
    Prompt, PromptCreate, PromptUpdate, PromptPatch,
    Collection, CollectionCreate,
    PromptList, CollectionList, HealthResponse,
    get_current_time
)
from app.storage import storage, UNASSIGNED_COLLECTION_NAME
from app.utils import sort_prompts_by_date, filter_prompts_by_collection, search_prompts
from app import __version__

app = FastAPI(
    title="PromptLab API",
    description="AI Prompt Engineering Platform",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Health Check ==============

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", version=__version__)


# ============== Prompt Endpoints ==============

@app.get("/prompts", response_model=PromptList)
def list_prompts(
    collection_id: Optional[str] = None,
    search: Optional[str] = None
):
    prompts = storage.get_all_prompts()
    
    # Filter by collection if specified
    if collection_id:
        prompts = filter_prompts_by_collection(prompts, collection_id)
    
    # Search if query provided
    if search:
        prompts = search_prompts(prompts, search)
    
    # Sort by date (newest first)
    prompts = sort_prompts_by_date(prompts, descending=True)
    
    return PromptList(prompts=prompts, total=len(prompts))


@app.get("/prompts/{prompt_id}", response_model=Prompt)
def get_prompt(prompt_id: str):
    prompt = storage.get_prompt(prompt_id)
    
    if prompt is not None:
        return prompt
    else:
        raise HTTPException(status_code=404, detail="Prompt not found")
    

@app.post("/prompts", response_model=Prompt, status_code=201)
def create_prompt(prompt_data: PromptCreate):
    # Validate collection exists if provided
    if prompt_data.collection_id:
        collection = storage.get_collection(prompt_data.collection_id)
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")
    
    prompt = Prompt(**prompt_data.model_dump())
    return storage.create_prompt(prompt)


@app.put("/prompts/{prompt_id}", response_model=Prompt)
def update_prompt(prompt_id: str, prompt_data: PromptUpdate):
    existing = storage.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Validate collection if provided
    if prompt_data.collection_id:
        collection = storage.get_collection(prompt_data.collection_id)
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")

    updated_prompt = Prompt(
        id=existing.id,
        title=prompt_data.title,
        content=prompt_data.content,
        description=prompt_data.description,
        collection_id=prompt_data.collection_id,
        created_at=existing.created_at,
        updated_at=get_current_time()
    )
    
    return storage.update_prompt(prompt_id, updated_prompt)


@app.patch("/prompts/{prompt_id}", response_model=Prompt)
def patch_prompt(prompt_id: str, prompt_data: PromptPatch):
    existing = storage.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Only apply the fields the client actually sent.
    # Omitted fields stay unchanged; an explicit null clears the field.
    changes = prompt_data.model_dump(exclude_unset=True)

    # Validate the collection only when it is being changed
    # (explicit null means "remove from collection" and needs no check)
    if "collection_id" in changes and changes["collection_id"] is not None:
        collection = storage.get_collection(changes["collection_id"])
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")

    updated_prompt = existing.model_copy(update=changes)
    updated_prompt.updated_at = get_current_time()

    return storage.update_prompt(prompt_id, updated_prompt)


@app.delete("/prompts/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: str):
    if not storage.delete_prompt(prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return None


# ============== Collection Endpoints ==============
@app.get("/collections", response_model=CollectionList)
def list_collections():
    collections = storage.get_all_collections()
    return CollectionList(collections=collections, total=len(collections))


@app.get("/collections/{collection_id}", response_model=Collection)
def get_collection(collection_id: str):
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
    

@app.post("/collections", response_model=Collection, status_code=201)
def create_collection(collection_data: CollectionCreate):
    collection = Collection(**collection_data.model_dump())
    return storage.create_collection(collection)


@app.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: str,
    action: Optional[Literal["reassign", "create_new", "unassign"]] = None,
    target_collection_id: Optional[str] = None,
    new_collection_name: Optional[str] = None,
    new_collection_description: Optional[str] = None,
):
    """Delete a collection without orphaning its prompts.

    - Empty collection: deleted immediately, returns 204.
    - Collection with prompts and no action: returns 409 with an impact
      preview (orphaned prompt count + available options) so the client
      can prompt the user for a choice.
    - Collection with prompts and an action: prompts are moved first, then
      the collection is deleted. Returns 200 with a summary of what happened.

    Actions:
    - reassign:    move prompts to an existing collection (target_collection_id)
    - create_new:  create (or reuse by name) a collection (new_collection_name)
                   and move prompts into it
    - unassign:    move prompts to the system "Unassigned" collection
    """
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # The Unassigned collection is the safety net for orphaned prompts,
    # so it must always exist.
    if collection.name == UNASSIGNED_COLLECTION_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"The '{UNASSIGNED_COLLECTION_NAME}' collection cannot be deleted"
        )

    prompts = storage.get_prompts_by_collection(collection_id)

    # Nothing to reassign: delete right away
    if not prompts:
        storage.delete_collection(collection_id)
        return Response(status_code=204)

    # Prompts would be orphaned: force the client to make an explicit choice
    if action is None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Collection '{collection.name}' still has {len(prompts)} "
                    f"prompt(s). Choose how to handle them before deleting."
                ),
                "orphaned_prompt_count": len(prompts),
                "options": ["reassign", "create_new", "unassign"],
            }
        )

    # Validate everything before mutating anything, so a failed request
    # leaves no partial state behind.
    if action == "reassign":
        if not target_collection_id:
            raise HTTPException(
                status_code=400,
                detail="target_collection_id is required when action='reassign'"
            )
        if target_collection_id == collection_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot reassign prompts to the collection being deleted"
            )
        target = storage.get_collection(target_collection_id)
        if not target:
            raise HTTPException(status_code=400, detail="Target collection not found")
    elif action == "create_new":
        if not new_collection_name or not new_collection_name.strip():
            raise HTTPException(
                status_code=400,
                detail="new_collection_name is required when action='create_new'"
            )
        name = new_collection_name.strip()
        target = storage.get_collection_by_name(name)
        if target and target.id == collection_id:
            raise HTTPException(
                status_code=400,
                detail="new_collection_name matches the collection being deleted"
            )
        if target is None:
            target = storage.create_collection(Collection(
                name=name,
                description=new_collection_description
            ))
    else:  # action == "unassign"
        target = storage.get_or_create_unassigned_collection()

    # All validated: move the prompts first, then delete the collection
    moved = storage.reassign_prompts(collection_id, target.id)
    storage.delete_collection(collection_id)

    return {
        "deleted_collection_id": collection_id,
        "action": action,
        "prompts_moved": moved,
        "target_collection_id": target.id,
        "target_collection_name": target.name,
    }

