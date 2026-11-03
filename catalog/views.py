from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .security import address_key
from .forms import LeadForm
from .models import Article, FAQ, Lead, PrivacyPolicy, Project, Service


def home(request):
    return render(request, "catalog/home.html", {
        "services": Service.objects.filter(published=True)[:6],
        "projects": Project.objects.filter(published=True)[:6],
        "articles": Article.objects.filter(published=True)[:3],
        "faqs": FAQ.objects.filter(published=True)[:8],
    })


def services(request):
    return render(request, "catalog/list.html", {
        "items": Service.objects.filter(published=True), "heading": "Мебель на заказ",
        "intro": "Индивидуальные решения для вашего пространства.",
    })


def projects(request):
    return render(request, "catalog/list.html", {
        "items": Project.objects.filter(published=True), "heading": "Наши работы",
        "intro": "Примеры мебели, изготовленной по индивидуальным проектам.",
    })


def articles(request):
    return render(request, "catalog/list.html", {
        "items": Article.objects.filter(published=True), "heading": "Полезные статьи",
        "intro": "О выборе мебели, материалах и планировании интерьера.",
    })


def service_detail(request, slug):
    item = get_object_or_404(Service, slug=slug, published=True)
    return render(request, "catalog/detail.html", {"item": item, "kind": "Услуга"})


def project_detail(request, slug):
    item = get_object_or_404(Project, slug=slug, published=True)
    return render(request, "catalog/detail.html", {"item": item, "kind": "Работа", "photos": item.photos.all()})


def article_detail(request, slug):
    item = get_object_or_404(Article, slug=slug, published=True)
    return render(request, "catalog/detail.html", {"item": item, "kind": "Статья"})


def contacts(request):
    return render(request, "catalog/contacts.html")


def privacy(request):
    current = PrivacyPolicy.current()
    version = request.GET.get("version")
    if version is not None:
        policy = get_object_or_404(
            PrivacyPolicy, version=version, published_at__isnull=False,
        )
    else:
        policy = current
    return render(request, "catalog/privacy.html", {
        "policy": policy,
        "archived": bool(policy and (current is None or policy.pk != current.pk)),
    })


@require_POST
def submit_lead(request):
    form = LeadForm(request.POST)
    redirect_url = request.POST.get("next", "/")
    if not (redirect_url.startswith("/") and not redirect_url.startswith("//")):
        redirect_url = "/"
    if not url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        redirect_url = "/"

    if PrivacyPolicy.current() is None:
        return render(request, "catalog/lead_form.html", {
            "form": form, "policy_unavailable": True,
        }, status=503)

    if not form.is_valid():
        return render(request, "catalog/lead_form.html", {"form": form}, status=400)

    # Блокировка строки политики не позволяет заменить её между проверкой
    # редакции и записью заявки (в PostgreSQL; SQLite используется в предпросмотре).
    with transaction.atomic():
        policy = PrivacyPolicy.objects.select_for_update().filter(
            is_active=True, published_at__isnull=False,
        ).first()
        if policy is None:
            return render(request, "catalog/lead_form.html", {
                "form": form, "policy_unavailable": True,
            }, status=503)
        if form.cleaned_data["consent_version"] != policy.version:
            return render(request, "catalog/lead_form.html", {
                "form": form, "policy_changed": True,
            }, status=409)

        # Five submissions per shared client IP in 15 minutes. For real traffic,
        # configure shared Redis cache and a trusted proxy IP policy before launch.
        key = address_key(request, "lead-rate")
        count = cache.get(key, 0)
        if count >= 5:
            return render(request, "catalog/lead_form.html", {
                "form": form, "rate_limited": True,
            }, status=429)
        if count:
            cache.incr(key)
        else:
            cache.set(key, 1, timeout=900)

        Lead.objects.create(
            name=form.cleaned_data["name"],
            phone=form.cleaned_data["phone"],
            message=form.cleaned_data["message"],
            consent_at=timezone.now(),
            consent_version=policy.version,
            consent_policy=policy,
            source=redirect_url[:300],
        )
    messages.success(request, "Спасибо! Заявка получена. Мы свяжемся с вами.")
    return HttpResponseRedirect(redirect_url)


def robots(request):
    content = "User-agent: *\nDisallow: /upravlenie/\nDisallow: /zayavka/\nSitemap: " + request.build_absolute_uri(reverse("sitemap")) + "\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
