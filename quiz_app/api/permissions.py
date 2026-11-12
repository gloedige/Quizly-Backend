from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow quiz detail actions only to the quiz owner."""

    def has_object_permission(self, request, view, obj):
        """Check that the authenticated user owns the quiz."""
        return obj.owner_id == request.user.id
