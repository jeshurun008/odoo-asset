from datetime import datetime, timezone
from typing import Dict, Optional, Set
from app.domain.maintenance_request import MaintenanceRequest, MaintenanceStatus, MaintenancePriority
from app.domain.asset import AssetStatus
from app.exceptions.exceptions import ConflictException, NotFoundException
from app.logging.logger import business_logger
from app.repositories.maintenance_request import AbstractMaintenanceRequestRepository
from app.repositories.asset import AbstractAssetRepository
from app.services.asset_lifecycle_service import AssetLifecycleService

# Explicit Maintenance Workflow State Transition Matrix
MAINTENANCE_TRANSITIONS: Dict[MaintenanceStatus, Set[MaintenanceStatus]] = {
    MaintenanceStatus.PENDING: {MaintenanceStatus.APPROVED, MaintenanceStatus.REJECTED},
    MaintenanceStatus.APPROVED: {MaintenanceStatus.TECHNICIAN_ASSIGNED},
    MaintenanceStatus.TECHNICIAN_ASSIGNED: {MaintenanceStatus.IN_PROGRESS},
    MaintenanceStatus.IN_PROGRESS: {MaintenanceStatus.RESOLVED},
    MaintenanceStatus.REJECTED: set(),
    MaintenanceStatus.RESOLVED: set()
}


class MaintenanceService:
    """
    Service Layer managing Asset Maintenance requests, approval status workflows,
    technician assignment logs, and asset lifecycle integration.
    """
    def __init__(
        self,
        maintenance_repository: AbstractMaintenanceRequestRepository,
        asset_repository: AbstractAssetRepository,
        lifecycle_service: AssetLifecycleService
    ):
        self.maintenance_repo = maintenance_repository
        self.asset_repo = asset_repository
        self.lifecycle_service = lifecycle_service

    async def raise_request(
        self,
        asset_id: str,
        raised_by: str,
        issue_description: str,
        priority: MaintenancePriority,
        photo_ref: Optional[str] = None
    ) -> MaintenanceRequest:
        """Raises a new maintenance request, validating that no duplicate unresolved request is active."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        # 1. Validation: check for open/unresolved request for this asset
        open_reqs = await self.maintenance_repo.list_unresolved_by_asset(asset_id)
        if open_reqs:
            raise ConflictException("An active maintenance request is already open for this asset.")

        new_req = MaintenanceRequest(
            asset_id=asset_id,
            raised_by=raised_by,
            issue_description=issue_description,
            priority=priority,
            photo_ref=photo_ref
        )
        created = await self.maintenance_repo.create(new_req)
        business_logger.info(f"Maintenance request raised for asset '{asset.asset_tag}' (ID: {created.id})")
        return created

    async def approve_request(self, request_id: str, approver_id: str) -> MaintenanceRequest:
        """Approves a request, caching the pre-maintenance asset status and moving asset to UNDER_MAINTENANCE."""
        req = await self.maintenance_repo.get_by_id(request_id)
        if not req:
            raise NotFoundException(f"Maintenance request with ID {request_id} not found.")

        # Validate workflow path
        self._validate_transition(req.status, MaintenanceStatus.APPROVED)

        asset = await self.asset_repo.get_by_id(req.asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {req.asset_id} not found.")

        # Cache pre-maintenance asset status
        req.pre_maintenance_asset_status = asset.status

        # Transition Asset to UNDER_MAINTENANCE
        await self.lifecycle_service.transition_to(
            asset=asset,
            target_status=AssetStatus.UNDER_MAINTENANCE,
            actor_id=approver_id,
            reason=f"Asset maintenance approved (Request ID: {request_id})"
        )

        req.status = MaintenanceStatus.APPROVED
        req.approved_by = approver_id
        req.updated_at = datetime.now(timezone.utc)

        updated = await self.maintenance_repo.update(req)
        business_logger.info(f"Maintenance request approved: ID {request_id}")
        return updated

    async def reject_request(self, request_id: str, rejected_by: str, reason: str) -> MaintenanceRequest:
        """Rejects a request, leaving the asset status untouched."""
        if not reason or not reason.strip():
            raise ConflictException("A rejection reason is required.")

        req = await self.maintenance_repo.get_by_id(request_id)
        if not req:
            raise NotFoundException(f"Maintenance request with ID {request_id} not found.")

        # Validate workflow path
        self._validate_transition(req.status, MaintenanceStatus.REJECTED)

        req.status = MaintenanceStatus.REJECTED
        req.approved_by = rejected_by
        req.rejected_reason = reason
        req.resolved_at = datetime.now(timezone.utc)
        req.updated_at = datetime.now(timezone.utc)

        updated = await self.maintenance_repo.update(req)
        business_logger.info(f"Maintenance request rejected: ID {request_id}")
        return updated

    async def assign_technician(self, request_id: str, technician_name: str, actor_id: str) -> MaintenanceRequest:
        """Assigns a technician to the approved maintenance request."""
        if not technician_name or not technician_name.strip():
            raise ConflictException("Technician name is required.")

        req = await self.maintenance_repo.get_by_id(request_id)
        if not req:
            raise NotFoundException(f"Maintenance request with ID {request_id} not found.")

        # Validate workflow path
        self._validate_transition(req.status, MaintenanceStatus.TECHNICIAN_ASSIGNED)

        req.status = MaintenanceStatus.TECHNICIAN_ASSIGNED
        req.assigned_technician = technician_name
        req.updated_at = datetime.now(timezone.utc)

        updated = await self.maintenance_repo.update(req)
        business_logger.info(f"Maintenance request assigned to technician '{technician_name}': ID {request_id}")
        return updated

    async def start_work(self, request_id: str, actor_id: str) -> MaintenanceRequest:
        """Moves request from TECHNICIAN_ASSIGNED to IN_PROGRESS."""
        req = await self.maintenance_repo.get_by_id(request_id)
        if not req:
            raise NotFoundException(f"Maintenance request with ID {request_id} not found.")

        # Validate workflow path
        self._validate_transition(req.status, MaintenanceStatus.IN_PROGRESS)

        req.status = MaintenanceStatus.IN_PROGRESS
        req.updated_at = datetime.now(timezone.utc)

        updated = await self.maintenance_repo.update(req)
        business_logger.info(f"Maintenance work started: ID {request_id}")
        return updated

    async def resolve_request(self, request_id: str, actor_id: str) -> MaintenanceRequest:
        """Resolves request, returning the asset to its correct pre-maintenance status (ALLOCATED or AVAILABLE)."""
        req = await self.maintenance_repo.get_by_id(request_id)
        if not req:
            raise NotFoundException(f"Maintenance request with ID {request_id} not found.")

        # Validate workflow path
        self._validate_transition(req.status, MaintenanceStatus.RESOLVED)

        asset = await self.asset_repo.get_by_id(req.asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {req.asset_id} not found.")

        # Revert Asset Status based on cached pre-maintenance status
        target_status = AssetStatus.AVAILABLE
        if req.pre_maintenance_asset_status == AssetStatus.ALLOCATED:
            target_status = AssetStatus.ALLOCATED

        await self.lifecycle_service.transition_to(
            asset=asset,
            target_status=target_status,
            actor_id=actor_id,
            reason=f"Maintenance resolved. Reverting to prior status: {target_status}"
        )

        req.status = MaintenanceStatus.RESOLVED
        req.resolved_at = datetime.now(timezone.utc)
        req.updated_at = datetime.now(timezone.utc)

        updated = await self.maintenance_repo.update(req)
        business_logger.info(f"Maintenance request resolved: ID {request_id}")
        return updated

    def _validate_transition(self, current: MaintenanceStatus, target: MaintenanceStatus) -> None:
        """Enforces the maintenance workflow transition matrix rules."""
        allowed = MAINTENANCE_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ConflictException(
                f"Invalid maintenance transition. Cannot transition request from state '{current}' to '{target}'."
            )
