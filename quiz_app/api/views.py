# Third-party
from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Local imports
from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import (
    GeneratedQuizSerializer,
    QuizCreateSerializer,
    QuizSerializer,
    QuizUpdateSerializer,
)
from quiz_app.models import Question, Quiz
from quiz_app.services import generate_quiz_content


class QuizViewSet(viewsets.ModelViewSet):
    """Provide authenticated quiz CRUD and synchronous YouTube generation."""
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """List only owned quizzes and use object permissions for detail actions."""
        queryset = Quiz.objects.prefetch_related('questions')
        return queryset.filter(owner=self.request.user) if self.action == 'list' else queryset

    def get_serializer_class(self):
        """Select write serializers for generation input and partial edits."""
        if self.action == 'create':
            return QuizCreateSerializer
        if self.action == 'partial_update':
            return QuizUpdateSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        """Generate and persist a quiz synchronously from a YouTube URL."""
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        quiz = self._generate_quiz(request.user, request_serializer.validated_data['url'])
        return Response(QuizSerializer(quiz).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Return the complete quiz representation after a partial edit."""
        response = super().partial_update(request, *args, **kwargs)
        return Response(QuizSerializer(self.get_object()).data, status=response.status_code)

    def _generate_quiz(self, owner, canonical_url):
        """Validate generated content and persist the quiz atomically."""
        try:
            generated = GeneratedQuizSerializer(data=generate_quiz_content(canonical_url))
            generated.is_valid(raise_exception=True)
        except Exception as error:
            raise serializers.ValidationError('Unable to generate a quiz from this video.') from error
        return save_generated_quiz(owner, canonical_url, generated.validated_data)


def save_generated_quiz(owner, canonical_url, generated_data):
    """Save a quiz and its generated questions in one transaction."""
    questions = generated_data['questions']
    quiz_data = {key: value for key, value in generated_data.items() if key != 'questions'}
    with transaction.atomic():
        quiz = Quiz.objects.create(owner=owner, video_url=canonical_url, **quiz_data)
        Question.objects.bulk_create([Question(quiz=quiz, **item) for item in questions])
    return quiz
