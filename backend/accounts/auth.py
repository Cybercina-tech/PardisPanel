"""
Custom JWT authentication that validates token_version for force-logout support.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class JWTAuthenticationWithTokenVersion(JWTAuthentication):
    """
    After standard JWT validation, ensures the token's token_version claim
    matches the user's current token_version (invalidates tokens after force logout).
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, validated_token = result
        token_version = validated_token.get('token_version')
        if token_version is None:
            return result  # Old tokens without claim still work until we enforce
        if getattr(user, 'token_version', 0) != token_version:
            raise InvalidToken('Token has been invalidated (e.g. force logout).')
        return result
