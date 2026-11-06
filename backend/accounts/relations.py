"""Serializer relations that respect per-account scoping."""
from rest_framework import serializers


class ScopedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """A related field whose queryset is built per request, from a callable.

    A queryset handed to DRF is evaluated when the serializer class body runs —
    at import time, with no account in context — so a scoped manager's
    fail-closed ``.none()`` would be baked in for the life of the process, and
    an unscoped one would offer every customer's rows as valid input. Deferring
    to a callable means the choices are always the ones the account in flight
    actually owns.
    """

    def get_queryset(self):
        return self.queryset()
