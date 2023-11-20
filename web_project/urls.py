# """
# URL configuration for web_project project.

# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/4.2/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
from django.contrib import admin
from django.urls import path, include
from homework_app import views
from django.urls import re_path
from homework_app.views import CustomTokenObtainPairView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.home, name="home"),

    # path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('members/', include('django.contrib.auth.urls')), #yoyoapp??
    path('login/',views.login_user, name='login_user'),
    path('signup/',views.signup_user, name='signup_user'),

    path('handle_homework/', views.handle_homework, name='handle_homework'),
    path('handle_homework/<int:pk>/', views.handle_homework_id, name='handle_homework_id'),

    path('handle_classes/', views.handle_classes, name='handle_classes'),
    path('handle_classes/<int:pk>/', views.handle_classes_id, name='handle_classes_id'),

    path('handle_students_class/<int:sid>/<int:cid>/', views.handle_students_class, name='handle_students_class'),


    # path('category/type/<str:type>/', views.get_cat_id, name="get_cat_id"),
    # path('latests/', views.get_latests, name='get_latests'),

    # path('categories/', views.handle_category, name='handle_category'),
    # path('categories/<int:pk>/', views.handle_category_id, name='handle_category_id'),

    # path('categories/<int:cid>/tricks/', views.handle_trick, name='handle_trick'), 
    # path('categories/<int:cid>/tricks/<int:tid>/', views.handle_trick_id, name='handle_trick_id'), 
    
    # path('categories/<int:cid>/tricks/<int:tid>/comments/', views.handle_comment, name='handle_comment'),
    # path('categories/<int:cid>/tricks/<int:tid>/comments/<int:ccid>/', views.handle_comment_id, name='handle_comment_id'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)