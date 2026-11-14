from django.db import models
from django.db.models import Q


class Mirrored(models.Model):
    """Fields shared by every row mirrored from Keycloak."""

    synced_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class Organization(Mirrored):
    id = models.CharField(primary_key=True, max_length=64)  # Keycloak org ID
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class Group(Mirrored):
    """A group inside an organization: a club, a mentorship, and so on."""

    id = models.CharField(primary_key=True, max_length=64)  # Keycloak group ID
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="groups"
    )

    def __str__(self) -> str:
        return self.name


class Membership(Mirrored):
    """A user's membership of an organization, or of one group inside it."""

    user_sub = models.CharField(max_length=64, db_index=True)  # Keycloak user ID
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
        null=True,
        blank=True,
    )
    roles = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_sub", "organization"],
                condition=Q(group__isnull=True),
                name="amt_auth_unique_org_membership",
            ),
            models.UniqueConstraint(
                fields=["user_sub", "organization", "group"],
                condition=Q(group__isnull=False),
                name="amt_auth_unique_group_membership",
            ),
        ]
