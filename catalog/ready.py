from django.db import connection
from django.http import HttpResponse, HttpResponseServerError
from django.views.decorators.http import require_GET


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return HttpResponseServerError("not ready", content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
