from unittest.mock import patch

import fitz
from django.test import SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from api.schemas import (
    FeedbackResponse,
    OrdemApresentacao,
    TopicoAvaliado,
)
from api.services import pdf
from api.services import gemini
from api.services.gemini import GeminiErro


class SaudeTests(SimpleTestCase):
    def test_saude_retorna_ok(self):
        resposta = self.client.get("/api/saude/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "ok")


class ApiValidacaoTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.paginas = [{"numero": 1, "texto": "Conteúdo útil do slide."}]

    def test_rejeita_paginas_vazias(self):
        resposta = self.client.post("/api/topicos/", {"paginas": []}, format="json")
        self.assertEqual(resposta.status_code, 400)

    def test_rejeita_material_sem_texto(self):
        resposta = self.client.post(
            "/api/topicos/",
            {"paginas": [{"numero": 1, "texto": "   "}]},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("texto útil", str(resposta.json()))

    def test_rejeita_ensaio_invalido(self):
        resposta = self.client.post(
            "/api/avaliar/",
            {"paginas": self.paginas, "ensaio": " " * 20},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    @override_settings(MAX_CARACTERES_MATERIAL=5)
    def test_rejeita_material_acima_do_limite(self):
        resposta = self.client.post(
            "/api/perguntas/",
            {"paginas": self.paginas},
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)


class PDFTests(SimpleTestCase):
    @staticmethod
    def _pdf_com_paginas(textos):
        documento = fitz.open()
        for texto in textos:
            pagina = documento.new_page()
            pagina.insert_text((72, 72), texto)
        conteudo = documento.tobytes()
        documento.close()
        return conteudo

    def test_extrai_pdf_textual_preservando_numeracao(self):
        paginas, aviso = pdf.extrair_texto(
            self._pdf_com_paginas(["primeira", "segunda"]), max_paginas=20
        )
        self.assertEqual([pagina.numero for pagina in paginas], [1, 2])
        self.assertEqual([pagina.texto for pagina in paginas], ["primeira", "segunda"])
        self.assertIsNotNone(aviso)

    def test_upload_ausente_vazio_invalido_e_acima_do_limite(self):
        self.assertEqual(self.client.post("/api/materiais/").status_code, 400)
        vazio = self.client.post(
            "/api/materiais/",
            {"arquivo": SimpleUploadedFile("vazio.pdf", b"", content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(vazio.status_code, 400)
        invalido = self.client.post(
            "/api/materiais/",
            {"arquivo": SimpleUploadedFile("invalido.pdf", b"nao e pdf")},
            format="multipart",
        )
        self.assertEqual(invalido.status_code, 422)
        with override_settings(MAX_PDF_MB=0):
            grande = self.client.post(
                "/api/materiais/",
                {"arquivo": SimpleUploadedFile("grande.pdf", b"pdf")},
                format="multipart",
            )
        self.assertEqual(grande.status_code, 413)

    def setUp(self):
        self.client = APIClient()


class GeminiViewTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "paginas": [{"numero": 1, "texto": "Material de referência."}],
            "ensaio": "Este é um ensaio suficientemente longo para análise.",
        }

    @staticmethod
    def _feedback(topicos):
        return FeedbackResponse(
            resumo_geral="Resumo",
            cobertura_percentual=99,
            topicos=topicos,
            erros_conteudo=[],
            info_nao_sustentada=[],
            ordem_apresentacao=OrdemApresentacao(
                avaliacao="adequada", sugestao="manter"
            ),
            perguntas_banca=[],
            proximo_passo="reensaiar",
        )

    def test_avaliacao_calcula_cobertura_no_backend(self):
        resultado = self._feedback(
            [
                TopicoAvaliado(
                    titulo="A", slide=1, status="coberto", trecho_material="",
                    trecho_ensaio="", comentario=""
                ),
                TopicoAvaliado(
                    titulo="B", slide=1, status="parcial", trecho_material="",
                    trecho_ensaio="", comentario=""
                ),
                TopicoAvaliado(
                    titulo="C", slide=1, status="omitido", trecho_material="",
                    trecho_ensaio="", comentario=""
                ),
            ]
        )
        with patch("api.views.gemini.gerar_estruturado", return_value=resultado):
            resposta = self.client.post("/api/avaliar/", self.payload, format="json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["cobertura_percentual"], 67)

        with patch(
            "api.views.gemini.gerar_estruturado",
            return_value=self._feedback([]),
        ):
            resposta = self.client.post("/api/avaliar/", self.payload, format="json")
        self.assertEqual(resposta.json()["cobertura_percentual"], 0)

    def test_resposta_vazia_ou_invalida_da_ia(self):
        for erro in (
            GeminiErro(502, "O serviço de análise retornou uma resposta vazia."),
            GeminiErro(502, "O serviço de análise retornou dados em formato inválido."),
        ):
            with patch("api.views.gemini.gerar_estruturado", side_effect=erro):
                resposta = self.client.post(
                    "/api/avaliar/", self.payload, format="json"
                )
            self.assertEqual(resposta.status_code, 502)
            self.assertNotIn("google", str(resposta.data).lower())

    def test_provedor_indisponivel_e_limite_temporario(self):
        for erro in (GeminiErro(503, "indisponível"), GeminiErro(429, "temporário")):
            with patch("api.views.gemini.gerar_estruturado", side_effect=erro):
                resposta = self.client.post(
                    "/api/avaliar/", self.payload, format="json"
                )
            self.assertEqual(resposta.status_code, erro.status)

    @override_settings(GEMINI_MAX_TENTATIVAS=1)
    def test_falha_do_provedor_tem_log_sanitizado(self):
        erro = gemini.genai_errors.ClientError(503, {"error": {"message": "segredo"}})
        with patch("api.services.gemini._chamar_gemini", side_effect=erro):
            with self.assertLogs("api.services.gemini", level="WARNING") as registros:
                with self.assertRaises(GeminiErro):
                    gemini.gerar_estruturado("prompt privado", FeedbackResponse)
        log = "\n".join(registros.output)
        self.assertIn("operacao=generate_content", log)
        self.assertIn("excecao=ClientError", log)
        self.assertIn("codigo_provedor=503", log)
        self.assertNotIn("segredo", log)
        self.assertNotIn("prompt privado", log)
