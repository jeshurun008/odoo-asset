from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.domain.asset import Asset, AssetStatus
from app.exceptions.exceptions import ConflictException, NotFoundException, ValidationException
from app.logging.logger import business_logger
from app.repositories.asset import AbstractAssetRepository
from app.repositories.asset_category import AbstractAssetCategoryRepository
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.repositories.transfer_request import AbstractTransferRequestRepository
from app.repositories.maintenance_request import AbstractMaintenanceRequestRepository


class AssetService:
    """
    Service Layer managing Asset Directory inventory, registrations, property updates,
    and history logs.
    """
    def __init__(
        self,
        asset_repository: AbstractAssetRepository,
        category_repository: AbstractAssetCategoryRepository,
        allocation_repository: AbstractAssetAllocationRepository,
        transfer_repository: Optional[AbstractTransferRequestRepository] = None,
        maintenance_repository: Optional[AbstractMaintenanceRequestRepository] = None
    ):
        self.asset_repo = asset_repository
        self.cat_repo = category_repository
        self.alloc_repo = allocation_repository
        self.transfer_repo = transfer_repository
        self.maintenance_repo = maintenance_repository

    async def register_asset(
        self,
        name: str,
        category_id: str,
        serial_number: str,
        acquisition_date: datetime,
        acquisition_cost: float,
        condition: str,
        location: str,
        department_id: Optional[str] = None,
        is_bookable: bool = False,
        document_refs: Optional[List[str]] = None
    ) -> Asset:
        """Registers a new capital asset, generating a sequential tag and verifying category status."""
        # 1. Verify Category exists and is Active
        category = await self.cat_repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(f"Asset Category with ID {category_id} not found.")
        if not category.is_active:
            raise ConflictException(f"Asset Category '{category.name}' is inactive. Cannot link assets.")

        # 2. Race-safe sequential tag generation
        asset_tag = await self.asset_repo.generate_next_tag()

        # 3. Verify Serial Number uniqueness among active assets
        # In a real system, serial numbers must be unique within category or overall.
        # We search matching serial numbers.
        _, total_matching = await self.asset_repo.list_paginated(
            limit=1,
            filters={"serial_number": serial_number}
        )
        if total_matching > 0:
            raise ConflictException(f"Asset with serial number '{serial_number}' is already registered.")

        new_asset = Asset(
            name=name,
            category_id=category_id,
            serial_number=serial_number,
            acquisition_date=acquisition_date,
            acquisition_cost=acquisition_cost,
            condition=condition,
            location=location,
            department_id=department_id,
            is_bookable=is_bookable,
            document_refs=document_refs or [],
            status=AssetStatus.AVAILABLE,
            asset_tag=asset_tag
        )

        created = await self.asset_repo.create(new_asset)
        business_logger.info(f"Asset registered: '{created.name}' (Tag: {created.asset_tag})")
        return created

    async def update_asset(
        self,
        asset_id: str,
        name: Optional[str] = None,
        category_id: Optional[str] = None,
        serial_number: Optional[str] = None,
        acquisition_date: Optional[datetime] = None,
        acquisition_cost: Optional[float] = None,
        condition: Optional[str] = None,
        location: Optional[str] = None,
        department_id: Optional[str] = None,
        is_bookable: Optional[bool] = None,
        document_refs: Optional[List[str]] = None
    ) -> Asset:
        """Updates non-lifecycle properties of an asset."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        if category_id:
            category = await self.cat_repo.get_by_id(category_id)
            if not category:
                raise NotFoundException(f"Asset Category with ID {category_id} not found.")
            if not category.is_active:
                raise ConflictException("Cannot link to inactive category.")
            asset.category_id = category_id

        if name is not None:
            asset.name = name
        if serial_number is not None:
            asset.serial_number = serial_number
        if acquisition_date is not None:
            asset.acquisition_date = acquisition_date
        if acquisition_cost is not None:
            asset.acquisition_cost = acquisition_cost
        if condition is not None:
            asset.condition = condition
        if location is not None:
            asset.location = location
        if department_id is not None:
            asset.department_id = department_id if department_id != "" else None
        if is_bookable is not None:
            asset.is_bookable = is_bookable
        if document_refs is not None:
            asset.document_refs = document_refs

        asset.updated_at = datetime.now(timezone.utc)
        updated = await self.asset_repo.update(asset)
        business_logger.info(f"Asset properties updated: '{updated.asset_tag}'")
        return updated

    async def get_asset_history(self, asset_id: str) -> Dict[str, Any]:
        """Aggregates all allocation histories and provides integration stubs for maintenance logs."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        # Fetch allocations from repository
        allocations = await self.alloc_repo.list_by_asset(asset_id)

        # Fetch transfers from repository
        transfers = []
        if self.transfer_repo:
            transfers, _ = await self.transfer_repo.list_paginated(
                limit=1000,
                filters={"asset_id": asset_id}
            )

        # Fetch maintenance history from repository
        maintenance = []
        if self.maintenance_repo:
            maintenance, _ = await self.maintenance_repo.list_paginated(
                limit=1000,
                filters={"asset_id": asset_id}
            )

        return {
            "asset_id": asset_id,
            "asset_tag": asset.asset_tag,
            "allocations": allocations,
            "transfers": transfers,
            "maintenance_history": maintenance
        }
