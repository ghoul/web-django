from django.test import TestCase
from homework_app.factory import *
from homework_app.serializers import *
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.urls import reverse
from datetime import datetime, timedelta, date
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
from io import StringIO

class LoginViewUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        school = School.objects.create(title="school", license_end = datetime.today())
        self.user = CustomUser.objects.create_user(username ='test@example.com', email='test@example.com', 
                                                    password ='testpassword', role=1, gender=1, school=school)
        self.url = reverse('login') 

    def test_login_successful(self):
        data = {'email': 'test@example.com', 'password': 'testpassword'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('csrf_token', response.data)

    def test_login_invalid_credentials(self):
        data = {'email': 'test@example.com', 'password': 'wrongpassword'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Neteisingas el. paštas arba slaptažodis')

    def test_login_expired_license(self):
        self.user.school.license_end = datetime.today().date() - timedelta(days=3)
        self.user.school.save()
        self.user.save()
        data = {'email': 'test@example.com', 'password': 'testpassword'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Jūsų licenzija nebegalioja')


class PasswordViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUserFactory.create()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('password-detail', kwargs={'pk': self.user.pk})

    def test_update_password(self):
        data = {'password': 'changed_password'}
        response = self.client.put(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_data(self):
        data = {}
        response = self.client.put(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permission_denied(self):
        another_user =  CustomUserFactory.create()
        data = {'password': 'changed_password'}
        url = reverse('password-detail', kwargs={'pk': another_user.pk})
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AssignmentViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group_teacher, _ = Group.objects.get_or_create(name='teacher')
        self.teacher = CustomUserFactory.create(role=2)
        self.teacher.groups.add(self.group_teacher)
        self.classs = ClassFactory.create()
        self.homework = HomeworkFactory.create(teacher=self.teacher)
        self.assignment = AssignmentFactory.create(homework=self.homework,  classs=self.classs, from_date = date.today(), to_date=date.today())
        self.valid_payload = {
            'homework': self.homework.id,
            'from_date': str(date.today()),
            'to_date': str(date.today()),
            'classs': self.classs.id,
        }

    def test_create_assignment_authenticated_teacher(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('assignments-list')
        response = self.client.post(url, data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assignment.objects.count(), 2) # +1 in setup

    def test_create_assignment_unauthenticated(self):
        url = reverse('assignments-list')
        response = self.client.post(url, data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Assignment.objects.count(), 1)

    def test_update_assignment_authenticated_teacher(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('assignments-detail', args=[self.assignment.id])
        updated_to_date = str(date.today() + timedelta(days=1))
        updated_to_date = datetime.strptime(updated_to_date, '%Y-%m-%d').date()
        updated_payload = {
            'to_date': updated_to_date,
        }
        response = self.client.put(url, data=updated_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Assignment.objects.get(id=self.assignment.id).to_date, updated_to_date)

    def test_update_assignment_unauthenticated(self):
        url = reverse('assignments-detail', args=[self.assignment.id])
        updated_to_date = str(date.today() + timedelta(days=1))
        updated_payload = {
            'to_date': updated_to_date,
        }
        response = self.client.put(url, data=updated_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(str(Assignment.objects.get(id=self.assignment.id).to_date), str(date.today()))

    def test_update_assignment_different_teacher(self):
        other_teacher = CustomUserFactory.create(role=2)
        other_teacher.groups.add(self.group_teacher)
        self.client.force_authenticate(user=other_teacher)
        url = reverse('assignments-detail', args=[self.assignment.id])
        updated_to_date = str(date.today() + timedelta(days=1))
        updated_to_date = datetime.strptime(updated_to_date, '%Y-%m-%d').date()
        updated_payload = {
            'to_date': updated_to_date,
        }
        response = self.client.put(url, data=updated_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(str(Assignment.objects.get(id=self.assignment.id).to_date), str(date.today()))


class ProfileViewUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUserFactory.create(email='test@example.com')
        self.url = reverse('user_profile-detail', kwargs={'pk': self.user.pk})

    def test_retrieve_user_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_update_user_email(self):
        self.client.force_authenticate(user=self.user)
        updated_email = 'updated@example.com'
        updated_data = {'email': updated_email}
        response = self.client.put(self.url, data=updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], updated_email)

    def test_update_user_no_email(self):
        self.client.force_authenticate(user=self.user)
        invalid_data = {'username': 'new_username'}  # no email
        response = self.client.put(self.url, data=invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_multiple_fields(self):
        self.client.force_authenticate(user=self.user)   
        updated_data = {'email': 'updated@example.com', 'username': 'new_username'}  # too many fields
        response = self.client.put(self.url, data=updated_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)        


class AssignmentViewStatisticsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.assignment = AssignmentFactory.create()
        self.student1 = CustomUserFactory.create(classs=self.assignment.classs)
        self.student2 = CustomUserFactory.create(classs=self.assignment.classs)
        self.assignment_result1 = AssignmentResultFactory.create(
            assignment=self.assignment, student=self.student1, points=80, time=datetime.strptime('00:30:00', '%H:%M:%S')
        )
        self.assignment_result2 = AssignmentResultFactory.create(
            assignment=self.assignment, student=self.student2, points=90, time=datetime.strptime('00:25:00', '%H:%M:%S')
        )

    def test_retrieve_assignment_statistics(self):
        self.client.force_authenticate(user=self.student1)
        url = reverse('assignment_statistics-detail', kwargs={'pk': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['assignment_results']), 2) 

    def test_retrieve_assignment_statistics_unauthenticated(self):
        url = reverse('assignment_statistics-detail', kwargs={'pk': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_assignment_statistics_wrong_assignment_id(self):
        self.client.force_authenticate(user=self.student1)
        url = reverse('assignment_statistics-detail', kwargs={'pk': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_assignment_statistics_no_students(self):
        assignment_no_students = AssignmentFactory.create()
        self.client.force_authenticate(user=self.student1)
        url = reverse('assignment_statistics-detail', kwargs={'pk': assignment_no_students.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['assignment_results']), 0)


class ClassViewStatisticsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.classs = ClassFactory.create()
        self.student1 = CustomUserFactory.create(classs=self.classs)
        self.student2 = CustomUserFactory.create(classs=self.classs)
        self.assignment1 = AssignmentFactory.create(classs=self.classs)
        self.assignment2 = AssignmentFactory.create(classs=self.classs)
        self.assignment_result1 = AssignmentResultFactory.create(
            student=self.student1, assignment=self.assignment1, points=80
        )
        self.assignment_result2 = AssignmentResultFactory.create(
            student=self.student2, assignment=self.assignment1, points=90
        )
        self.assignment_result3 = AssignmentResultFactory.create(
            student=self.student1, assignment=self.assignment2, points=70
        )

    def test_list_class_statistics(self):
        self.client.force_authenticate(user=self.student1)
        url = reverse('class_statistics-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['leaderboard']), 2)

    def test_list_class_statistics_unauthenticated(self):
        url = reverse('class_statistics-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)       


class OneStudentViewStatisticsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = CustomUserFactory.create()
        self.assignment = AssignmentFactory.create()
        self.question1 = QuestionAnswerPairFactory.create(homework = self.assignment.homework)
        self.question2 = QuestionAnswerPairFactory.create(homework = self.assignment.homework)
        self.assignment_result = AssignmentResultFactory.create(
            student=self.student, assignment=self.assignment, points=80
        )
        self.question_answer_result1 = QuestionAnswerPairResultFactory.create(
            assignment=self.assignment, student=self.student, question=self.question1, points=10
        )
        self.question_answer_result2 = QuestionAnswerPairResultFactory.create(
            assignment=self.assignment, student=self.student, question=self.question2, points=20
        )

    def test_list_student_statistics(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('one_student_answers', kwargs={'assignment_id': self.assignment.id, 'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['points'], calculate_assignment_points(self.assignment))
        self.assertEqual(response.data['score'], calculate_score(self.student, self.assignment))
        self.assertEqual(response.data['grade'], calculate_grade(response.data['score'], self.assignment))
        self.assertEqual(len(response.data['results']), 2) 

    def test_list_student_statistics_invalid_assignment_id(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('one_student_answers', kwargs={'assignment_id': 999, 'student_id': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_student_statistics_invalid_student_id(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('one_student_answers', kwargs={'assignment_id': self.assignment.id, 'student_id': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
         

class HomeworkViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = CustomUserFactory.create(role=2)
        self.student = CustomUserFactory.create(role=1)
        self.group_teacher, _ = Group.objects.get_or_create(name='teacher')
        self.teacher.groups.add(self.group_teacher)
        self.homework = HomeworkFactory(teacher=self.teacher)

    def test_retrieve_homework_teacher(self):
        self.client.force_login(self.teacher)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_homework_student(self):
        self.client.force_login(self.student)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_homework_teacher_invalid_data(self):
        self.client.force_login(self.teacher)
        url = reverse('homework-list')
        data = {'title': 'New Homework'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_homework_student(self):
        self.client.force_login(self.student)
        url = reverse('homework-list')
        data = {'title': 'New Homework'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_homework_teacher(self):
        self.client.force_login(self.teacher)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        data = {'title': 'Updated Homework'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_homework_student(self):
        self.client.force_login(self.student)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        data = {'title': 'Updated Homework'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_homework_teacher(self):
        self.client.force_login(self.teacher)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_homework_student(self):
        self.client.force_login(self.student)
        url = reverse('homework-detail', kwargs={'pk': self.homework.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)     

class TestViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group_student, _ = Group.objects.get_or_create(name='student')
        self.student = CustomUserFactory.create()
        self.student.groups.add(self.group_student)
        self.homework = HomeworkFactory.create()
        self.assignment = AssignmentFactory.create(pk=1, homework=self.homework)
        self.question1 = QuestionAnswerPairFactory.create(homework=self.homework, qtype=1, points=10)
        self.question2 = QuestionAnswerPairFactory.create(homework=self.homework, qtype=2, points=20)
        self.question3 = QuestionAnswerPairFactory.create(homework=self.homework, qtype=3, points=30)
        self.url = reverse('test', kwargs={'assignment_id': 1})

    def test_get_questions(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_post_answers_invalid_assignment_id(self):
        self.client.force_login(self.student)
        invalid_url = reverse('test', kwargs={'assignment_id': 999})
        data = {'time': 10000, 'pairs': []}
        response = self.client.post(invalid_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_answers_invalid_data(self):
        self.client.force_login(self.student)
        data = {'pairs': []}  # no time
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)            


class SchoolViewAdminTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUserFactory.create(is_superuser=True, is_staff=True, role=3)
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';')
        writer.writerow(['Ona', 'Onaite', '8B', 'moteris'])
        self.csv_file = SimpleUploadedFile("file.csv", csv_data.getvalue().encode())

    def test_create_school(self):
        self.client.force_login(self.admin)
        url = reverse('school-list')
        data = {
            'title': 'Test School',
            'license': '2024-12-31',
            'file': self.csv_file
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_school_duplicate(self):
        self.client.force_login(self.admin)
        existing_school = School.objects.create(title='Existing School', license_end='2024-12-31')
        url = reverse('school-list')
        data = {
            'title': 'Existing School', 
            'license': '2024-12-31',
            'file': self.csv_file
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_school_empty_file(self):
        self.client.force_login(self.admin)
        url = reverse('school-list')
        data = {
            'title': 'Test School',
            'license': '2024-12-31',
            'file': SimpleUploadedFile("empty.csv", b"")
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)        


class UpdateViewSchoolTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUserFactory.create(is_superuser=True, is_staff=True, role=3)
        self.school = SchoolFactory.create()

    def test_update_school(self):
        self.client.force_login(self.admin)

        data = {
            'title': 'New Title',
            'license': '2025-12-31',
        }
        url = reverse('school-update', kwargs={'school_id': self.school.id})
        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.school.refresh_from_db()
        self.assertEqual(self.school.title, 'New Title')
        self.assertEqual(str(self.school.license_end), '2025-12-31')

    def test_update_nonexistent_school(self):
        data = {
            'title': 'New Title',
            'license': '2025-12-31',
        }
        url = reverse('school-update', kwargs={'school_id': 999})
        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)        