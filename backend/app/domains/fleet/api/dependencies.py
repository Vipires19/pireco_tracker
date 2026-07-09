from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.domains.identity.api.dependencies import get_current_user
from app.domains.identity.models import User
from app.kernel.security.permissions import Permission, role_has_permission


def require_permission(permission: Permission) -> Callable:
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(role_has_permission(role.slug, permission.value) for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return checker


require_vehicles_read = require_permission(Permission.VEHICLES_READ)
require_vehicles_write = require_permission(Permission.VEHICLES_WRITE)
