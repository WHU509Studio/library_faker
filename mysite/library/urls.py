from django.urls import path

from . import views

app_name = 'library'
urlpatterns = [
    path('', views.log_in),
    path('library/', views.library_form, name='library'),
]