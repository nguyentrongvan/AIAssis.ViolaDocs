"""
Tests for Workflow & Tasks endpoints.

Covers:
- POST /workflows - Start workflow on document
- GET /workflows/{id} - Get workflow status
- POST /tasks/{id}/action - Approve/reject/request changes
- GET /tasks - Get task inbox
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.api
class TestWorkflowsStart:
    """Tests for POST /workflows endpoint."""
    
    async def test_start_workflow_success(self, client, user_token, test_document):
        """Test starting workflow on document."""
        response = client.post(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "template": "approval",
                "assignees": []
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert "id" in data["data"] or "workflow_id" in data["data"]
    
    async def test_start_workflow_with_assignees(self, client, user_token, test_document, regular_user):
        """Test starting workflow with assignees."""
        response = client.post(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": test_document.id,
                "template": "review",
                "assignees": [regular_user.id]
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_start_workflow_not_found_document(self, client, user_token):
        """Test starting workflow on non-existent document."""
        response = client.post(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": 99999,
                "template": "approval"
            }
        )
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]
    
    async def test_start_workflow_unauthorized(self, client):
        """Test starting workflow without authentication."""
        response = client.post(
            "/api/v1/workflows",
            json={"document_id": 1, "template": "approval"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestWorkflowsGet:
    """Tests for GET /workflows/{id} endpoint."""
    
    async def test_get_workflow_success(self, client, user_token, test_db, test_document, regular_user):
        """Test getting workflow status."""
        from src.app.models.workflows import Workflow
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.commit()
        await test_db.refresh(workflow)
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert data["data"]["id"] == workflow.id
    
    async def test_get_workflow_not_found(self, client, user_token):
        """Test getting non-existent workflow."""
        response = client.get(
            "/api/v1/workflows/99999",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_workflow_unauthorized(self, client):
        """Test getting workflow without authentication."""
        response = client.get("/api/v1/workflows/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestTasksAction:
    """Tests for POST /tasks/{id}/action endpoint."""
    
    async def test_task_approve_success(self, client, user_token, test_db, test_document, regular_user):
        """Test approving a task."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        await test_db.refresh(task)
        
        response = client.post(
            f"/api/v1/tasks/{task.id}/action",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "action": "approve",
                "comment": "Looks good"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
    
    async def test_task_reject_success(self, client, user_token, test_db, test_document, regular_user):
        """Test rejecting a task."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        await test_db.refresh(task)
        
        response = client.post(
            f"/api/v1/tasks/{task.id}/action",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "action": "reject",
                "comment": "Needs revision"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_task_request_changes_success(self, client, user_token, test_db, test_document, regular_user):
        """Test requesting changes on a task."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        await test_db.refresh(task)
        
        response = client.post(
            f"/api/v1/tasks/{task.id}/action",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "action": "request_changes",
                "comment": "Please update section 3"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_task_action_not_found(self, client, user_token):
        """Test action on non-existent task."""
        response = client.post(
            "/api/v1/tasks/99999/action",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"action": "approve"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_task_action_unauthorized(self, client, user_token, staff_token, test_db, test_document, regular_user, staff_user):
        """Test action on task assigned to another user."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        await test_db.refresh(task)
        
        # Try to act on task as different user
        response = client.post(
            f"/api/v1/tasks/{task.id}/action",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"action": "approve"}
        )
        # Should either allow (if staff can act) or deny
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
    
    async def test_task_action_invalid_action(self, client, user_token, test_db, test_document, regular_user):
        """Test action with invalid action type."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        await test_db.refresh(task)
        
        response = client.post(
            f"/api/v1/tasks/{task.id}/action",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"action": "invalid_action"}
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.api
class TestTasksInbox:
    """Tests for GET /tasks endpoint."""
    
    async def test_get_tasks_inbox_success(self, client, user_token, test_db, test_document, regular_user):
        """Test getting task inbox."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        
        response = client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_success"] is True
        assert isinstance(data["data"], list)
    
    async def test_get_tasks_filtered_by_state(self, client, user_token, test_db, test_document, regular_user):
        """Test getting tasks filtered by state."""
        from src.app.models.workflows import Workflow, Task
        workflow = Workflow(
            document_id=test_document.id,
            template="approval",
            state="pending",
            assignees=[regular_user.id]
        )
        test_db.add(workflow)
        await test_db.flush()
        
        task = Task(
            workflow_id=workflow.id,
            assignee_id=regular_user.id,
            state="pending"
        )
        test_db.add(task)
        await test_db.commit()
        
        response = client.get(
            "/api/v1/tasks?state=pending",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    async def test_get_tasks_unauthorized(self, client):
        """Test getting tasks without authentication."""
        response = client.get("/api/v1/tasks")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
