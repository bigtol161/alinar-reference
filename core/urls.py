from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('catalog/', views.catalog, name='catalog'),
    path('master/<str:slug>/', views.master_detail, name='master'),
    path('request/', views.request_create, name='request_new'),
    path('request/<str:master_slug>/', views.request_create, name='request_new_master'),
    path('become-master/', views.become_master, name='become_master'),
    path('account/', views.account, name='account'),
    path('account/cancel/<int:pk>/', views.cancel_request, name='cancel_request'),
    path('auth/register/', views.sign_up, name='sign_up'),
    path('auth/login/', views.sign_in, name='sign_in'),
    path('auth/logout/', views.sign_out, name='sign_out'),
    path('api/suggest/', views.suggest, name='suggest'),
]
