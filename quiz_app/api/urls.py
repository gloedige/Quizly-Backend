from rest_framework.routers import SimpleRouter

from quiz_app.api.views import QuizViewSet


app_name = 'quiz_api'
router = SimpleRouter()
router.register('quizzes', QuizViewSet, basename='quiz')
urlpatterns = router.urls
