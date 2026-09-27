"""Load asset policy rows for the core helpers."""

from domain2.models import AssetPolicy


def _policy_visibilities_for(
    role: str,
    context: str,
    field_name: str,
) -> list[str] | None:
    """Load one visibility list from an AssetPolicy row, or None when missing."""
    try:
        policy = AssetPolicy.objects.get(role=role, context=context)
    except AssetPolicy.DoesNotExist:
        return None
    return list(getattr(policy, field_name))


class OrmReadablePolicyLookup:
    """Load (role, context) readable visibility lists from AssetPolicy rows."""

    def readable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        """Return stored visibility classes, or None when no policy row exists."""
        return _policy_visibilities_for(role, context, "readable_visibilities")


class OrmWritablePolicyLookup:
    """Load (role, context) writable visibility lists from AssetPolicy rows."""

    def writable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        """Return stored writable classes, or None when no policy row exists."""
        return _policy_visibilities_for(role, context, "writable_visibilities")
