from django.urls import path

from api.views import (
    AuthCsrfView,
    AuthLogoutView,
    AuthSessionView,
    AuthSignupView,
    AuthLoginView,
    ApresentacaoDetalheView,
    ApresentacoesView,
    AvaliarView,
    MateriaisView,
    PerguntasView,
    SaudeView,
    TentativaDetalheView,
    TopicosView,
)

urlpatterns = [
    path("auth/csrf/", AuthCsrfView.as_view()),
    path("auth/session/", AuthSessionView.as_view()),
    path("auth/login/", AuthLoginView.as_view()),
    path("auth/signup/", AuthSignupView.as_view()),
    path("auth/logout/", AuthLogoutView.as_view()),
    path("apresentacoes/", ApresentacoesView.as_view()),
    path("apresentacoes/<uuid:presentation_id>/", ApresentacaoDetalheView.as_view()),
    path(
        "apresentacoes/<uuid:presentation_id>/tentativas/<uuid:attempt_id>/",
        TentativaDetalheView.as_view(),
    ),
    path("saude/", SaudeView.as_view()),
    path("materiais/", MateriaisView.as_view()),
    path("topicos/", TopicosView.as_view()),
    path("avaliar/", AvaliarView.as_view()),
    path("perguntas/", PerguntasView.as_view()),
]
