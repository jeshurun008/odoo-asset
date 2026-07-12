from abc import abstractmethod
from typing import List
from app.domain.transfer_request import TransferRequest
from app.repositories.base import AbstractRepository


class AbstractTransferRequestRepository(AbstractRepository[TransferRequest]):
    """Abstract TransferRequest repository interface."""

    @abstractmethod
    async def list_pending_by_asset(self, asset_id: str) -> List[TransferRequest]:
        """Fetch all pending (REQUESTED) transfer requests for a specific asset ID."""
        pass
