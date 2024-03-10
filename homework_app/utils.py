from .models import *
from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='teacher').exists()

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='student').exists()

def get_completed_students_count(assignment):
    assignment_results = AssignmentResult.objects.filter(assignment=assignment)
    return assignment_results.values('student').distinct().count()

def get_assignment_status(assignment):
    completed_students_count = get_completed_students_count(assignment)
    total_students_count = StudentClass.objects.filter(classs=assignment.classs).count()
    if total_students_count == 0:
        return 'Bad'
    completion_percentage = (completed_students_count / total_students_count) * 100
    if completion_percentage >= 75:
        return 'Good'
    elif completion_percentage >= 50:
        return 'Average'
    else:
        return 'Bad' 