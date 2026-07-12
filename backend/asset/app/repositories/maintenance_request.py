from abc import abstractmethod
from typing import List
from app.domain.maintenance_request import MaintenanceRequest
from app.repositories.base import AbstractRepository


class AbstractMaintenanceRequestRepository(AbstractRepository[MaintenanceRequest]):
    """Abstract MaintenanceRequest repository interface."""

    @abstractmethod
    async def list_unresolved_by_asset(self, asset_id: str) -> List[MaintenanceRequest]:
        """Fetch all open/unresolved maintenance requests for a specific asset ID."""
        pass

    @abstractmethod
    async def list_active_today(self) -> List[MaintenanceRequest]:
        """Fetch all maintenance requests active or resolved/raised today (Dashboard feeds hook)."""
        pass

    @abstractmethod
    async def list_maintenance_today(self) -> List[MaintenanceRequest]:
        """Fetch all requests raised today (excluding RESOLVED), or currently IN_PROGRESS/TECHNICIAN_ASSIGNED."""
        pass

