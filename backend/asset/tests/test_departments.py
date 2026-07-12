import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    department_repository_instance
)
from app.domain.user import User, Role
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin_and_login(client: AsyncClient):
    """Helper to seed an admin user and return headers with JWT."""
    user_repository_instance._users.clear()
    department_repository_instance._departments.clear()
    
    pwd = "AdminPass123!"
    admin = User(email="admin-dept@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)
    
    form_data = {"username": admin.email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_read_department(client: AsyncClient):
    """Verify department registration and retrieval."""
    headers = await _create_admin_and_login(client)
    
    # 1. Create department
    payload = {
        "name": "Engineering",
        "description": "Software development division"
    }
    response = await client.post("/api/v1/departments", json=payload, headers=headers)
    assert response.status_code == 201
    dept_data = response.json()["data"]
    assert dept_data["name"] == "Engineering"
    assert dept_data["is_active"] is True
    
    # 2. Get department details
    response_get = await client.get(f"/api/v1/departments/{dept_data['id']}", headers=headers)
    assert response_get.status_code == 200
    assert response_get.json()["data"]["name"] == "Engineering"


async def test_circular_hierarchy_check(client: AsyncClient):
    """Ensure circular dependencies are rejected in parent assignments."""
    headers = await _create_admin_and_login(client)
    
    # Create Dept A
    res_a = await client.post("/api/v1/departments", json={"name": "Dept A"}, headers=headers)
    id_a = res_a.json()["data"]["id"]
    
    # Create Dept B (parent is A)
    res_b = await client.post("/api/v1/departments", json={"name": "Dept B", "parent_department_id": id_a}, headers=headers)
    id_b = res_b.json()["data"]["id"]
    
    # Try updating Dept A to have B as parent (A -> B -> A circular cycle)
    res_update = await client.patch(f"/api/v1/departments/{id_a}", json={"parent_department_id": id_b}, headers=headers)
    assert res_update.status_code == 409
    assert "Circular hierarchy detected" in res_update.json()["error"]["message"]


async def test_assign_department_head_validation(client: AsyncClient):
    """Verify that a department head must be a user with the DEPARTMENT_HEAD or ADMIN role."""
    headers = await _create_admin_and_login(client)
    
    # Seed a standard Employee
    emp = User(email="employee@assetflow.com", hashed_password=hash_password("Password!"), name="Employee", role=Role.EMPLOYEE)
    await user_repository_instance.create(emp)
    
    # Seed a Department Head
    head = User(email="head@assetflow.com", hashed_password=hash_password("Password!"), name="Head User", role=Role.DEPARTMENT_HEAD)
    await user_repository_instance.create(head)
    
    # 1. Attempt assigning Employee as head (should fail)
    res_fail = await client.post("/api/v1/departments", json={"name": "Dept Fail", "department_head_id": emp.id}, headers=headers)
    assert res_fail.status_code == 409
    assert "does not possess the DEPARTMENT_HEAD or ADMIN role" in res_fail.json()["error"]["message"]
    
    # 2. Attempt assigning Head User as head (should succeed)
    res_ok = await client.post("/api/v1/departments", json={"name": "Dept OK", "department_head_id": head.id}, headers=headers)
    assert res_ok.status_code == 201


async def test_deactivate_department_blocked(client: AsyncClient):
    """Ensure deactivation is blocked when active children or employees remain."""
    headers = await _create_admin_and_login(client)
    
    # 1. Create Parent and Child
    res_parent = await client.post("/api/v1/departments", json={"name": "Parent Dept"}, headers=headers)
    parent_id = res_parent.json()["data"]["id"]
    
    res_child = await client.post("/api/v1/departments", json={"name": "Child Dept", "parent_department_id": parent_id}, headers=headers)
    child_id = res_child.json()["data"]["id"]
    
    # Try deactivating Parent Dept (should fail due to child)
    res_deact = await client.patch(f"/api/v1/departments/{parent_id}/deactivate", headers=headers)
    assert res_deact.status_code == 409
    assert "1 active sub-department(s) still assigned" in res_deact.json()["error"]["message"]

    # Deactivate Child
    await client.patch(f"/api/v1/departments/{child_id}/deactivate", headers=headers)

    # Seed employee inside Parent Dept
    emp = User(
        email="emp-dept@assetflow.com",
        hashed_password=hash_password("Password!"),
        name="Employee",
        role=Role.EMPLOYEE,
        department_id=parent_id
    )
    await user_repository_instance.create(emp)

    # Try deactivating Parent (should fail due to employee)
    res_deact2 = await client.patch(f"/api/v1/departments/{parent_id}/deactivate", headers=headers)
    assert res_deact2.status_code == 409
    assert "1 active employee(s) still assigned" in res_deact2.json()["error"]["message"]


async def test_deactivate_department_blocked_by_active_employees(client: AsyncClient):
    """Verify that deactivating a department is blocked when active employees are assigned."""
    headers = await _create_admin_and_login(client)

    # Create Parent Dept
    res = await client.post("/api/v1/departments", json={"name": "Finance"}, headers=headers)
    dept_id = res.json()["data"]["id"]

    # Assign employee
    emp = User(
        email="finance-emp@assetflow.com",
        hashed_password=hash_password("Password!"),
        name="Finance Guy",
        role=Role.EMPLOYEE,
        department_id=dept_id
    )
    await user_repository_instance.create(emp)

    # Try deactivating
    res_deact = await client.patch(f"/api/v1/departments/{dept_id}/deactivate", headers=headers)
    assert res_deact.status_code == 409
    assert "Cannot deactivate department: 1 active employee(s) still assigned." in res_deact.json()["error"]["message"]


async def test_department_duplicate_active_name_rejected(client: AsyncClient):
    """Verify that duplicate department names are rejected among active departments (case-insensitive), but inactive names can be reused."""
    headers = await _create_admin_and_login(client)

    # 1. Create department "Finance"
    res1 = await client.post("/api/v1/departments", json={"name": "Finance"}, headers=headers)
    assert res1.status_code == 201
    dept_id = res1.json()["data"]["id"]

    # 2. Attempt to create another "finance" (different casing) -> Should fail with 409
    res2 = await client.post("/api/v1/departments", json={"name": "finance"}, headers=headers)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["error"]["message"]

    # 3. Deactivate the first "Finance" department
    await client.patch(f"/api/v1/departments/{dept_id}/deactivate", headers=headers)

    # 4. Attempt to create "finance" again -> Should now succeed
    res3 = await client.post("/api/v1/departments", json={"name": "finance"}, headers=headers)
    assert res3.status_code == 201
