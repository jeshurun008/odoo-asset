import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    department_repository_instance
)
from app.domain.user import User, Role
from app.domain.department import Department
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _seed_data():
    """Seeds departments and employees for scoping tests."""
    user_repository_instance._users.clear()
    department_repository_instance._departments.clear()
    
    # 1. Create two departments
    dept_eng = Department(name="Engineering")
    dept_sales = Department(name="Sales")
    await department_repository_instance.create(dept_eng)
    await department_repository_instance.create(dept_sales)
    
    # 2. Seed Admin
    pwd = "Password123!"
    admin = User(email="admin-dir@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)
    
    # 3. Seed Department Head for Engineering
    head_eng = User(
        email="head-eng@assetflow.com",
        hashed_password=hash_password(pwd),
        name="Eng Head",
        role=Role.DEPARTMENT_HEAD,
        department_id=dept_eng.id
    )
    await user_repository_instance.create(head_eng)
    
    # 4. Seed Employee in Engineering
    emp_eng = User(
        email="emp-eng@assetflow.com",
        hashed_password=hash_password(pwd),
        name="Eng Employee",
        role=Role.EMPLOYEE,
        department_id=dept_eng.id
    )
    await user_repository_instance.create(emp_eng)
    
    # 5. Seed Employee in Sales
    emp_sales = User(
        email="emp-sales@assetflow.com",
        hashed_password=hash_password(pwd),
        name="Sales Employee",
        role=Role.EMPLOYEE,
        department_id=dept_sales.id
    )
    await user_repository_instance.create(emp_sales)
    
    return {
        "admin": admin,
        "head_eng": head_eng,
        "emp_eng": emp_eng,
        "emp_sales": emp_sales,
        "dept_eng": dept_eng,
        "dept_sales": dept_sales,
        "password": pwd
    }


async def test_employee_directory_admin_scoping(client: AsyncClient):
    """Admin must see all employees in the directory."""
    data = await _seed_data()
    
    # Login as Admin
    form_data = {"username": data["admin"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/employees", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    # Admin sees 4 users: admin, head_eng, emp_eng, emp_sales
    assert len(items) == 4


async def test_employee_directory_dept_head_scoping(client: AsyncClient):
    """Department Head must only see employees belonging to their department."""
    data = await _seed_data()
    
    # Login as Engineering Department Head
    form_data = {"username": data["head_eng"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=res_login.url.path if "res_login" in locals() else form_data)
    # Wait, res_login is from form_data above
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/employees", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    # Head sees only Engineering employees: head_eng, emp_eng
    assert len(items) == 2
    emails = [user["email"] for user in items]
    assert "head-eng@assetflow.com" in emails
    assert "emp-eng@assetflow.com" in emails
    assert "emp-sales@assetflow.com" not in emails


async def test_employee_detail_scoping(client: AsyncClient):
    """Verify detail permissions and cross-department block for Department Heads."""
    data = await _seed_data()
    
    # Login as Engineering Head
    form_data = {"username": data["head_eng"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. View employee in own department (Eng Employee) -> Success
    res_own = await client.get(f"/api/v1/employees/{data['emp_eng'].id}", headers=headers)
    assert res_own.status_code == 200
    
    # 2. View employee in other department (Sales Employee) -> Forbidden
    res_other = await client.get(f"/api/v1/employees/{data['emp_sales'].id}", headers=headers)
    assert res_other.status_code == 403
    assert "Access denied" in res_other.json()["error"]["message"]


async def test_login_blocked_for_deactivated_employee(client: AsyncClient):
    """Verify that administratively deactivating a user blocks them from logging in."""
    data = await _seed_data()

    # 1. Login initially (should succeed)
    form_data = {"username": data["emp_eng"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    assert res_login.status_code == 200

    # 2. Deactivate the employee as Admin
    form_data_admin = {"username": data["admin"].email, "password": data["password"]}
    res_admin_login = await client.post("/api/v1/auth/login", data=form_data_admin)
    admin_token = res_admin_login.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    res_deact = await client.patch(f"/api/v1/employees/{data['emp_eng'].id}/deactivate", headers=admin_headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["data"]["is_active"] is False

    # 3. Attempt login again (should fail with 401 and inactive status message)
    res_login_retry = await client.post("/api/v1/auth/login", data=form_data)
    assert res_login_retry.status_code == 401
    assert "Account is inactive" in res_login_retry.json()["error"]["message"]
