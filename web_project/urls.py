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
    path('handle_homework_id/<int:pk>/', views.handle_homework_id, name='handle_homework_id'),

    path('handle_classes/', views.handle_classes, name='handle_classes'),
    path('handle_classes/<int:pk>/', views.handle_classes_id, name='handle_classes_id'),

    path('handle_students_class/<int:sid>/<int:cid>/', views.handle_students_class, name='handle_students_class'),

    path('handle_teacher_class/<int:cid>/', views.handle_teacher_class, name='handle_teacher_class'),
    path('get_classes_by_teacher/', views.get_classes_by_teacher, name='get_classes_by_teacher'),
    path('handle_assign_homework/', views.handle_assign_homework, name='handle_assign_homework'),
    path('handle_teacher_students/', views.handle_teacher_students, name='handle_teacher_students'),
    path('handle_student_teachers/', views.handle_student_teachers, name='handle_student_teachers'),
    path('handle_teachers/', views.handle_teachers, name='handle_teachers'),
    path('handle_students/', views.handle_students, name='handle_students'),
    path('get_not_confirmed_students/',views.get_not_confirmed_students, name='get_not_confirmed_students'),
    path('get_not_confirmed_teachers/',views.get_not_confirmed_teachers, name='get_not_confirmed_teachers'),
    path('get_assignment_statistics/<int:pk>/',views.get_assignment_statistics, name='get_assignment_statistics'),
    path('handle_assignments_teacher/',views.handle_assignments_teacher, name='handle_assignments_teacher'),
    path('handle_assignments_teacher_finished/',views.handle_assignments_teacher_finished, name='handle_assignments_teacher_finished'),
    path('handle_assignments_student/',views.handle_assignments_student, name='handle_assignments_student'),
    path('handle_assignments_student_finished/',views.handle_assignments_student_finished, name='handle_assignments_student_finished'),
    path('handle_students_assignment_results/<int:aid>/',views.handle_students_assignment_results, name='handle_students_assignment_results'),
    path('get_one_student_answers/<int:aid>/<int:sid>/',views.get_one_student_answers, name='get_one_student_answers'),
    
    path('start_game/',views.start_game, name='start_game'),
    path('post_answer/',views.post_answer, name='post_answer'),
    path('post_summary/',views.post_summary, name='post_summary'),
    path('get_questions/<int:aid>/',views.get_questions, name='get_questions'),

    path('user_data/',views.user_data, name='user_data'),
    path('change_password/',views.change_password, name='change_password'),
    path('get_user_id/',views.get_user_id, name='get_user_id'),

    # path('category/type/<str:type>/', views.get_cat_id, name="get_cat_id"),
    # path('latests/', views.get_latests, name='get_latests'),

    # path('categories/', views.handle_category, name='handle_category'),
    # path('categories/<int:pk>/', views.handle_category_id, name='handle_category_id'),

    # path('categories/<int:cid>/tricks/', views.handle_trick, name='handle_trick'), 
    # path('categories/<int:cid>/tricks/<int:tid>/', views.handle_trick_id, name='handle_trick_id'), 
    
    # path('categories/<int:cid>/tricks/<int:tid>/comments/', views.handle_comment, name='handle_comment'),
    # path('categories/<int:cid>/tricks/<int:tid>/comments/<int:ccid>/', views.handle_comment_id, name='handle_comment_id'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)