from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.domain.asset_category import AssetCategory
from app.exceptions.exceptions import ConflictException, NotFoundException, ValidationException
from app.logging.logger import business_logger
from app.repositories.asset_category import AbstractAssetCategoryRepository
from app.repositories.asset import AbstractAssetRepository

VALID_FIELD_TYPES = {"TEXT", "NUMBER", "DATE", "BOOLEAN"}


class AssetCategoryService:
    """
    Service Layer managing Asset Categories, custom fields schema validations,
    and asset relationship validation stubs.
    """
    def __init__(
        self,
        category_repository: AbstractAssetCategoryRepository,
        asset_repository: Optional[AbstractAssetRepository] = None
    ):
        self.cat_repo = category_repository
        self.asset_repo = asset_repository

    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        custom_fields: Optional[List[Dict[str, Any]]] = None
    ) -> AssetCategory:
        """Creates a new Asset Category, validating custom fields schemas."""
        # 1. Uniqueness check
        existing = await self.cat_repo.get_by_name(name)
        if existing:
            raise ConflictException(f"Asset Category with name '{name}' already exists.")

        # 2. Custom Fields validation
        fields = custom_fields or []
        self._validate_custom_fields(fields)

        new_cat = AssetCategory(
            name=name,
            description=description,
            custom_fields=fields
        )
        created = await self.cat_repo.create(new_cat)
        business_logger.info(f"Asset Category created: '{created.name}' (ID: {created.id})")
        return created

    async def update_category(
        self,
        cat_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        custom_fields: Optional[List[Dict[str, Any]]] = None
    ) -> AssetCategory:
        """Updates an existing Asset Category and validates schema updates."""
        cat = await self.cat_repo.get_by_id(cat_id)
        if not cat:
            raise NotFoundException(f"Asset Category with ID {cat_id} not found.")

        # 1. Uniqueness check
        if name and name.lower() != cat.name.lower():
            existing = await self.cat_repo.get_by_name(name)
            if existing:
                raise ConflictException(f"Asset Category with name '{name}' already exists.")
            cat.name = name

        if description is not None:
            cat.description = description

        # 2. Custom Fields validation
        if custom_fields is not None:
            self._validate_custom_fields(custom_fields)
            cat.custom_fields = custom_fields

        cat.updated_at = datetime.now(timezone.utc)
        updated = await self.cat_repo.update(cat)
        business_logger.info(f"Asset Category updated: '{updated.name}' (ID: {updated.id})")
        return updated

    async def deactivate_category(self, cat_id: str) -> AssetCategory:
        """Deactivates a category soft-flipping its status, blocking if active assets reference it."""
        cat = await self.cat_repo.get_by_id(cat_id)
        if not cat:
            raise NotFoundException(f"Asset Category with ID {cat_id} not found.")

        if not cat.is_active:
            return cat  # Already inactive

        # 3. Check active assets reference (Phase 3 integration check)
        if self.asset_repo:
            active_count = await self.asset_repo.count_active_by_category(cat_id)
            if active_count > 0:
                raise ConflictException(
                    f"Cannot deactivate category: {active_count} active asset(s) still reference this category."
                )

        cat.is_active = False
        cat.updated_at = datetime.now(timezone.utc)
        updated = await self.cat_repo.update(cat)
        business_logger.info(f"Asset Category deactivated: '{updated.name}' (ID: {updated.id})")
        return updated

    def _validate_custom_fields(self, custom_fields: List[Dict[str, Any]]) -> None:
        """Validates list of custom field dictionaries against types and uniqueness requirements."""
        field_names = set()
        for idx, field in enumerate(custom_fields):
            name = field.get("name")
            field_type = field.get("type")
            required = field.get("required")

            # Basic checks
            if not name or not isinstance(name, str):
                raise ValidationException(
                    message=f"Custom field at index {idx} must possess a string 'name'.",
                    details={"field": "custom_fields"}
                )
            
            if not field_type or field_type.upper() not in VALID_FIELD_TYPES:
                raise ValidationException(
                    message=(
                        f"Custom field '{name}' has invalid type '{field_type}'. "
                        f"Valid types are: {list(VALID_FIELD_TYPES)}"
                    ),
                    details={"field": "custom_fields"}
                )

            if not isinstance(required, bool):
                raise ValidationException(
                    message=f"Custom field '{name}' must possess a boolean 'required' flag.",
                    details={"field": "custom_fields"}
                )

            # Uniqueness check
            normalized_name = name.strip().lower()
            if normalized_name in field_names:
                raise ValidationException(
                    message=f"Duplicate custom field name '{name}' detected in category schema.",
                    details={"field": "custom_fields"}
                )
            field_names.add(normalized_name)

    async def _has_active_assets(self, cat_id: str) -> bool:
        """Integration point contract checking if a category is referenced by active assets."""
        if not self.asset_repo:
            return False
        _, total = await self.asset_repo.list_paginated(
            limit=1,
            filters={"category_id": cat_id}
        )
        return total > 0
