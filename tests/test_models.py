from django.test import TestCase
from homework_app.factory import *

class SchoolTest(TestCase):
    def test_school_creation(self):
        school = SchoolFactory()
        self.assertIsNotNone(school)

        