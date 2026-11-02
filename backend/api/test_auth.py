from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class AutenticacaoTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        csrf = self.client.get("/api/auth/csrf/")
        self.assertEqual(csrf.status_code, 200)
        self.csrf = self.client.cookies["csrftoken"].value
        self.headers = {"HTTP_X_CSRFTOKEN": self.csrf}

    def post_json(self, url, data, csrf=True):
        headers = self.headers if csrf else {}
        return self.client.post(
            url, data, content_type="application/json", **headers
        )

    def test_sessao_anônima_e_cadastro_válido(self):
        anonima = self.client.get("/api/auth/session/")
        self.assertEqual(anonima.json(), {"autenticado": False, "usuario": None})

        resposta = self.post_json(
            "/api/auth/signup/",
            {
                "nome": "Ada Lovelace",
                "email": "Ada@Example.com",
                "password": "Uma senha forte 123!",
                "password2": "Uma senha forte 123!",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        usuario = get_user_model().objects.get(email="ada@example.com")
        self.assertEqual(usuario.first_name, "Ada Lovelace")
        self.assertNotIn("password", resposta.json()["data"]["user"])

    def test_cadastro_rejeita_confirmacao_e_senha_invalidas(self):
        resposta = self.post_json(
            "/api/auth/signup/",
            {
                "nome": "Pessoa",
                "email": "pessoa@example.com",
                "password": "123",
                "password2": "456",
            },
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_login_válido_inválido_e_logout(self):
        get_user_model().objects.create_user(
            username="login",
            email="login@example.com",
            password="Uma senha forte 123!",
        )
        invalido = self.post_json(
            "/api/auth/login/",
            {"email": "login@example.com", "password": "errada"},
        )
        self.assertEqual(invalido.status_code, 400)
        valido = self.post_json(
            "/api/auth/login/",
            {"email": "login@example.com", "password": "Uma senha forte 123!"},
        )
        self.assertEqual(valido.status_code, 200)
        self.assertTrue(self.client.get("/api/auth/session/").json()["autenticado"])
        self.headers["HTTP_X_CSRFTOKEN"] = self.client.cookies["csrftoken"].value
        logout = self.post_json("/api/auth/logout/", {})
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(self.client.get("/api/auth/session/").json()["autenticado"])

    def test_operacoes_mutáveis_sem_csrf_são_rejeitadas(self):
        resposta = self.post_json(
            "/api/auth/login/",
            {"email": "x@example.com", "password": "x"},
            csrf=False,
        )
        self.assertEqual(resposta.status_code, 403)

    def test_endpoints_de_analise_rejeitam_anônimo_antes_do_gemini(self):
        with patch("api.views.gemini.gerar_estruturado") as gerar:
            resposta = self.post_json(
                "/api/topicos/",
                {"paginas": [{"numero": 1, "texto": "Material"}]},
            )
        self.assertEqual(resposta.status_code, 403)
        gerar.assert_not_called()

    def test_rota_google_nao_existe(self):
        resposta = self.client.post(
            "/api/auth/google/start/",
            {},
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 404)
