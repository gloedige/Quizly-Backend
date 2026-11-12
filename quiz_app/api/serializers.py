# Third-party
from rest_framework import serializers

# Local imports
from quiz_app.models import Question, Quiz
from quiz_app.services import canonicalize_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    """Serialize generated questions for quiz responses."""

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer', 'created_at', 'updated_at']
        read_only_fields = fields


class QuizSerializer(serializers.ModelSerializer):
    """Serialize quizzes and their ordered question collection."""
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'created_at', 'updated_at', 'video_url', 'questions']
        read_only_fields = fields


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Validate allowed partial edits to a quiz."""

    class Meta:
        model = Quiz
        fields = ['title', 'description']


class QuizCreateSerializer(serializers.Serializer):
    """Validate and canonicalize a YouTube URL submitted for quiz generation."""
    url = serializers.CharField(max_length=2048)

    def validate_url(self, value):
        """Return the canonical watch URL or a field validation error."""
        try:
            return canonicalize_youtube_url(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error


class GeneratedQuestionSerializer(serializers.Serializer):
    """Validate one AI-generated question and its correct answer."""
    question_title = serializers.CharField(max_length=500)
    question_options = serializers.ListField(child=serializers.CharField(max_length=500))
    answer = serializers.CharField(max_length=500)

    def validate(self, attrs):
        """Require four distinct options and exactly one listed answer."""
        options = attrs['question_options']
        if len(options) != 4 or len(set(options)) != 4 or attrs['answer'] not in options:
            raise serializers.ValidationError('Each question requires four distinct options and a listed answer.')
        return attrs


class GeneratedQuizSerializer(serializers.Serializer):
    """Validate the AI response before any quiz data is persisted."""
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=150)
    questions = GeneratedQuestionSerializer(many=True)

    def validate_questions(self, value):
        """Require the required ten generated questions."""
        if len(value) != 10:
            raise serializers.ValidationError('The generated quiz must contain exactly 10 questions.')
        return value
