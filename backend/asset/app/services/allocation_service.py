from datetime import datetime, timezone
from typing import Optional
from app.domain.allocation import AssetAllocation
from app.domain.asset import AssetStatus
from app.domain.user import Role
from app.exceptions.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.logging.logger import business_logger
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.repositories.asset import AbstractAssetRepository
from app.repositories.user import AbstractUserRepository
from app.repositories.department import AbstractDepartmentRepository
from app.services.asset_lifecycle_service import AssetLifecycleService


class AllocationService:
    """
    Service Layer managing Asset Allocation checkouts, return check-ins,
    double allocation prevention, and overdue reporting.
    """
    def __init__(
        self,
        alloc_repository: AbstractAssetAllocationRepository,
        asset_repository: AbstractAssetRepository,
        user_repository: AbstractUserRepository,
        dept_repository: AbstractDepartmentRepository,
        lifecycle_service: AssetLifecycleService
    ):
        self.alloc_repo = alloc_repository
        self.asset_repo = asset_repository
        self.user_repo = user_repository
        self.dept_repo = dept_repository
        self.lifecycle_service = lifecycle_service

    async def allocate_asset(
        self,
        asset_id: str,
        allocated_to_type: str,  # "EMPLOYEE" or "DEPARTMENT"
        allocated_to_id: str,
        allocated_by: str,
        expected_return_date: Optional[datetime] = None
    ) -> AssetAllocation:
        """Performs checkout allocation, ensuring availability and blocking double-allocation."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        # 1. Check for active allocations (to prevent double checkout and report holder name)
        active_allocs = await self.alloc_repo.list_active_by_asset(asset_id)
        if active_allocs:
            active = active_allocs[0]
            holder_name = "Unknown"
            if active.allocated_to_type == "EMPLOYEE":
                holder = await self.user_repo.get_by_id(active.allocated_to_id)
                if holder:
                    holder_name = holder.name
            else:
                holder = await self.dept_repo.get_by_id(active.allocated_to_id)
                if holder:
                    holder_name = holder.name
            raise ConflictException(
                f"Asset is currently held by {holder_name}."
            )

        # 2. Availability validation (allow AVAILABLE or RESERVED states)
        if asset.status not in (AssetStatus.AVAILABLE, AssetStatus.RESERVED):
            raise ConflictException(f"Asset '{asset.asset_tag}' is currently unavailable (Status: {asset.status}).")

        # 3. Recipient existence & active status validation
        if allocated_to_type == "EMPLOYEE":
            recipient = await self.user_repo.get_by_id(allocated_to_id)
            if not recipient:
                raise NotFoundException(f"Employee recipient with ID {allocated_to_id} not found.")
            if not recipient.is_active:
                raise ConflictException("Cannot allocate assets to an inactive employee account.")
        elif allocated_to_type == "DEPARTMENT":
            recipient = await self.dept_repo.get_by_id(allocated_to_id)
            if not recipient:
                raise NotFoundException(f"Department recipient with ID {allocated_to_id} not found.")
            if not recipient.is_active:
                raise ConflictException("Cannot allocate assets to an inactive department.")
        else:
            raise ConflictException(f"Invalid allocation recipient type '{allocated_to_type}'.")

        # 4. Create checkout record
        new_alloc = AssetAllocation(
            asset_id=asset_id,
            allocated_to_type=allocated_to_type,
            allocated_to_id=allocated_to_id,
            allocated_by=allocated_by,
            expected_return_date=expected_return_date
        )
        created = await self.alloc_repo.create(new_alloc)

        # 5. Transition lifecycle status to ALLOCATED
        await self.lifecycle_service.transition_to(
            asset=asset,
            target_status=AssetStatus.ALLOCATED,
            actor_id=allocated_by,
            reason=f"Checked out to {allocated_to_type} ID: {allocated_to_id}"
        )

        business_logger.info(f"Asset '{asset.asset_tag}' allocated to {allocated_to_type} '{allocated_to_id}'")
        return created

    async def return_asset(
        self,
        allocation_id: str,
        condition_check_in_notes: str,
        return_actor_id: str
    ) -> AssetAllocation:
        """Performs check-in return, releasing asset status back to AVAILABLE."""
        alloc = await self.alloc_repo.get_by_id(allocation_id)
        if not alloc:
            raise NotFoundException(f"Asset Allocation record with ID {allocation_id} not found.")

        if alloc.returned_at is not None:
            raise ConflictException("Asset is not currently allocated.")

        asset = await self.asset_repo.get_by_id(alloc.asset_id)
        if not asset:
            raise NotFoundException(f"Linked asset with ID {alloc.asset_id} not found.")

        # 1. Enforce Department Head return permission scoping
        actor = await self.user_repo.get_by_id(return_actor_id)
        if not actor:
            raise NotFoundException(f"Actor user with ID {return_actor_id} not found.")

        if actor.role == Role.DEPARTMENT_HEAD:
            # Must scope check-in permission to their department
            if alloc.allocated_to_type == "DEPARTMENT":
                if alloc.allocated_to_id != actor.department_id:
                    raise ForbiddenException("Department heads can only check-in assets within their department.")
            else:
                # Employee checkout return: employee must belong to dept head's department
                recipient = await self.user_repo.get_by_id(alloc.allocated_to_id)
                if not recipient or recipient.department_id != actor.department_id:
                    raise ForbiddenException("Department heads can only check-in assets within their department.")

        # 2. Record Return Check-in fields
        alloc.returned_at = datetime.now(timezone.utc)
        alloc.condition_check_in_notes = condition_check_in_notes
        updated_alloc = await self.alloc_repo.update(alloc)

        # 3. Transition status back to AVAILABLE
        await self.lifecycle_service.transition_to(
            asset=asset,
            target_status=AssetStatus.AVAILABLE,
            actor_id=return_actor_id,
            reason=f"Returned check-in. Condition notes: {condition_check_in_notes}"
        )

        business_logger.info(f"Asset '{asset.asset_tag}' returned check-in completed.")
        return updated_alloc
