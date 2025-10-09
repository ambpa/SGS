# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from members import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout/password reset
    path('members/', include('members.urls', namespace='members')),  # tutte le rotte di members
    path('dashboard/', views.dashboard, name='dashboard'),
    path('subscription-data/', views.subscription_data, name='subscription_data'),
    path('subscriptions-category-data/', views.subscriptions_by_category, name='subscription_category_data'),

    # Root URL punta alla dashboard
    path('', views.dashboard, name='home'),
]

# Serve i file MEDIA in sviluppo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
