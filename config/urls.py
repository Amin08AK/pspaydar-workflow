# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings # <-- این را اضافه کنید
from django.conf.urls.static import static # <-- این را اضافه کنید

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

# ===== این بخش را برای نمایش فایل‌ها در حالت توسعه اضافه کنید =====
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)