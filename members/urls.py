# members/urls.py
from django.urls import path
from . import views

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

]
