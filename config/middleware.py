"""Project middleware - response headers not covered by Django built-ins."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class PermissionsPolicyMiddleware:
    """Set Permissions-Policy on every response - JSON API needs no browser features."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "microphone=(), payment=(), usb=()"
        )
        return response
