"""Utility functions for PromptLab"""

from typing import List
from app.models import Prompt


def sort_prompts_by_date(prompts: List[Prompt], descending: bool = True) -> List[Prompt]:
    """Sort prompts by creation date.

    Args:
        prompts: The prompts to sort.
        descending: If True (default), newest prompts come first; if False,
            oldest come first.

    Returns:
        A new list containing the same prompts, ordered by created_at.
    """
    return sorted(prompts, key=lambda p: p.created_at, reverse=descending)


def filter_prompts_by_collection(prompts: List[Prompt], collection_id: str) -> List[Prompt]:
    """Keep only the prompts assigned to a given collection.

    Args:
        prompts: The prompts to filter.
        collection_id: The unique identifier of the collection to match.

    Returns:
        A new list of the prompts whose collection_id equals collection_id.
    """
    return [p for p in prompts if p.collection_id == collection_id]


def search_prompts(prompts: List[Prompt], query: str) -> List[Prompt]:
    """Search prompts by title and description.

    Args:
        prompts: The prompts to search.
        query: Case-insensitive substring to look for in each prompt's
            title and (if set) description.

    Returns:
        A new list of the prompts whose title or description contains the
        query.
    """
    query_lower = query.lower()
    return [
        p for p in prompts
        if query_lower in p.title.lower() or
           (p.description and query_lower in p.description.lower())
    ]


def validate_prompt_content(content: str) -> bool:
    """Check if prompt content is valid.
    
    A valid prompt should:
    - Not be empty
    - Not be just whitespace
    - Be at least 10 characters

    Args:
        content: The raw prompt template text to validate.

    Returns:
        True if the content is non-blank and at least 10 characters long
        after stripping surrounding whitespace, False otherwise.
    """
    if not content or not content.strip():
        return False
    return len(content.strip()) >= 10


def extract_variables(content: str) -> List[str]:
    """Extract template variables from prompt content.

    Variables are in the format {{variable_name}}.

    Args:
        content: The prompt template text to scan.

    Returns:
        A list of variable names (without braces) in order of appearance;
        empty if the content contains no variables.
    """
    import re
    pattern = r'\{\{(\w+)\}\}'
    return re.findall(pattern, content)
