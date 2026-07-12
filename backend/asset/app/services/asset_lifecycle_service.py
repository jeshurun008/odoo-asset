from datetime import datetime, timezone
from typing import Dict, Optional, Set
from app.domain.asset import Asset, AssetStatus
from app.exceptions.exceptions import ConflictException
from app.logging.logger import business_logger
from app.repositories.asset import AbstractAssetRepository

# The official Phase 3 Asset Lifecycle Transition Table
ALLOWED_TRANSITIONS: Dict[AssetStatus, Set[AssetStatus]] = {
    AssetStatus.AVAILABLE: {
        AssetStatus.ALLOCATED,
        AssetStatus.RESERVED,
        AssetStatus.UNDER_MAINTENANCE,
        AssetStatus.LOST,
        AssetStatus.RETIRED
    },
    AssetStatus.ALLOCATED: {
        AssetStatus.AVAILABLE,
        AssetStatus.UNDER_MAINTENANCE,  # Allow transitioning an allocated asset into repair
        AssetStatus.LOST
    },
    AssetStatus.RESERVED: {
        AssetStatus.AVAILABLE,
        AssetStatus.ALLOCATED           # Allow checking out a reserved asset directly
    },
    AssetStatus.UNDER_MAINTENANCE: {
        AssetStatus.AVAILABLE,
        AssetStatus.ALLOCATED,          # Re-allocated directly after repair
        AssetStatus.LOST
    },
    AssetStatus.LOST: {
        AssetStatus.AVAILABLE,          # Asset was located/recovered
        AssetStatus.RETIRED
    },
    AssetStatus.RETIRED: {
        AssetStatus.DISPOSED
    },
    AssetStatus.DISPOSED: set()         # Terminal state, no outbound transitions allowed
}


class AssetLifecycleService:
    """
    State Machine orchestrator managing Asset Status transitions, validation constraints,
    and history tracing.
    """
    def __init__(self, asset_repository: AbstractAssetRepository):
        self.asset_repo = asset_repository

    async def transition_to(
        self,
        asset: Asset,
        target_status: AssetStatus,
        actor_id: str,
        reason: Optional[str] = None
    ) -> Asset:
        """
        Validates the transition path and updates the asset status.
        Logs the event immutably to the structured business log.
        """
        current_status = asset.status
        if target_status == current_status:
            return asset  # No state change needed

        allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_next:
            raise ConflictException(
                f"Invalid lifecycle transition. Cannot transition asset '{asset.asset_tag}' "
                f"from status '{current_status}' to target status '{target_status}'."
            )

        # Apply state changes
        asset.status = target_status
        asset.updated_at = datetime.now(timezone.utc)
        updated_asset = await self.asset_repo.update(asset)

        # Log transition business activity audit record
        business_logger.info(
            f"LIFECYCLE_TRANSITION: Actor '{actor_id}' transitioned asset '{asset.id}' ({asset.asset_tag}) "
            f"from '{current_status}' to '{target_status}'. Reason: '{reason or 'None provided'}'."
        )
        return updated_asset
