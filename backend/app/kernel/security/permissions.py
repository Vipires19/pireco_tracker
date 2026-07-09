from enum import StrEnum


class Permission(StrEnum):
    DASHBOARD_READ = "dashboard:read"
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    CLIENTS_READ = "clients:read"
    CLIENTS_WRITE = "clients:write"
    VEHICLES_READ = "vehicles:read"
    VEHICLES_WRITE = "vehicles:write"
    TRACKERS_READ = "trackers:read"
    TRACKERS_WRITE = "trackers:write"
    INSTALLATIONS_READ = "installations:read"
    INSTALLATIONS_WRITE = "installations:write"
    OPERATIONS_READ = "operations:read"
    MONITORING_READ = "monitoring:read"
    BILLING_READ = "billing:read"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [p.value for p in Permission],
    "operator": [
        Permission.DASHBOARD_READ.value,
        Permission.CLIENTS_READ.value,
        Permission.VEHICLES_READ.value,
        Permission.TRACKERS_READ.value,
        Permission.TRACKERS_WRITE.value,
        Permission.INSTALLATIONS_READ.value,
        Permission.INSTALLATIONS_WRITE.value,
        Permission.OPERATIONS_READ.value,
        Permission.MONITORING_READ.value,
    ],
    "viewer": [
        Permission.DASHBOARD_READ.value,
        Permission.CLIENTS_READ.value,
        Permission.VEHICLES_READ.value,
        Permission.TRACKERS_READ.value,
        Permission.INSTALLATIONS_READ.value,
        Permission.MONITORING_READ.value,
    ],
}


def role_has_permission(role_slug: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role_slug, [])
