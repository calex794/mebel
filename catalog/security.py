"""Limit admin login attempts with the shared Redis cache in production."""
import hashlib

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.urls import reverse
from django.http import HttpResponseRedirect
import hmac
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


def client_address(request):
    if getattr(settings, "TRUST_PROXY_X_REAL_IP", False):
        ip = request.META.get("HTTP_X_REAL_IP", "")
        if ip:
            return ip[:64]
    return request.META.get("REMOTE_ADDR", "unknown")[:64]


def address_key(request, purpose):
    return purpose + ":" + hashlib.sha256(client_address(request).encode()).hexdigest()


class AdminLoginThrottle(MiddlewareMixin):
    def process_request(self, request):
        if request.path not in {"/upravlenie/login/", "/upravlenie/vhod/"} or request.method != "POST":
            return None
        key = address_key(request, "admin-login")
        if cache.get(key, 0) >= 10:
            return HttpResponse("Слишком много попыток. Попробуйте позднее.", status=429)
        if not cache.add(key, 1, timeout=900):
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=900)
        return None


class AdminKeySessionGuard(MiddlewareMixin):
    """Protect the entire Django admin and revoke sessions when the key rotates."""

    def process_request(self, request):
        if not request.path.startswith("/upravlenie/"):
            return None
        expected = getattr(settings, "MEBEL_ADMIN_KEY_SHA256", "")
        if not expected:
            if getattr(settings, "MEBEL_ADMIN_KEY_REQUIRED", False):
                if request.user.is_authenticated:
                    auth_logout(request)
                return HttpResponse("Управление временно недоступно.", status=503)
            return None
        if request.path == "/upravlenie/vhod/":
            return None
        if request.user.is_authenticated:
            fingerprint = str(request.session.get("mebel_admin_key_hash", ""))
            if not hmac.compare_digest(fingerprint, expected):
                auth_logout(request)
                return HttpResponseRedirect(reverse("admin_key_login"))
        return None
