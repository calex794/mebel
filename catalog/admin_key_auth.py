"""Administrator key-only login, adapted from Erida to Django's native sessions.

The high-entropy key is shown to its owner once and never stored in the database.
Only its SHA-256 digest is configured on the server. The Django session remembers
the digest that authenticated it; changing the digest revokes older admin sessions.
"""
import hashlib
import hmac

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model, login as auth_login
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods


class KeyLoginForm(forms.Form):
    access_key = forms.CharField(
        label="Ключ администратора",
        min_length=40,
        max_length=256,
        strip=True,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "off",
            "spellcheck": "false",
            "autofocus": "autofocus",
        }),
    )


def _private(response):
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    response["Referrer-Policy"] = "no-referrer"
    response["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'self'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@never_cache
@require_http_methods(["GET", "POST"])
def admin_login_entry(request):
    """Intercept Django's default password form before the admin URL patterns."""
    if not settings.MEBEL_ADMIN_KEY_SHA256:
        if not settings.DEBUG:
            return _private(HttpResponse("Управление временно недоступно.", status=503))
        return admin.site.login(request)
    if request.method != "GET":
        return _private(HttpResponseNotAllowed(["GET"]))
    return _private(HttpResponseRedirect(reverse("admin_key_login")))


@never_cache
@sensitive_post_parameters("access_key")
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_key_login(request):
    expected = settings.MEBEL_ADMIN_KEY_SHA256
    if not expected:
        if not settings.DEBUG:
            return _private(HttpResponse("Управление временно недоступно.", status=503))
        raise Http404()

    if (
        request.method == "GET"
        and request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
        and hmac.compare_digest(
            str(request.session.get("mebel_admin_key_hash", "")), expected
        )
    ):
        return _private(HttpResponseRedirect(reverse("admin:index")))

    form = KeyLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        provided = form.cleaned_data["access_key"]
        fingerprint = hashlib.sha256(provided.encode("utf-8")).hexdigest()
        if hmac.compare_digest(fingerprint, expected):
            User = get_user_model()
            username = settings.MEBEL_ADMIN_KEY_USER
            user = User._default_manager.filter(
                **{User.USERNAME_FIELD: username},
                is_active=True,
                is_staff=True,
                is_superuser=True,
            ).first()
            if user is not None:
                auth_login(
                    request, user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                request.session["mebel_admin_key_hash"] = expected
                request.session.set_expiry(8 * 60 * 60)
                return _private(HttpResponseRedirect(reverse("admin:index")))
        form.add_error("access_key", "Неверный ключ.")
    status = 401 if request.method == "POST" else 200
    return _private(render(request, "admin/key_login.html", {"form": form}, status=status))
