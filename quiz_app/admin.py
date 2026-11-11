from django.contrib import admin

from quiz_app.models import Question, Quiz


class QuestionInline(admin.TabularInline):
	"""Edit quiz questions on the parent quiz admin page."""

	model = Question
	extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
	"""Provide searchable quiz management with inline questions."""

	list_display = ('title', 'owner', 'video_url', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('title', 'owner__username')
	inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	"""Provide a dedicated question admin view."""

	list_display = ('question_title', 'quiz', 'answer')
	search_fields = ('question_title', 'quiz__title')
