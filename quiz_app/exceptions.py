from rest_framework import status
from rest_framework.exceptions import APIException

class QuizGenerationError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An internal error occurred while generating the quiz.'
    default_code = 'quiz_generation_failed'