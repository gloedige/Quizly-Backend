from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


GENERATED_QUESTIONS = [
	{
		'question_title': f'Question {index}',
		'question_options': ['A', 'B', 'C', 'D'],
		'answer': 'A',
	}
	for index in range(1, 11)
]
GENERATED_QUIZ = {
	'title': 'Science Quiz',
	'description': 'A short science quiz.',
	'questions': GENERATED_QUESTIONS,
}


class QuizEndpointTests(TestCase):
	"""Exercise the quiz API through its public HTTP endpoints."""

	def setUp(self):
		"""Create a user and authenticate the API client with login cookies."""
		self.client = APIClient()
		self.user = get_user_model().objects.create_user('quiz-user', password='pass')
		self.client.post('/api/login/', {'username': 'quiz-user', 'password': 'pass'})

	def create_quiz(self, client=None, url='https://youtu.be/dQw4w9WgXcQ'):
		"""Create a quiz through the public API with external generation mocked."""
		api_client = client or self.client
		with patch('quiz_app.api.views.generate_quiz_content', return_value=GENERATED_QUIZ):
			return api_client.post('/api/quizzes/', {'url': url}, format='json')

	def test_create_quiz_canonicalizes_youtube_url_and_returns_ten_questions(self):
		"""Create returns a canonical URL and the generated quiz payload."""
		canonical_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
		with patch('quiz_app.api.views.generate_quiz_content', return_value=GENERATED_QUIZ):
			response = self.client.post('/api/quizzes/', {'url': 'https://youtu.be/dQw4w9WgXcQ'}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data['video_url'], canonical_url)
		self.assertEqual(len(response.data['questions']), 10)

	def test_create_quiz_accepts_browser_and_share_urls(self):
		"""Both YouTube URL forms resolve to the same canonical watch URL."""
		urls = ['https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'https://youtu.be/dQw4w9WgXcQ']
		for url in urls:
			with patch('quiz_app.api.views.generate_quiz_content', return_value=GENERATED_QUIZ):
				response = self.client.post('/api/quizzes/', {'url': url}, format='json')
			self.assertEqual(response.status_code, 201)
			self.assertEqual(response.data['video_url'], 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')

	def test_create_quiz_rejects_non_youtube_url(self):
		"""Reject non-YouTube URLs without calling the generation service."""
		with patch('quiz_app.api.views.generate_quiz_content') as generate:
			response = self.client.post('/api/quizzes/', {'url': 'https://example.com/video'}, format='json')
		self.assertEqual(response.status_code, 400)
		generate.assert_not_called()

	def test_create_quiz_generation_failure_returns_400_without_saving(self):
		"""A provider failure returns 400 and does not create a quiz."""
		with patch('quiz_app.api.views.generate_quiz_content', side_effect=RuntimeError('provider unavailable')):
			response = self.client.post('/api/quizzes/', {'url': 'https://youtu.be/dQw4w9WgXcQ'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertEqual(self.client.get('/api/quizzes/').data, [])

	def test_create_quiz_rejects_wrong_question_count(self):
		"""Reject AI output that does not contain exactly ten questions."""
		invalid_quiz = {**GENERATED_QUIZ, 'questions': GENERATED_QUESTIONS[:-1]}
		with patch('quiz_app.api.views.generate_quiz_content', return_value=invalid_quiz):
			response = self.client.post('/api/quizzes/', {'url': 'https://youtu.be/dQw4w9WgXcQ'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertEqual(self.client.get('/api/quizzes/').data, [])

	def test_create_quiz_rejects_duplicate_options(self):
		"""Reject generated questions that do not have four distinct options."""
		questions = [dict(question, question_options=['A', 'A', 'B', 'C']) for question in GENERATED_QUESTIONS]
		invalid_quiz = {**GENERATED_QUIZ, 'questions': questions}
		with patch('quiz_app.api.views.generate_quiz_content', return_value=invalid_quiz):
			response = self.client.post('/api/quizzes/', {'url': 'https://youtu.be/dQw4w9WgXcQ'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertEqual(self.client.get('/api/quizzes/').data, [])

	def test_create_quiz_requires_authentication(self):
		"""Anonymous callers cannot create or list quizzes."""
		client = APIClient()
		self.assertEqual(client.post('/api/quizzes/', {'url': 'https://youtu.be/dQw4w9WgXcQ'}, format='json').status_code, 401)
		self.assertEqual(client.get('/api/quizzes/').status_code, 401)

	def test_quiz_list_contains_only_the_authenticated_users_quizzes(self):
		"""The collection endpoint returns only the caller's quizzes."""
		self.create_quiz()
		other_client = APIClient()
		other_client.post('/api/register/', {'username': 'other', 'email': 'other@example.com', 'password': 'pass', 'confirmed_password': 'pass'}, format='json')
		other_client.post('/api/login/', {'username': 'other', 'password': 'pass'}, format='json')
		self.create_quiz(client=other_client)
		response = self.client.get('/api/quizzes/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)

	def test_quiz_detail_denies_access_to_another_owner(self):
		"""A different authenticated user receives 403 for a quiz detail."""
		quiz_id = self.create_quiz().data['id']
		other_client = APIClient()
		other_client.post('/api/register/', {'username': 'other', 'email': 'other@example.com', 'password': 'pass', 'confirmed_password': 'pass'}, format='json')
		other_client.post('/api/login/', {'username': 'other', 'password': 'pass'}, format='json')
		response = other_client.get(f'/api/quizzes/{quiz_id}/')
		self.assertEqual(response.status_code, 403)
		self.assertEqual(other_client.patch(f'/api/quizzes/{quiz_id}/', {'title': 'Hack'}, format='json').status_code, 403)
		self.assertEqual(other_client.delete(f'/api/quizzes/{quiz_id}/').status_code, 403)

	def test_quiz_detail_returns_404_for_unknown_id(self):
		"""A nonexistent quiz uses the documented not-found response."""
		self.assertEqual(self.client.get('/api/quizzes/999/').status_code, 404)

	def test_owner_can_retrieve_and_partially_update_quiz(self):
		"""The owner can retrieve a quiz and patch its title and description."""
		quiz_id = self.create_quiz().data['id']
		response = self.client.get(f'/api/quizzes/{quiz_id}/')
		self.assertEqual(response.status_code, 200)
		response = self.client.patch(f'/api/quizzes/{quiz_id}/', {'title': 'Updated'}, format='json')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['title'], 'Updated')
		self.assertIn('questions', response.data)

	def test_owner_can_delete_quiz(self):
		"""Deleting an owned quiz returns 204 and removes it from the collection."""
		quiz_id = self.create_quiz().data['id']
		response = self.client.delete(f'/api/quizzes/{quiz_id}/')
		self.assertEqual(response.status_code, 204)
		self.assertEqual(self.client.get('/api/quizzes/').data, [])
