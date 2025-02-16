from django.urls import path
from .views import views_auth
from .views import views_app


urlpatterns = [
    path('', views_auth.user_login, name='login'),
    path('index/', views_app.index, name='index'),
    path('signup/', views_auth.user_signup, name='signup'),
    path('logout/', views_auth.user_logout, name='logout'),
    path('error_page/', views_app.error_page, name='error_page'),
    path('generate-summary', views_app.generate_summary, name='generate-summary'),
]
