import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance,
    booking_repository_instance,
    department_repository_instance
)
from app.domain.user import User, Role
from app.domain.asset import Asset, AssetStatus
from app.domain.asset_category import AssetCategory
from app.domain.department import Department
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _seed_data(client: AsyncClient):
    """Helper to seed directory database elements."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    booking_repository_instance._bookings.clear()
    department_repository_instance._departments.clear()

    pwd = "Password123!"
    admin = User(email="admin-book@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    dept = Department(name="R&D")
    await department_repository_instance.create(dept)

    emp = User(email="emp-book@assetflow.com", hashed_password=hash_password(pwd), name="Employee Booker", role=Role.EMPLOYEE, department_id=dept.id)
    await user_repository_instance.create(emp)

    emp_other = User(email="other@assetflow.com", hashed_password=hash_password(pwd), name="Other Employee", role=Role.EMPLOYEE)
    await user_repository_instance.create(emp_other)

    dept_head = User(email="head-book@assetflow.com", hashed_password=hash_password(pwd), name="Dept Head", role=Role.DEPARTMENT_HEAD, department_id=dept.id)
    await user_repository_instance.create(dept_head)

    cat = AssetCategory(name="Electronics")
    await asset_category_repository_instance.create(cat)

    asset_bookable = Asset(
        name="Conference Room A",
        category_id=cat.id,
        serial_number="ROOM-A",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=5000.0,
        condition="NEW",
        location="HQ - Floor 1",
        is_bookable=True,
        asset_tag="AF-0001"
    )
    await asset_repository_instance.create(asset_bookable)

    asset_non_bookable = Asset(
        name="Private Desk Laptop",
        category_id=cat.id,
        serial_number="LAPTOP-NB",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=1500.0,
        condition="GOOD",
        location="HQ",
        is_bookable=False,
        asset_tag="AF-0002"
    )
    await asset_repository_instance.create(asset_non_bookable)

    # Login Admin
    form_admin = {"username": admin.email, "password": pwd}
    res_admin = await client.post("/api/v1/auth/login", data=form_admin)
    token_admin = res_admin.json()["data"]["access_token"]

    # Login Employee
    form_emp = {"username": emp.email, "password": pwd}
    res_emp = await client.post("/api/v1/auth/login", data=form_emp)
    token_emp = res_emp.json()["data"]["access_token"]

    # Login Dept Head
    form_head = {"username": dept_head.email, "password": pwd}
    res_head = await client.post("/api/v1/auth/login", data=form_head)
    token_head = res_head.json()["data"]["access_token"]

    return {
        "admin_headers": {"Authorization": f"Bearer {token_admin}"},
        "emp_headers": {"Authorization": f"Bearer {token_emp}"},
        "head_headers": {"Authorization": f"Bearer {token_head}"},
        "emp": emp,
        "emp_other": emp_other,
        "asset_bookable": asset_bookable,
        "asset_non_bookable": asset_non_bookable,
        "dept": dept
    }


async def test_create_booking_success(client: AsyncClient):
    """Verify that creating a booking works with valid inputs."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    payload = {
        "asset_id": data["asset_bookable"].id,
        "start_time": start,
        "end_time": end
    }

    response = await client.post("/api/v1/bookings", json=payload, headers=headers)
    assert response.status_code == 201
    res_data = response.json()["data"]
    assert res_data["status"] == "UPCOMING"
    assert res_data["booked_by"] == data["emp"].id


async def test_create_booking_validation_failures(client: AsyncClient):
    """Verify validations: non-bookable block, past-date block, and invalid range block."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    # 1. Non-bookable asset block -> 409
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    res_nb = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_non_bookable"].id,
        "start_time": start,
        "end_time": end
    }, headers=headers)
    assert res_nb.status_code == 409

    # 2. Past-date block -> 422
    past_start = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    past_end = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    res_past = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": past_start,
        "end_time": past_end
    }, headers=headers)
    assert res_past.status_code == 422
    assert "start time must be in the future" in res_past.json()["error"]["message"]

    # 3. Invalid range end_time <= start_time -> 422
    invalid_end = start
    res_inv = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": start,
        "end_time": invalid_end
    }, headers=headers)
    assert res_inv.status_code == 422


async def test_booking_overlap_validation(client: AsyncClient):
    """Verify strict inequality overlap: conflicting checkouts block, touching ranges succeed."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    # Create first booking: 9:00 - 10:00 tomorrow
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    b1_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    b1_end = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()

    res1 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b1_start,
        "end_time": b1_end
    }, headers=headers)
    assert res1.status_code == 201

    # Attempt overlapping checkout: 9:30 - 10:30 -> Should block with 409
    b2_start = tomorrow.replace(hour=9, minute=30, second=0, microsecond=0).isoformat()
    b2_end = tomorrow.replace(hour=10, minute=30, second=0, microsecond=0).isoformat()
    res2 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b2_start,
        "end_time": b2_end
    }, headers=headers)
    assert res2.status_code == 409

    # Attempt touching range checkout: 10:00 - 11:00 -> Should succeed
    b3_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    b3_end = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()
    res3 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b3_start,
        "end_time": b3_end
    }, headers=headers)
    assert res3.status_code == 201


async def test_cancel_and_reschedule_bookings(client: AsyncClient):
    """Verify cancellation and reschedule operations."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    # 1. Create booking
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    res_create = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": start,
        "end_time": end
    }, headers=headers)
    booking_id = res_create.json()["data"]["id"]

    # 2. Reschedule booking to another time slot
    new_start = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    new_end = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    res_resched = await client.patch(f"/api/v1/bookings/{booking_id}/reschedule", json={
        "start_time": new_start,
        "end_time": new_end
    }, headers=headers)
    assert res_resched.status_code == 200

    # 3. Cancel booking
    res_cancel = await client.patch(f"/api/v1/bookings/{booking_id}/cancel", json={
        "cancellation_reason": "No longer needed"
    }, headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["data"]["status"] == "CANCELLED"


async def test_rbac_booking_endpoints(client: AsyncClient):
    """Verify cancellation permissions for bookers, department heads, and non-related employees."""
    data = await _seed_data(client)
    headers_admin = data["admin_headers"]
    headers_emp = data["emp_headers"]
    headers_head = data["head_headers"]

    # Booker creates booking on behalf of research department
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    res_create = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": start,
        "end_time": end,
        "booked_for_department_id": data["dept"].id
    }, headers=headers_emp)
    booking_id = res_create.json()["data"]["id"]

    # Seed non-related employee
    pwd = "Password123!"
    form_other = {"username": data["emp_other"].email, "password": pwd}
    res_other = await client.post("/api/v1/auth/login", data=form_other)
    token_other = res_other.json()["data"]["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # 1. Other employee tries to cancel -> Should fail with 403
    res_fail = await client.patch(f"/api/v1/bookings/{booking_id}/cancel", json={"cancellation_reason": "Hijack"}, headers=headers_other)
    assert res_fail.status_code == 403

    # 2. Booker's Department Head cancels -> Should succeed (200)
    res_ok = await client.patch(f"/api/v1/bookings/{booking_id}/cancel", json={"cancellation_reason": "Head override"}, headers=headers_head)
    assert res_ok.status_code == 200


async def test_touching_boundary_booking_allowed(client: AsyncClient):
    """Verify that touching but non-overlapping boundaries are allowed."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    b1_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    b1_end = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()

    res1 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b1_start,
        "end_time": b1_end
    }, headers=headers)
    assert res1.status_code == 201

    # Touching boundary: starts exactly at 10:00 when first ends.
    b2_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    b2_end = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()

    res2 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b2_start,
        "end_time": b2_end
    }, headers=headers)
    assert res2.status_code == 201


async def test_overlap_ignores_cancelled_bookings(client: AsyncClient):
    """Verify that a cancelled booking does not block a new booking for the same slot."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    b1_start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()
    b1_end = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()

    res1 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b1_start,
        "end_time": b1_end
    }, headers=headers)
    assert res1.status_code == 201
    booking_id = res1.json()["data"]["id"]

    # Cancel the booking
    res_cancel = await client.patch(f"/api/v1/bookings/{booking_id}/cancel", json={
        "cancellation_reason": "Change of plans"
    }, headers=headers)
    assert res_cancel.status_code == 200

    # Book the exact same slot again
    res2 = await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": b1_start,
        "end_time": b1_end
    }, headers=headers)
    assert res2.status_code == 201


async def test_list_bookings_starting_within(client: AsyncClient):
    """Verify list_bookings_starting_within retrieves only the correct bookings."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    # Clear all bookings to have a clean state for starting_within check
    booking_repository_instance._bookings.clear()

    # Create additional bookable assets to prevent overlap conflicts
    from app.domain.asset import Asset
    cat_id = data["asset_bookable"].category_id
    asset2 = Asset(
        name="Conference Room B",
        category_id=cat_id,
        serial_number="ROOM-B",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=5000.0,
        condition="NEW",
        location="HQ - Floor 1",
        is_bookable=True,
        asset_tag="AF-0003"
    )
    await asset_repository_instance.create(asset2)

    asset3 = Asset(
        name="Conference Room C",
        category_id=cat_id,
        serial_number="ROOM-C",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=5000.0,
        condition="NEW",
        location="HQ - Floor 1",
        is_bookable=True,
        asset_tag="AF-0004"
    )
    await asset_repository_instance.create(asset3)

    # 1. Booking starting in 15 mins (within 30 mins window)
    start_within = (datetime.now(timezone.utc) + timedelta(minutes=15))
    end_within = start_within + timedelta(hours=1)
    await client.post("/api/v1/bookings", json={
        "asset_id": data["asset_bookable"].id,
        "start_time": start_within.isoformat(),
        "end_time": end_within.isoformat()
    }, headers=headers)

    # 2. Booking starting in 45 mins (outside 30 mins window)
    start_outside = (datetime.now(timezone.utc) + timedelta(minutes=45))
    end_outside = start_outside + timedelta(hours=1)
    await client.post("/api/v1/bookings", json={
        "asset_id": asset2.id,
        "start_time": start_outside.isoformat(),
        "end_time": end_outside.isoformat()
    }, headers=headers)

    # 3. Booking starting in 10 mins but cancelled
    start_cancelled = (datetime.now(timezone.utc) + timedelta(minutes=10))
    end_cancelled = start_cancelled + timedelta(hours=1)
    res_cancelled = await client.post("/api/v1/bookings", json={
        "asset_id": asset3.id,
        "start_time": start_cancelled.isoformat(),
        "end_time": end_cancelled.isoformat()
    }, headers=headers)
    cancelled_id = res_cancelled.json()["data"]["id"]
    await client.patch(f"/api/v1/bookings/{cancelled_id}/cancel", json={"cancellation_reason": "cancel"}, headers=headers)

    # Fetch from repository directly to prove the repository method works
    results = await booking_repository_instance.list_bookings_starting_within(30)
    assert len(results) == 1
    # Check start time is matching within
    assert abs((results[0].start_time.replace(tzinfo=timezone.utc) - start_within).total_seconds()) < 5


async def test_booking_lifecycle_status_computed(client: AsyncClient):
    """Verify that computed_status behaves correctly across CANCELLED, UPCOMING, ONGOING, and COMPLETED states."""
    data = await _seed_data(client)
    from app.domain.booking import Booking

    # 1. UPCOMING
    b_upcoming = Booking(
        asset_id=data["asset_bookable"].id,
        booked_by=data["emp"].id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2)
    )
    assert b_upcoming.computed_status == "UPCOMING"

    # 2. ONGOING
    b_ongoing = Booking(
        asset_id=data["asset_bookable"].id,
        booked_by=data["emp"].id,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    assert b_ongoing.computed_status == "ONGOING"

    # 3. COMPLETED
    b_completed = Booking(
        asset_id=data["asset_bookable"].id,
        booked_by=data["emp"].id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        end_time=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    assert b_completed.computed_status == "COMPLETED"

    # 4. CANCELLED
    b_cancelled = Booking(
        asset_id=data["asset_bookable"].id,
        booked_by=data["emp"].id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        cancelled_at=datetime.now(timezone.utc)
    )
    assert b_cancelled.computed_status == "CANCELLED"



