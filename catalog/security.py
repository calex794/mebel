"""Limit admin login attempts with the shared Redis cache in production."""
import hashlib

from django.conf import settings
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
        if request.path != "/upravlenie/login/" or request.method != "POST":
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
