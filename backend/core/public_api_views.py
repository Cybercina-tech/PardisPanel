from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.scoping import act_as_account, resolve_public_account_id, unscoped
from core.prices_snapshot import build_prices_public_snapshot


class PublicPricesAPIView(APIView):
    """
    GET /api/public/prices/?account=<slug> — latest category and special
    prices as JSON. No authentication (invalid JWT must not block access).

    The slug names whose prices to publish; a single-account deployment may
    omit it. An unknown or ambiguous slug returns an empty snapshot rather than
    another desk's prices.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "public_prices"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        with unscoped():
            account_id = resolve_public_account_id(request.query_params.get("account"))
        with act_as_account(account_id):
            return Response(build_prices_public_snapshot())
