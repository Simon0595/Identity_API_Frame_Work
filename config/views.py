"""Health check and a couple of SPA helpers."""

from core.auth.authentication import JWTAuthentication, TokenPrincipal
from core.auth.local_tokens import dev_login_enabled, mint_local_token
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.serializers import DevLoginRequestSerializer


@api_view(["GET"])
def health(_request: Request) -> Response:
    """Simple liveness check."""
    return Response({"status": "ok"})


class MeView(APIView):
    """GET /api/v1/me. Role and sub come from the token, not a database lookup."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        principal = request.user
        assert isinstance(principal, TokenPrincipal)  # nosec B101
        return Response({"sub": principal.sub, "role": principal.role})


class DevLoginView(APIView):
    """POST /api/v1/dev/login. Offline demo only; 404 when disabled."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        if not dev_login_enabled():
            raise Http404

        serializer = DevLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token = mint_local_token(sub=str(data["sub"]), role=str(data["role"]))
        # "Bearer" is the RFC 6750 auth-scheme label, not a secret (bandit B105 FP).
        return Response({"access_token": token, "token_type": "Bearer"})  # nosec B105
