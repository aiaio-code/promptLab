"""API tests for PromptLab

These tests verify the API endpoints work correctly.
Students should expand these tests significantly in Week 3.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealth:
    """Tests for health endpoint."""
    
    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestPrompts:
    """Tests for prompt endpoints."""
    
    def test_create_prompt(self, client: TestClient, sample_prompt_data):
        response = client.post("/prompts", json=sample_prompt_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_prompt_data["title"]
        assert data["content"] == sample_prompt_data["content"]
        assert "id" in data
        assert "created_at" in data
    
    def test_list_prompts_empty(self, client: TestClient):
        response = client.get("/prompts")
        assert response.status_code == 200
        data = response.json()
        assert data["prompts"] == []
        assert data["total"] == 0
    
    def test_list_prompts_with_data(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        client.post("/prompts", json=sample_prompt_data)
        
        response = client.get("/prompts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["total"] == 1
    
    def test_get_prompt_success(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]
        
        response = client.get(f"/prompts/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prompt_id
    
    def test_get_prompt_not_found(self, client: TestClient):
        """Test that getting a non-existent prompt returns 404."""
        response = client.get("/prompts/nonexistent-id")
        assert response.status_code == 404
    
    def test_delete_prompt(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/prompts/{prompt_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/prompts/{prompt_id}")
        assert get_response.status_code == 404

    def test_update_prompt(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]
        original_updated_at = create_response.json()["updated_at"]

        # Update it
        updated_data = {
            "title": "Updated Title",
            "content": "Updated content for the prompt",
            "description": "Updated description"
        }

        import time
        time.sleep(0.1)  # Small delay to ensure timestamp would change

        response = client.put(f"/prompts/{prompt_id}", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

        # The updated_at timestamp should be refreshed on update
        assert data["updated_at"] != original_updated_at

    def test_sorting_order(self, client: TestClient):
        """Test that prompts are sorted newest first."""
        import time
        # Create prompts with delay
        prompt1 = {"title": "First", "content": "First prompt content"}
        prompt2 = {"title": "Second", "content": "Second prompt content"}

        client.post("/prompts", json=prompt1)
        time.sleep(0.1)
        client.post("/prompts", json=prompt2)

        response = client.get("/prompts")
        prompts = response.json()["prompts"]

        # Newest (Second) should be first
        assert prompts[0]["title"] == "Second"


class TestCollections:
    """Tests for collection endpoints."""

    def test_create_collection(self, client: TestClient, sample_collection_data):
        response = client.post("/collections", json=sample_collection_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_collection_data["name"]
        assert "id" in data

    def test_list_collections(self, client: TestClient, sample_collection_data):
        client.post("/collections", json=sample_collection_data)

        response = client.get("/collections")
        assert response.status_code == 200
        data = response.json()
        assert len(data["collections"]) == 1

    def test_get_collection_not_found(self, client: TestClient):
        response = client.get("/collections/nonexistent-id")
        assert response.status_code == 404

    def test_delete_collection_empty(self, client: TestClient, sample_collection_data):
        """Deleting an empty collection returns 204 with no action needed."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]

        response = client.delete(f"/collections/{collection_id}")
        assert response.status_code == 204

        assert client.get(f"/collections/{collection_id}").status_code == 404

    def test_delete_collection_with_prompts_requires_action(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """Deleting a non-empty collection without an action returns 409 and changes nothing."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(f"/collections/{collection_id}")
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["orphaned_prompt_count"] == 1
        assert set(detail["options"]) == {"reassign", "create_new", "unassign"}

        # Atomicity: collection and prompt are untouched
        assert client.get(f"/collections/{collection_id}").status_code == 200
        prompt = client.get("/prompts").json()["prompts"][0]
        assert prompt["collection_id"] == collection_id

    def test_delete_collection_action_reassign(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=reassign moves prompts to the chosen existing collection."""
        source_id = client.post("/collections", json=sample_collection_data).json()["id"]
        target_id = client.post("/collections", json={"name": "Marketing"}).json()["id"]
        prompt_id = client.post(
            "/prompts", json={**sample_prompt_data, "collection_id": source_id}
        ).json()["id"]
        original_updated_at = client.get(f"/prompts/{prompt_id}").json()["updated_at"]

        import time
        time.sleep(0.1)  # Ensure a timestamp change would be visible

        response = client.delete(
            f"/collections/{source_id}",
            params={"action": "reassign", "target_collection_id": target_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_collection_id"] == source_id
        assert data["action"] == "reassign"
        assert data["prompts_moved"] == 1
        assert data["target_collection_id"] == target_id
        assert data["target_collection_name"] == "Marketing"

        # Source collection is gone and the prompt now points at the target
        assert client.get(f"/collections/{source_id}").status_code == 404
        prompt = client.get(f"/prompts/{prompt_id}").json()
        assert prompt["collection_id"] == target_id
        assert prompt["updated_at"] != original_updated_at

    def test_delete_collection_action_reassign_missing_target(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=reassign without target_collection_id returns 400."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(f"/collections/{collection_id}", params={"action": "reassign"})
        assert response.status_code == 400
        assert client.get(f"/collections/{collection_id}").status_code == 200

    def test_delete_collection_action_reassign_to_self(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """Reassigning prompts to the collection being deleted returns 400."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(
            f"/collections/{collection_id}",
            params={"action": "reassign", "target_collection_id": collection_id}
        )
        assert response.status_code == 400
        assert client.get(f"/collections/{collection_id}").status_code == 200

    def test_delete_collection_action_reassign_invalid_target(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=reassign with a non-existent target collection returns 400."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(
            f"/collections/{collection_id}",
            params={"action": "reassign", "target_collection_id": "nonexistent-id"}
        )
        assert response.status_code == 400
        assert client.get(f"/collections/{collection_id}").status_code == 200

    def test_delete_collection_action_create_new(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=create_new creates a collection and moves the prompts into it."""
        source_id = client.post("/collections", json=sample_collection_data).json()["id"]
        prompt_id = client.post(
            "/prompts", json={**sample_prompt_data, "collection_id": source_id}
        ).json()["id"]

        response = client.delete(
            f"/collections/{source_id}",
            params={"action": "create_new", "new_collection_name": "Archived"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["prompts_moved"] == 1
        assert data["target_collection_name"] == "Archived"

        # New collection exists and holds the prompt
        new_collection = client.get(f"/collections/{data['target_collection_id']}")
        assert new_collection.status_code == 200
        assert new_collection.json()["name"] == "Archived"
        assert client.get(f"/prompts/{prompt_id}").json()["collection_id"] == data["target_collection_id"]
        assert client.get(f"/collections/{source_id}").status_code == 404

    def test_delete_collection_action_create_new_reuses_existing_name(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """create_new with a name that already exists reuses that collection."""
        source_id = client.post("/collections", json=sample_collection_data).json()["id"]
        existing_id = client.post("/collections", json={"name": "Research"}).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": source_id})

        response = client.delete(
            f"/collections/{source_id}",
            params={"action": "create_new", "new_collection_name": "Research"}
        )
        assert response.status_code == 200
        assert response.json()["target_collection_id"] == existing_id

        # No duplicate collection was created
        collections = client.get("/collections").json()["collections"]
        assert [c["name"] for c in collections] == ["Research"]

    def test_delete_collection_action_create_new_missing_name(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=create_new without a name returns 400."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(f"/collections/{collection_id}", params={"action": "create_new"})
        assert response.status_code == 400
        assert client.get(f"/collections/{collection_id}").status_code == 200

    def test_delete_collection_action_create_new_same_name_as_deleted(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """create_new naming the collection being deleted returns 400."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(
            f"/collections/{collection_id}",
            params={"action": "create_new", "new_collection_name": sample_collection_data["name"]}
        )
        assert response.status_code == 400
        assert client.get(f"/collections/{collection_id}").status_code == 200

    def test_delete_collection_action_unassign(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """action=unassign moves prompts to the system 'Unassigned' collection."""
        source_id = client.post("/collections", json=sample_collection_data).json()["id"]
        prompt_id = client.post(
            "/prompts", json={**sample_prompt_data, "collection_id": source_id}
        ).json()["id"]

        response = client.delete(f"/collections/{source_id}", params={"action": "unassign"})
        assert response.status_code == 200
        data = response.json()
        assert data["prompts_moved"] == 1
        assert data["target_collection_name"] == "Unassigned"

        # The Unassigned collection exists and holds the prompt
        unassigned = client.get(f"/collections/{data['target_collection_id']}")
        assert unassigned.status_code == 200
        assert unassigned.json()["name"] == "Unassigned"
        assert client.get(f"/prompts/{prompt_id}").json()["collection_id"] == data["target_collection_id"]
        assert client.get(f"/collections/{source_id}").status_code == 404

    def test_delete_collection_unassign_reuses_single_unassigned_collection(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """Repeated unassign deletions share one 'Unassigned' collection."""
        for name in ("Alpha", "Beta"):
            col_id = client.post("/collections", json={"name": name}).json()["id"]
            client.post("/prompts", json={**sample_prompt_data, "collection_id": col_id})
            response = client.delete(f"/collections/{col_id}", params={"action": "unassign"})
            assert response.status_code == 200

        collections = client.get("/collections").json()
        assert collections["total"] == 1
        assert collections["collections"][0]["name"] == "Unassigned"

        unassigned_id = collections["collections"][0]["id"]
        prompts = client.get("/prompts").json()["prompts"]
        assert len(prompts) == 2
        assert all(p["collection_id"] == unassigned_id for p in prompts)

    def test_delete_unassigned_collection_is_forbidden(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """The system 'Unassigned' collection cannot be deleted."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})
        unassigned_id = client.delete(
            f"/collections/{collection_id}", params={"action": "unassign"}
        ).json()["target_collection_id"]

        # Even with an action supplied, deletion is refused
        response = client.delete(f"/collections/{unassigned_id}", params={"action": "unassign"})
        assert response.status_code == 400
        assert client.get(f"/collections/{unassigned_id}").status_code == 200

    def test_delete_collection_invalid_action(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """An unknown action value is rejected with 422."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})

        response = client.delete(f"/collections/{collection_id}", params={"action": "bogus"})
        assert response.status_code == 422
        assert client.get(f"/collections/{collection_id}").status_code == 200
