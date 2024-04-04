from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from homework_app.factory import AssignmentFactory, CustomUserFactory, OptionFactory, QuestionAnswerPairFactory, QuestionAnswerPairResultFactory
from homework_app.models import *

class QuestionsViewGameTestCase(APITestCase):
    def setUp(self):
        self.assignment = AssignmentFactory.create()
        self.student = CustomUserFactory.create()
        self.question = QuestionAnswerPairFactory.create(homework=self.assignment.homework, qtype=2)
        self.questionselect = QuestionAnswerPairFactory.create(homework=self.assignment.homework, qtype = 3)
        self.option1 = OptionFactory.create(question=self.questionselect)
        self.option2 = OptionFactory.create(question=self.questionselect)
        

    def test_list_questions(self):
        url = reverse('game', kwargs={'assignment_id': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('questions', response.data)

    def test_post_answer_simple(self):
        url = reverse('game', kwargs={'assignment_id': self.assignment.id})
        data = {
            'assignment_id': self.assignment.id,
            'question_id': self.question.id,
            'answer': 'answer',
            'student_id': self.student.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post_answer_select(self):
        url = reverse('game', kwargs={'assignment_id': self.assignment.id})
        data = {
            'assignment_id': self.assignment.id,
            'question_id': self.questionselect.id,
            'answer': 'answer',
            'student_id': self.student.id,
            'selected': 0
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)    

    def test_post_answer_select_update(self):
        self.previous_answer = QuestionAnswerPairResultFactory.create(assignment=self.assignment, question=self.questionselect, student=self.student)
        url = reverse('game', kwargs={'assignment_id': self.assignment.id})
        data = {
            'assignment_id': self.assignment.id,
            'question_id': self.questionselect.id,
            'answer': 'answer',
            'student_id': self.student.id,
            'selected': 1
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)        

    def test_post_answer_invalid_data(self):
        url = reverse('game', kwargs={'assignment_id': self.assignment.id})
        data = {} 
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SummaryViewTestCase(APITestCase):
    def setUp(self):
        self.student = CustomUserFactory.create()
        self.assignment = AssignmentFactory.create()
        self.question_result = QuestionAnswerPairResultFactory.create(assignment=self.assignment, student=self.student)

    def test_create_summary(self):
        url = reverse('post_summary')
        data = {
            'assignment_id': self.assignment.id,
            'student_id': self.student.id,
            'time' : '00:10:00',
            'points': 200
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AssignmentResult.objects.filter(assignment=self.assignment,student=self.student).exists())

    def test_invalid_data(self):
        url = reverse('post_summary')
        data = {
            'assignment_id': self.assignment.id,
            'student_id': self.student.id,
            'points': 20
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)