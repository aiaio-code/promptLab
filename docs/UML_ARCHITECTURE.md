# System Architecture - ASCII UML

ASCII UML diagrams for the PromptLab backend, derived from the code in
`backend/`. For per-module API details see the generated reference in
`docs/api/` (`index.html`).

Legend (plain-ASCII stand-ins for UML notation):

```
+--------+   class / module            + public member   - private member
|        |
+--------+
  -->        association / dependency ("uses", "imports")
  --|>       inheritance (arrow points to the parent class)
  *--        composition (owns; label shows multiplicity)
  0..1       "zero or one"  (Optional[X])      0..* = "any number"
```

## 1. Component Diagram (layers)

```
              +--------------------------------------+
              |               CLIENTS                |
              |  curl - Swagger UI (/docs) - pytest  |
              |     (product UI not yet built)       |
              +------------------+-------------------+
                                 | HTTP (JSON)
                                 v
+----------------------------------------------------------------------+
| «module» main.py - entry point                                       |
| uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)      |
+----------------------------------------------------------------------+
                                 | imports `app`
                                 v
+----------------------------------------------------------------------+
| «module» app/api.py - FastAPI app + CORSMiddleware (10 endpoints)    |
|----------------------------------------------------------------------|
| GET    /health            -> health_check()                          |
| GET    /prompts           -> list_prompts(collection_id, search)     |
| POST   /prompts           -> create_prompt(prompt_data)              |
| GET    /prompts/{id}      -> get_prompt(prompt_id)                   |
| PUT    /prompts/{id}      -> update_prompt(prompt_id, prompt_data)   |
| PATCH  /prompts/{id}      -> patch_prompt(prompt_id, prompt_data)    |
| DELETE /prompts/{id}      -> delete_prompt(prompt_id)                |
| GET    /collections       -> list_collections()                      |
| POST   /collections       -> create_collection(collection_data)      |
| GET    /collections/{id}  -> get_collection(collection_id)           |
| DELETE /collections/{id}  -> delete_collection(confirm-and-choose)   |
+----------------------------------------------------------------------+
        |                        |                          |
        | validates/serializes   | reads/writes via         | transforms with
        v                        v                          v
+-------------------+ +-----------------------+ +------------------------+
| «module»          | | «module»              | | «utility»              |
| app/models.py     | | app/storage.py        | | app/utils.py           |
| Pydantic schemas: | | Storage singleton:    | | pure functions:        |
| validation +      | | two dicts keyed by    | | sort / filter / search |
| serialization     | | UUID (in-memory only) | | / validate / extract   |
+-------------------+ +-----------------------+ +------------------------+
        ^                        ^                          ^
        +------------------------+------------+-------------+
                 models.py is imported by storage.py and utils.py
```

## 2. Module Dependency Graph

```
+---------+   imports   +---------+
| main.py | ----------> | api.py  |
+---------+             +----+----+
                             |
        +--------------------+---------------------+
        | imports            | imports             | imports
        v                    v                     v
+-------------+      +-----------+           +-----------+
|  models.py  | <--- |storage.py |           | utils.py  |
+-------------+ imp. +-----------+           +-----+-----+
       ^                                            |
       +--------------- imports --------------------+

tests/ (conftest.py, test_api.py) -- imports --> api.py, storage.py
```

## 3. Class Diagram - Domain Models (app/models.py)

Inheritance tree:

```
BaseModel (pydantic)
  |--|> PromptBase .................. shared prompt fields + validation
  |       |--|> PromptCreate ........ POST /prompts payload
  |       |--|> PromptUpdate ........ PUT /prompts/{id} payload (full replace)
  |       +--|> Prompt .............. + id, created_at, updated_at
  |--|> CollectionBase .............. shared collection fields + validation
  |       |--|> CollectionCreate .... POST /collections payload
  |       +--|> Collection .......... + id, created_at
  +--|> PromptPatch ................. PATCH payload; every field Optional
```

Class details:

```
+---------------------------------------------------------------+
|                          PromptBase                           |
|---------------------------------------------------------------|
| + title: str                   (1..200 chars)                 |
| + content: str                 (min 1 char)                   |
| + description: Optional[str]   (max 500 chars)                |
| + collection_id: Optional[str] (link to Collection, 0..1)     |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                      Prompt (PromptBase)                      |
|---------------------------------------------------------------|
| + id: str            (default: generate_id -> uuid4)          |
| + created_at: datetime (default: get_current_time)            |
| + updated_at: datetime (default: get_current_time)            |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                         CollectionBase                        |
|---------------------------------------------------------------|
| + name: str                    (1..100 chars)                 |
| + description: Optional[str]   (max 500 chars)                |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                  Collection (CollectionBase)                  |
|---------------------------------------------------------------|
| + id: str            (default: generate_id -> uuid4)          |
| + created_at: datetime (default: get_current_time)            |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                          PromptPatch                          |
|   (extends BaseModel directly - NOT PromptBase, so every      |
|    field stays Optional for merge-style partial updates)      |
|---------------------------------------------------------------|
| + title: Optional[str]         omitted = unchanged            |
| + content: Optional[str]       explicit null = clear field    |
| + description: Optional[str]                                  |
| + collection_id: Optional[str]                                |
+---------------------------------------------------------------+
```

Association between the two aggregates:

```
+----------+  0..*        collection_id          0..1  +--------------+
|  Prompt  | ----------------------------------------> | Collection |
+----------+    (loose reference by id string;         +--------------+
                 no storage-level foreign key)
```

Response envelopes (composition) and helpers:

```
+----------------+  1        prompts        0..*  +--------+
|   PromptList   | ------------------------------> | Prompt |
|----------------|                                 +--------+
| + prompts      |
| + total: int   |
+----------------+

+----------------+  1      collections      0..*  +------------+
| CollectionList | ------------------------------> | Collection |
|----------------|                                 +------------+
| + collections  |
| + total: int   |
+----------------+

+-----------------------------+  +----------------------------------------+
|       HealthResponse        |  | module helpers (app/models.py)         |
|-----------------------------|  |----------------------------------------|
| + status: str               |  | + generate_id() -> str      (uuid4)    |
| + version: str              |  | + get_current_time() -> datetime (UTC) |
+-----------------------------+  +----------------------------------------+
```

## 4. Class Diagram - Storage (app/storage.py)

```
+----------------------------------------------------------------------+
|                               Storage                                |
|        (global singleton `storage`; in-memory, lost on shutdown)     |
|----------------------------------------------------------------------|
| - _prompts: Dict[str, Prompt]                                        |
| - _collections: Dict[str, Collection]                                |
|----------------------------------------------------------------------|
| + create_prompt(prompt) -> Prompt                                    |
| + get_prompt(prompt_id) -> Optional[Prompt]                          |
| + get_all_prompts() -> List[Prompt]                                  |
| + update_prompt(prompt_id, prompt) -> Optional[Prompt]               |
| + delete_prompt(prompt_id) -> bool                                   |
| + create_collection(collection) -> Collection                        |
| + get_collection(collection_id) -> Optional[Collection]              |
| + get_all_collections() -> List[Collection]                          |
| + delete_collection(collection_id) -> bool                           |
| + get_collection_by_name(name) -> Optional[Collection]               |
| + get_or_create_unassigned_collection() -> Collection                |
| + get_prompts_by_collection(collection_id) -> List[Prompt]           |
| + reassign_prompts(from_id, to_id) -> int                            |
| + clear() -> None                       (test isolation)             |
+---------------------------+----------------------+-------------------+
                            | *                    | *
                         owns 0..*              owns 0..*
                            v                      v
                       +---------+           +------------+
                       |  Prompt |           | Collection |
                       +---------+           +------------+

Constant: UNASSIGNED_COLLECTION_NAME = "Unassigned"
  -> system collection that catches prompts when their collection is
     deleted with action="unassign"; cannot itself be deleted.
```

## 5. Utility Functions (app/utils.py)

```
+----------------------------------------------------------------------+
| «utility» app/utils.py - pure functions over Prompt lists            |
|----------------------------------------------------------------------|
| + sort_prompts_by_date(prompts, descending=True) -> List[Prompt]     |
| + filter_prompts_by_collection(prompts, collection_id) -> List[Pr..] |
| + search_prompts(prompts, query) -> List[Prompt]                     |
| + validate_prompt_content(content) -> bool   (defined, not wired in) |
| + extract_variables(content) -> List[str]      (defined, not wired)  |
+----------------------------------------------------------------------+
```

## 6. Runtime Notes

- Exactly one `Storage` instance exists per process (`storage` singleton);
  restarting the server wipes all data.
- `Prompt.updated_at` is refreshed by PUT, PATCH, and `reassign_prompts`.
- Collection deletion never orphans prompts: callers must supply
  `action` = reassign | create_new | unassign (409 preview otherwise).
- The test suite injects `TestClient(app)` and resets the singleton via
  `storage.clear()` around every test (see `tests/conftest.py`).
