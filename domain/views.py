"""Identity read/write views."""

from typing import cast
from uuid import UUID

from core.audit import ACTION_DENIED, ACTION_READ, ACTION_WRITE, AuditService
from core.auth.authentication import JWTAuthentication, TokenPrincipal
from core.payments.provider import PaymentWebhookError
from core.payments.webhook import process_payment_webhook
from core.permissions import allowed_write_keys
from core.policy import resolve_readable_visibilities, resolve_writable_visibilities
from core.redaction import redact_by_visibility
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.audit_storage import OrmAuditStorage
from domain.models import AuditEntry, Person, ProfileField, Role
from domain.policy_lookup import OrmReadablePolicyLookup, OrmWritablePolicyLookup
from domain.serializers import (
    AuditEntrySerializer,
    RedactedIdentitySerializer,
    WritableIdentitySerializer,
)
from domain.throttling import IdentityWriteThrottle

# Cap list size - admin sees recent rows only; avoids unbounded responses.
_AUDIT_LIST_LIMIT = 50


class IsAdminRole(BasePermission):
    """Admin-only. The audit route checks role here, not in the SPA."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        principal = request.user
        if not isinstance(principal, TokenPrincipal):
            return False
        return principal.role == Role.ADMIN


def _subject_owns(person: Person, principal: TokenPrincipal) -> bool:
    """True when this subject token owns the person. Empty owner_sub means no."""
    return bool(person.owner_sub) and person.owner_sub == principal.sub


def _record_access_audit(
    *,
    principal: TokenPrincipal,
    person_id: UUID,
    context: str,
    action: str,
    fields: list[str],
    decision_reason: str,
) -> None:
    """Append one audit row - shared by read and write paths."""
    AuditService(OrmAuditStorage()).record(
        caller_sub=principal.sub,
        role=principal.role,
        action=action,
        person_id=person_id,
        context=context,
        fields=fields,
        decision_reason=decision_reason,
    )


class IdentityReadView(APIView):
    """
    GET /api/v1/identities/{person_id}?context={context}

    Returns only the fields this role may see in this context.
    If that is nothing, return 404 not 403.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, person_id: UUID) -> Response:
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
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="no_readable_policy",
            )
            raise NotFound()

        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist as exc:
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="person_not_found",
            )
            raise NotFound() from exc

        if principal.role == Role.SUBJECT and not _subject_owns(person, principal):
            # Same 404 as an unknown person, so you cannot tell they exist.
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="not_owner",
            )
            raise NotFound()

        candidate_fields = ProfileField.objects.filter(
            person=person,
            context=context,
        )
        redacted_fields = cast(
            list[ProfileField],
            redact_by_visibility(candidate_fields, readable),
        )
        if not redacted_fields:
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=[],
                decision_reason="no_readable_fields",
            )
            raise NotFound()

        _record_access_audit(
            principal=principal,
            person_id=person_id,
            context=context,
            action=ACTION_READ,
            fields=[field.key for field in redacted_fields],
            decision_reason="policy_allowed",
        )

        payload = RedactedIdentitySerializer.from_redacted(
            person.id,
            context,
            redacted_fields,
        )
        serializer = RedactedIdentitySerializer(payload)
        return Response(serializer.data)


def _requested_field_keys(data: object) -> list[str]:
    """Extract nested field keys from a write body for audit - keys only."""
    if not isinstance(data, dict):
        return []
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return []
    return [str(key) for key in fields.keys()]


class IdentityWriteView(APIView):
    """
    PUT /api/v1/identities/{person_id}/contexts/{context}

    Create/update only profile fields writable for the caller's (role, context).
    Unauthorised or mass-assignment writes return 403 and persist nothing.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [IdentityWriteThrottle]

    def put(self, request: Request, person_id: UUID, context: str) -> Response:
        context = context.strip()
        if not context:
            return Response({"detail": "Invalid context."}, status=400)

        # Type-narrowing for mypy; JWTAuthentication guarantees a TokenPrincipal.
        principal = request.user
        assert isinstance(principal, TokenPrincipal)  # nosec B101

        writable = resolve_writable_visibilities(
            principal.role,
            context,
            OrmWritablePolicyLookup(),
        )
        if not writable:
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=_requested_field_keys(request.data),
                decision_reason="no_writable_policy",
            )
            raise PermissionDenied()

        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=_requested_field_keys(request.data),
                decision_reason="person_not_found",
            )
            raise PermissionDenied() from None

        if principal.role == Role.SUBJECT and not _subject_owns(person, principal):
            # Subject can only write their own record. 403, save nothing.
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=_requested_field_keys(request.data),
                decision_reason="not_owner",
            )
            raise PermissionDenied()

        candidate_fields = ProfileField.objects.filter(person=person, context=context)
        allowed_keys = allowed_write_keys(candidate_fields, writable)

        serializer = WritableIdentitySerializer(
            data=request.data,
            allowed_keys=allowed_keys,
        )
        if not serializer.is_valid():
            _record_access_audit(
                principal=principal,
                person_id=person_id,
                context=context,
                action=ACTION_DENIED,
                fields=_requested_field_keys(request.data),
                decision_reason="forbidden_fields",
            )
            raise PermissionDenied()

        written = serializer.validated_data["fields"]
        with transaction.atomic():
            for key, value in written.items():
                ProfileField.objects.filter(
                    person=person,
                    context=context,
                    key=key,
                ).update(value=value)

        _record_access_audit(
            principal=principal,
            person_id=person_id,
            context=context,
            action=ACTION_WRITE,
            fields=list(written.keys()),
            decision_reason="policy_allowed",
        )

        payload = {
            "id": person.id,
            "context": context,
            "fields": written,
        }
        return Response(payload)


class PaymentWebhookView(APIView):
    """
    POST /api/v1/payments/webhook

    Provider callback - authenticated by signed payload, not JWT. Deny by default on
    bad/missing signature; idempotent on repeated event ids (Stripe retries).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        signature = request.headers.get("Stripe-Signature")
        try:
            result = process_payment_webhook(request.body, signature)
        except PaymentWebhookError:
            # Generic client error - never echo verification details.
            return Response(
                {"detail": "Webhook verification failed."},
                status=400,
            )
        return Response(result)


class IdentityAuditView(APIView):
    """
    GET /api/v1/identities/{person_id}/audit

    Admin-only list of recent audit entries for one identity. Role is checked
    server-side on every request - not inferred from the URL.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request: Request, person_id: UUID) -> Response:
        entries = AuditEntry.objects.filter(person_id=person_id)[:_AUDIT_LIST_LIMIT]
        serializer = AuditEntrySerializer(entries, many=True)
        return Response(serializer.data)

