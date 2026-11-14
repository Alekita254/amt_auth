from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsOrgMember(BasePermission):
    """Allows users whose token carries at least one organization membership."""

    def has_permission(self, request, view) -> bool:
        claims = getattr(request.user, "claims", None)
        return claims is not None and claims.active_organization is not None


def _has_role(claims_attr: str, role: str) -> type[BasePermission]:
    class HasRole(BasePermission):
        def has_permission(self, request, view) -> bool:
            claims = getattr(request.user, "claims", None)
            return claims is not None and role in getattr(claims, claims_attr)

    return HasRole


def has_realm_role(role: str) -> type[BasePermission]:
    """`permission_classes = [has_realm_role("admin")]`"""
    return _has_role("realm_roles", role)


def has_client_role(role: str) -> type[BasePermission]:
    """`permission_classes = [has_client_role("editor")]` (roles of AMT_CLIENT_ID)."""
    return _has_role("client_roles", role)
