from django.conf import settings
from django.db import models


class Quiz(models.Model):
	"""Store a generated quiz and its owning user."""

	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quizzes')
	title = models.CharField(max_length=255)
	description = models.CharField(max_length=150)
	video_url = models.URLField(max_length=2048)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-created_at',)
		verbose_name = 'quiz'
		verbose_name_plural = 'quizzes'

	def __str__(self):
		"""Return the quiz title for admin and shell displays."""
		return self.title


class Question(models.Model):
	"""Store one generated question and its four answer options."""

	quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
	question_title = models.CharField(max_length=500)
	question_options = models.JSONField()
	answer = models.CharField(max_length=500)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('id',)
		verbose_name = 'question'
		verbose_name_plural = 'questions'

	def __str__(self):
		"""Return the question text for admin and shell displays."""
		return self.question_title
