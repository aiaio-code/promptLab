"""PromptLab API Server - application entry point.

README
======

What is PromptLab?
------------------
PromptLab is an AI prompt engineering platform - a "Postman for Prompts" -
that helps engineers store, organize, and manage prompt templates. Prompts
can contain template variables (e.g. ``{{input}}``), be grouped into
collections, and be filtered and searched over a REST API.

Current state: no UI
--------------------
The frontend has not been built yet, so the application is exercised
entirely through its REST API. FastAPI's auto-generated Swagger UI serves
as the de facto interface for trying every endpoint from a browser.

Requirements
------------
- Python 3.10+
- The packages listed in ``requirements.txt``

Running the server
------------------
From the ``backend/`` directory::

    pip install -r requirements.txt
    python main.py

The API is then available at:

- API root:          http://localhost:8000
- Interactive docs:  http://localhost:8000/docs  (Swagger UI)
- Alternative docs:  http://localhost:8000/redoc
- Health check:      http://localhost:8000/health

Using the API without a UI
--------------------------
Create a collection, then create prompts inside it::

    # Create a collection (note the "id" in the JSON response)
    curl -X POST http://localhost:8000/collections \
         -H "Content-Type: application/json" \
         -d '{"name": "Development", "description": "Prompts for dev tasks"}'

    # Create a prompt (optionally pass "collection_id" from above)
    curl -X POST http://localhost:8000/prompts \
         -H "Content-Type: application/json" \
         -d '{"title": "Code Review",
              "content": "Review the following code:\\n\\n{{code}}"}'

    # List prompts (optionally filter by collection or search text)
    curl "http://localhost:8000/prompts?search=review"

Running the tests
-----------------
From the ``backend/`` directory::

    pytest tests/ -v

Implementation notes
--------------------
- Data is stored in memory only (see ``app/storage.py``); everything is
  lost when the server stops.
- ``reload=True`` requires the app to be passed to uvicorn as the import
  string ``"main:app"`` rather than as an object.
"""

import uvicorn
from app.api import app

if __name__ == "__main__":
    # reload=True requires the app as an import string, not an object
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
