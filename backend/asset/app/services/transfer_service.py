import asyncio
from datetime import datetime, timezone
from typing import Optional
from app.domain.allocation import AssetAllocation
from app.domain.transfer_request import TransferRequest
from app.domain.user import Role
from app.exceptions.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.logging.logger import business_logger
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.repositories.asset import AbstractAssetRepository
from app.repositories.user import AbstractUserRepository
from app.repositories.department import AbstractDepartmentRepository
from app.repositories.transfer_request import AbstractTransferRequestRepository
from app.domain.notification import NotificationType


class TransferService:
    """
    Service Layer managing Asset Transfer requests, approvals, rejections,
    and atomic checkout updates.
    """
    def __init__(
        self,
        transfer_repository: AbstractTransferRequestRepository,
        alloc_repository: AbstractAssetAllocationRepository,
        asset_repository: AbstractAssetRepository,
        user_repository: AbstractUserRepository,
        dept_repository: AbstractDepartmentRepository,
        notification_service=None
    ):
        self.transfer_repo = transfer_repository
        self.alloc_repo = alloc_repository
        self.asset_repo = asset_repository
        self.user_repo = user_repository
        self.dept_repo = dept_repository
        self.notification_service = notification_service
        self._lock = asyncio.Lock()

    async def create_transfer_request(
        self,
        asset_id: str,
        requested_by: str,
        requested_to_type: str,  # "EMPLOYEE" or "DEPARTMENT"
        requested_to_id: str,
        reason: Optional[str] = None
    ) -> TransferRequest:
        """Submits a new Transfer request, validating active allocations and recipient status."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        # 1. Verify there is an active allocation to transfer
        active_allocs = await self.alloc_repo.list_active_by_asset(asset_id)
        if not active_allocs:
            raise ConflictException(f"Cannot request transfer. Asset '{asset.asset_tag}' has no active allocation.")
        active_alloc = active_allocs[0]

        # 2. Reject if a pending transfer request already exists for this asset
        pending = await self.transfer_repo.list_pending_by_asset(asset_id)
        if pending:
            raise ConflictException("A pending transfer request already exists for this asset.")

        # 3. Validate recipient status
        if requested_to_type == "EMPLOYEE":
            recipient = await self.user_repo.get_by_id(requested_to_id)
            if not recipient:
                raise NotFoundException(f"Target employee with ID {requested_to_id} not found.")
            if not recipient.is_active:
                raise ConflictException("Cannot transfer asset to an inactive employee account.")
        elif requested_to_type == "DEPARTMENT":
            recipient = await self.dept_repo.get_by_id(requested_to_id)
            if not recipient:
                raise NotFoundException(f"Target department with ID {requested_to_id} not found.")
            if not recipient.is_active:
                raise ConflictException("Cannot transfer asset to an inactive department.")
        else:
            raise ConflictException(f"Invalid transfer target type '{requested_to_type}'.")

        new_req = TransferRequest(
            asset_id=asset_id,
            current_allocation_id=active_alloc.id,
            requested_by=requested_by,
            requested_to_type=requested_to_type,
            requested_to_id=requested_to_id,
            reason=reason
        )
        created = await self.transfer_repo.create(new_req)
        business_logger.info(f"Transfer requested: Asset '{asset.asset_tag}' -> '{requested_to_id}'")
        return created

    async def approve_transfer(self, transfer_id: str, approver_id: str) -> TransferRequest:
        """Atomically approves the transfer, closing the old checkout and checking out to the recipient."""
        # Use central service lock to guarantee atomicity of the multiple mock repository updates
        async with self._lock:
            req = await self.transfer_repo.get_by_id(transfer_id)
            if not req:
                raise NotFoundException(f"Transfer request with ID {transfer_id} not found.")

            if req.status != "REQUESTED":
                raise ConflictException(f"Cannot approve transfer request in '{req.status}' state.")

            asset = await self.asset_repo.get_by_id(req.asset_id)
            if not asset:
                raise NotFoundException(f"Linked asset with ID {req.asset_id} not found.")

            # 1. Enforce Department Head approval scoping checks
            approver = await self.user_repo.get_by_id(approver_id)
            if not approver:
                raise NotFoundException(f"Approver user with ID {approver_id} not found.")

            # Fetch active old allocation record
            old_alloc = await self.alloc_repo.get_by_id(req.current_allocation_id)
            if not old_alloc or old_alloc.returned_at is not None:
                raise ConflictException("Current active allocation has been modified or returned already.")

            if approver.role == Role.DEPARTMENT_HEAD:
                # Must check if the active asset currently belongs to the head's department
                if old_alloc.allocated_to_type == "DEPARTMENT":
                    if old_alloc.allocated_to_id != approver.department_id:
                        raise ForbiddenException("Department heads can only approve transfers within their department.")
                else:
                    holder = await self.user_repo.get_by_id(old_alloc.allocated_to_id)
                    if not holder or holder.department_id != approver.department_id:
                        raise ForbiddenException("Department heads can only approve transfers within their department.")

            # 2. Close old allocation checkout
            old_alloc.returned_at = datetime.now(timezone.utc)
            old_alloc.condition_check_in_notes = f"Closed via Transfer Approval (Request ID: {transfer_id})"
            await self.alloc_repo.update(old_alloc)

            # 3. Create new allocation checkout directly (asset remains ALLOCATED status throughout)
            new_alloc = AssetAllocation(
                asset_id=req.asset_id,
                allocated_to_type=req.requested_to_type,
                allocated_to_id=req.requested_to_id,
                allocated_by=approver_id,
                expected_return_date=old_alloc.expected_return_date
            )
            await self.alloc_repo.create(new_alloc)

            # 4. Resolve Transfer Request as COMPLETED
            req.status = "COMPLETED"
            req.approved_by = approver_id
            req.resolved_at = datetime.now(timezone.utc)
            updated_req = await self.transfer_repo.update(req)

            business_logger.info(f"Transfer APPROVED and COMPLETED: Transfer ID {transfer_id}")
            if self.notification_service and req.requested_to_type == "EMPLOYEE":
                await self.notification_service.notify(req.requested_to_id, NotificationType.TRANSFER_APPROVED, {"entity_id": req.id, "entity_type": "transfer", "message": "Your asset transfer was approved."})
            return updated_req

    async def reject_transfer(self, transfer_id: str, resolver_id: str, reason: Optional[str] = None) -> TransferRequest:
        """Rejects the transfer request, leaving allocations and assets unmodified."""
        req = await self.transfer_repo.get_by_id(transfer_id)
        if not req:
            raise NotFoundException(f"Transfer request with ID {transfer_id} not found.")

        if req.status != "REQUESTED":
            raise ConflictException(f"Cannot resolve transfer request in '{req.status}' state.")

        # Enforce Department Head scoping checks
        approver = await self.user_repo.get_by_id(resolver_id)
        if not approver:
            raise NotFoundException(f"Approver user with ID {resolver_id} not found.")

        old_alloc = await self.alloc_repo.get_by_id(req.current_allocation_id)
        if not old_alloc:
            raise ConflictException("Current allocation record missing.")

        if approver.role == Role.DEPARTMENT_HEAD:
            if old_alloc.allocated_to_type == "DEPARTMENT":
                if old_alloc.allocated_to_id != approver.department_id:
                    raise ForbiddenException("Department heads can only reject transfers within their department.")
            else:
                holder = await self.user_repo.get_by_id(old_alloc.allocated_to_id)
                if not holder or holder.department_id != approver.department_id:
                    raise ForbiddenException("Department heads can only reject transfers within their department.")

        req.status = "REJECTED"
        req.approved_by = resolver_id
        req.reason = reason
        req.resolved_at = datetime.now(timezone.utc)
        updated_req = await self.transfer_repo.update(req)

        business_logger.info(f"Transfer REJECTED: Transfer ID {transfer_id}")
        return updated_req
