"""PromptLab API Server

Run with: python main.py
"""

import uvicorn
from app.api import app

if __name__ == "__main__":
    # reload=True requires the app as an import string, not an object
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
