from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from django.views.generic import TemplateView

urlpatterns = [
    path("portal-secreto/", admin.site.urls), 
    path("financeiro/", include("teddyfinanca.urls")),
    path("", include("core.urls")),
    path("sw.js", TemplateView.as_view(template_name="sw.js", content_type="application/javascript"), name="sw.js"),
    path("manifest.json", TemplateView.as_view(template_name="manifest.json", content_type="application/json"), name="manifest.json"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
