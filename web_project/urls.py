from django.urls import path, include
from homework_app import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'login', views.LoginViewUser, basename='login')
router.register(r'password', views.PasswordView, basename='password')
router.register(r'user_profile', views.ProfileViewUser, basename='user_profile')
router.register(r'assignments', views.AssignmentView, basename='assignments') 
router.register(r'classes', views.ClassesListView, basename='classes')
router.register(r'assignments_teacher', views.AssignmentListViewTeacher, basename='assignments_teacher') 
router.register(r'assignments_student', views.AssignmentListViewStudent, basename='assignments_student')
router.register(r'assignments_teacher_finished', views.AssignmentListViewTeacherFinished, basename='assignments_teacher_finished') 
router.register(r'assignments_student_finished', views.AssignmentListViewStudentFinished, basename='assignments_student_finished')
router.register(r'assignment_statistics', views.AssignmentViewStatistics, basename='assignment_statistics')
router.register(r'class_statistics', views.ClassViewStatistics, basename='class_statistics')
router.register(r'homework', views.HomeworkView, basename='homework')
router.register(r'school', views.SchoolViewAdmin, basename='school')

urlpatterns = [
    path('', include(router.urls)),

    path('login/', views.LoginViewUser.as_view({'post': 'post'}), name='login'),

    path('one_student_answers/<int:assignment_id>/<int:student_id>/', views.OneStudentViewStatistics.as_view({'get': 'list'}), name='one_student_answers'),
    path('test/<int:assignment_id>/', views.TestView.as_view({'get':'list', 'post':'post_answers'}), name='test'),
    path('school/update/<int:school_id>/', views.UpdateViewSchool.as_view(), name='school-update'),

    path('game/<int:assignment_id>/', views.QuestionsViewGame.as_view({'get':'list', 'post': 'post_answer'}), name='game'),
    path('post_summary/', views.SummaryView.as_view({'post':'create'}), name='post_summary'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)