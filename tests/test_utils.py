from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser,Group
from homework_app.factory import *
from homework_app.utils import *
from homework_app.models import *
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
from io import StringIO

class GenerateCsrfTokenTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generate_csrf_token(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        csrf_token = generate_csrf_token(request)
        self.assertIsNotNone(csrf_token)


class GenerateEmailPasswordTestCase(TestCase):
    def test_generate_email_password(self):
        first_name = "Jonas"
        last_name = "Jonaitis"
        email, password = generate_email_password(first_name, last_name)

        self.assertTrue(email.endswith('@goose.lt'))
        self.assertTrue(len(password) >= 8)
        self.assertFalse(CustomUser.objects.filter(email=email).exists())


class GetCurrentSchoolYearTestCase(TestCase):
    def test_get_current_school_year(self):
        start_date, end_date = get_current_school_year()
        self.assertIsInstance(start_date, date)
        self.assertIsInstance(end_date, date)


class GetAssignmentStatusTestCase(TestCase):
    def setUp(self):
        self.assignment = AssignmentFactory.create()
        self.classs = self.assignment.classs
        self.student1 = CustomUserFactory.create(classs=self.classs)
        self.student2 = CustomUserFactory.create(classs=self.classs)
        self.student3 = CustomUserFactory.create(classs=self.classs)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
    
    def test_get_completed_students_count(self):
        count = get_completed_students_count(self.assignment)
        self.assertEqual(count, 1)
    
    def test_get_assignment_status_average(self):
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student3)
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Average')
    
    def test_get_assignment_status_good(self):
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student2)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student3)
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Good')

    def test_get_assignment_status_bad(self):
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Bad')        


class CalculateScoreTestCase(TestCase):
    def setUp(self):
        self.student = CustomUserFactory.create()
        self.assignment = AssignmentFactory.create()

    def test_calculate_score_no_results(self):
        score = calculate_score(self.student, self.assignment)
        self.assertEqual(score, 0)

    def test_calculate_score_with_results(self):
        QuestionAnswerPairResultFactory.create(student=self.student,assignment=self.assignment, points=10)
        score = calculate_score(self.student, self.assignment)
        self.assertEqual(score, 10)        


class CalculateAssignmentPointsTestCase(TestCase):
    def setUp(self):
        self.assignment = AssignmentFactory.create()
        self.question_1 = QuestionAnswerPairFactory.create(homework=self.assignment.homework)
        self.question_2 = QuestionAnswerPairFactory.create(homework=self.assignment.homework)

    def test_calculate_assignment_points_no_questions(self):
        assignment = AssignmentFactory.create()
        points = calculate_assignment_points(assignment)
        self.assertEqual(points, 0)

    def test_calculate_assignment_points_with_questions(self):
        points = calculate_assignment_points(self.assignment)
        expected_points = self.question_1.points + self.question_2.points
        self.assertEqual(points, expected_points)


class CreateCorrectOptionTestCase(TestCase):
    def setUp(self):
        self.question = QuestionAnswerPairFactory.create()
        self.option = OptionFactory.create(question=self.question)

    def test_create_correct_option_success(self):
        response = create_correct_option(self.question, self.option)
        self.assertEqual(QuestionCorrectOption.objects.filter(question=self.question, option=self.option).exists(), True)
        self.assertEqual(response, None)


class ProcessAnswerTestCase(TestCase):
    def setUp(self):
        self.question = QuestionAnswerPairFactory.create( points=10)
        self.option1 = OptionFactory.create(question=self.question)
        self.option2 = OptionFactory.create(question=self.question)
        self.option3 = OptionFactory.create(question=self.question)
        QuestionCorrectOptionFactory.create(question=self.question, option=self.option1)
        QuestionCorrectOptionFactory.create(question=self.question, option=self.option2)

    def test_one_option_selected_correct(self):
        selected = '0' 
        points, selected_options = process_answer(self.question, selected)
        self.assertEqual(points, 5) 
        self.assertEqual(selected_options, [self.option1])

    def test_multiple_options_selected_correct(self):
        selected = '0,1' 
        points, selected_options = process_answer(self.question, selected)
        self.assertEqual(points, 10)
        self.assertEqual(selected_options, [self.option1, self.option2])

    def test_one_option_selected_incorrect(self):
        selected = '2' 
        points, selected_options = process_answer(self.question, selected)
        self.assertEqual(points, 0)
        self.assertEqual(selected_options, [self.option3])

    def test_combination_of_correct_and_incorrect_options(self):
        selected = '0,2'
        points, selected_options = process_answer(self.question, selected)
        self.assertEqual(points, 0)
        self.assertEqual(selected_options, [self.option1, self.option3])

    def test_no_option_selected(self):
        selected = ''
        points, selected_options = process_answer(self.question, selected)
        self.assertEqual(points, 0)
        self.assertEqual(selected_options, [])    


class UpdateOrCreateMembersTestCase(TestCase):
    def setUp(self):
        self.school = SchoolFactory.create()
        self.classs = ClassFactory.create(school=self.school)
        self.group_student, _ = Group.objects.get_or_create(name='student')
        self.group_teacher, _ = Group.objects.get_or_create(name='teacher')

    def test_valid_file(self):
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';')
        writer.writerow(['Jonas', 'Jonaitis', '8A', 'vyras'])
        csv_file = SimpleUploadedFile("file.csv", csv_data.getvalue().encode())
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(CustomUser.objects.first().first_name, 'Jonas')
        self.assertEqual(CustomUser.objects.first().last_name, 'Jonaitis')
        self.assertTrue(CustomUser.objects.first().groups.filter(name='student').exists())

    def test_invalid_file_empty(self):
        csv_file = SimpleUploadedFile("file.csv", b"")
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_invalid_file_wrong_format(self):
        csv_file = SimpleUploadedFile("file.csv", b"John")
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_existing_user_update(self):
        existing_user = CustomUserFactory.create(first_name="Ona", last_name="Onaite", email="ona@example.com", classs = self.classs, school=self.school)
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';')
        writer.writerow(['Ona', 'Onaite', '8B', 'moteris'])
        csv_file = SimpleUploadedFile("file.csv", csv_data.getvalue().encode())
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.filter(first_name="Ona").first().classs.title, '8B')
        self.assertEqual(CustomUser.objects.filter(first_name="Ona").first().gender, 2)

    def test_new_user_created(self):
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';')
        writer.writerow(['Mokytoja', 'Mokytojauskiene', '', 'moteris'])
        csv_file = SimpleUploadedFile("file.csv", csv_data.getvalue().encode())
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(CustomUser.objects.first().first_name, 'Mokytoja')

    def test_existing_user_deleted(self):
        existing_user1 = CustomUserFactory.create(school=self.school)
        existing_user2 = CustomUserFactory.create(school=self.school)
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';')
        writer.writerow(['Ona', 'Onaite', '8B', 'moteris'])
        csv_file = SimpleUploadedFile("file.csv", csv_data.getvalue().encode())
        update_or_create_members(csv_file, self.school)
        self.assertEqual(CustomUser.objects.count(), 1)            