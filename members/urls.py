# members/urls.py
from django.urls import path
from . import views
from . import views_config
from . import views_payments

app_name = "members"

urlpatterns = [


    path('add/', views.add_member, name='add_member'),
    path("edit/<int:member_id>/", views.edit_member, name="edit_member"),
    path("edit/<int:member_id>/add-document/", views.add_member_document, name="add_member_document"),

    path("document/<int:document_id>/edit/", views.edit_member_document, name="edit_member_document"),
    path("document/<int:document_id>/delete/", views.delete_member_document, name="delete_member_document"),
    path("password/change/", views.change_own_password, name="change_own_password"),
    path("profile/", views.profile, name="profile"),

    path("medical-certificate-status/", views.medical_certificate_status, name="medical_certificate_status"),

    path("subscriptions/<int:member_id>/", views.subscription_list, name="subscription_list"),
    path("subscriptions/<int:member_id>/add/", views.add_subscription, name="add_subscription"),
    path('subscriptions/', views.subscription_status, name='subscription_status'),

    #Chiamate per admin
    path('add-document/', views.add_document_admin, name='add_document_admin'),
    path('add-subscription/', views.add_subscription_admin, name='add_subscription_admin'),

    # --- Configurazione ---
    path('config/', views_config.config_home, name='config_home'),

    # Settori
    path('config/settori/', views_config.sector_list, name='sector_list'),
    path('config/settori/nuovo/', views_config.sector_add, name='sector_add'),
    path('config/settori/<int:pk>/modifica/', views_config.sector_edit, name='sector_edit'),
    path('config/settori/<int:pk>/elimina/', views_config.sector_delete, name='sector_delete'),

    # Insegnanti
    path('config/insegnanti/', views_config.instructor_list, name='instructor_list'),
    path('config/insegnanti/nuovo/', views_config.instructor_add, name='instructor_add'),
    path('config/insegnanti/<int:pk>/modifica/', views_config.instructor_edit, name='instructor_edit'),
    path('config/insegnanti/<int:pk>/elimina/', views_config.instructor_delete, name='instructor_delete'),
# --- Pagamenti ---
    path('payments/<int:member_id>/', views_payments.payment_list, name='payment_list'),
    path('payments/<int:member_id>/add/', views_payments.payment_add, name='payment_add'),
    path('payment/<int:pk>/edit/', views_payments.payment_edit, name='payment_edit'),
    path('payment/<int:pk>/delete/', views_payments.payment_delete, name='payment_delete'),
    path('payment/<int:pk>/toggle/', views_payments.payment_toggle_paid, name='payment_toggle_paid'),

# Listino pacchetti
    path('config/pacchetti/', views_config.package_list, name='package_list'),
    path('config/pacchetti/nuovo/', views_config.package_add, name='package_add'),
    path('config/pacchetti/<int:pk>/modifica/', views_config.package_edit, name='package_edit'),
    path('config/pacchetti/<int:pk>/elimina/', views_config.package_delete, name='package_delete'),

]
