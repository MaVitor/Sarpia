from django.urls import path

from api.views import (
    AvaliarView,
    MateriaisView,
    PerguntasView,
    SaudeView,
    TopicosView,
)

urlpatterns = [
    path("saude/", SaudeView.as_view()),
    path("materiais/", MateriaisView.as_view()),
    path("topicos/", TopicosView.as_view()),
    path("avaliar/", AvaliarView.as_view()),
    path("perguntas/", PerguntasView.as_view()),
]
