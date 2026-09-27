"""Asset read views."""

from typing import cast
from uuid import UUID

from core.audit import ACTION_DENIED, ACTION_READ, AuditService
from core.auth.authentication import JWTAuthentication, TokenPrincipal
from core.policy import resolve_readable_visibilities
from core.redaction import redact_by_visibility
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain2.audit_storage import OrmAuditStorage
from domain2.models import Asset, AssetAttribute
from domain2.policy_lookup import OrmReadablePolicyLookup
from domain2.serializers import RedactedAssetSerializer


def _record_access_audit(
    *,
    principal: TokenPrincipal,
    asset_id: UUID,
    context: str,
    action: str,
    fields: list[str],
    decision_reason: str,
) -> None:
    """Append one audit row - shared read-path helper."""
    AuditService(OrmAuditStorage()).record(
        caller_sub=principal.sub,
        role=principal.role,
        action=action,
        person_id=asset_id,
        context=context,
        fields=fields,
        decision_reason=decision_reason,
    )


class AssetReadView(APIView):
    """
    GET /api/v1/assets/{asset_id}?context={context}

    Returns only the attributes this role may see in this context.
    If that is nothing, return 404 not 403.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, asset_id: UUID) -> Response:
        context = request.query_params.get("context", "").strip()
        if not context:
            return Response(
                {"detail": "Query parameter 'context' is required."},
                status=400,
            )

        # Type-narrowing for mypy; JWTAuthentication guarantees a TokenPrincipal.
        principal = request.user
        assert isinstance(principal, TokenPrincipal)  # nosec B101

        readable = resolve_readable_visibilities(
            principal.role,
            context,
            OrmReadablePolicyLookup(),
        )
        if not readable:
            _record_access_audit(
                principal=principal,
                asset_id=asset_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="no_readable_policy",
            )
            raise NotFound()

        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist as exc:
            _record_access_audit(
                principal=principal,
                asset_id=asset_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="asset_not_found",
            )
            raise NotFound() from exc

        candidate_attributes = AssetAttribute.objects.filter(
            asset=asset,
            context=context,
        )
        redacted_attributes = cast(
            list[AssetAttribute],
            redact_by_visibility(candidate_attributes, readable),
        )
        if not redacted_attributes:
            _record_access_audit(
                principal=principal,
                asset_id=asset_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="no_readable_fields",
            )
            raise NotFound()

        _record_access_audit(
            principal=principal,
            asset_id=asset_id,
            context=context,
            action=ACTION_READ,
            fields=[attr.key for attr in redacted_attributes],
            decision_reason="policy_allowed",
        )

        payload = RedactedAssetSerializer.from_redacted(
            asset.id,
            context,
            redacted_attributes,
        )
        serializer = RedactedAssetSerializer(payload)
        return Response(serializer.data)
