from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class Role(str, Enum):
    ADMIN = "ADMIN"
    ASSET_MANAGER = "ASSET_MANAGER"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    EMPLOYEE = "EMPLOYEE"


@dataclass
class User:
    email: str
    hashed_password: str
    name: str
    role: Role = Role.EMPLOYEE
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    department_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_locked(self) -> bool:
        """Determines if the user account is currently soft-locked."""
        if not self.locked_until:
            return False
        # Normalize comparison to aware UTC timezone
        now = datetime.now(timezone.utc)
        locked_until_utc = self.locked_until
        if locked_until_utc.tzinfo is None:
            locked_until_utc = locked_until_utc.replace(tzinfo=timezone.utc)
        
        return now < locked_until_utc

    def increment_failed_login(self, max_attempts: int, lock_duration_minutes: int) -> None:
        """Increments failed logins and locks the user if max_attempts is exceeded."""
        self.failed_login_count += 1
        self.updated_at = datetime.now(timezone.utc)
        if self.failed_login_count >= max_attempts:
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

    def reset_failed_login(self) -> None:
        """Resets failed login count and clears lockouts."""
        self.failed_login_count = 0
        self.locked_until = None
        self.updated_at = datetime.now(timezone.utc)
