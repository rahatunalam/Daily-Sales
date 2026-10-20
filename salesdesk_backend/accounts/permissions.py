from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User

OWNER = User.Role.OWNER
MANAGER = User.Role.MANAGER
CASHIER = User.Role.CASHIER


def roles(*allowed):
    """Permission class: the signed-in user must have one of the given roles."""

    class HasRole(BasePermission):
        message = "Your role cannot do this."

        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.role in allowed)

    HasRole.__name__ = "Roles_" + "_".join(str(r) for r in allowed)
    return HasRole


# Role matrix (open question in the BRD: confirm with the owner).
IsOwner = roles(OWNER)
IsOwnerOrManager = roles(OWNER, MANAGER)


class OwnerWriteAnyoneRead(BasePermission):
    """Everyone signed in can read; only the owner can change."""

    message = "Only the owner can change this."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return request.method in SAFE_METHODS or u.role == OWNER
