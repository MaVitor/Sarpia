import re
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
from api.services import prompts
from api.views import _calcular_cobertura


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

    def test_cobertura_usa_apenas_topicos_principais(self):
        principais = [
            TopicoAvaliado(
                titulo=f"P{i}", slide=1, status="coberto",
                trecho_material="", trecho_ensaio="", comentario=""
            )
            for i in range(10)
        ]
        complementares = [
            TopicoAvaliado(
                titulo="Crédito", slide=1, status="omitido",
                trecho_material="", trecho_ensaio="", comentario=""
            )
        ]
        resultado = self._feedback(principais).model_copy(
            update={"topicos_complementares": complementares}
        )
        self.assertEqual(_calcular_cobertura(resultado), 100)

        parcial = principais[:9] + [
            TopicoAvaliado(
                titulo="P9", slide=1, status="parcial",
                trecho_material="", trecho_ensaio="", comentario=""
            )
        ]
        self.assertEqual(
            _calcular_cobertura(
                self._feedback(parcial).model_copy(
                    update={"topicos_complementares": complementares}
                )
            ),
            100,
        )
        omitido = principais[:9] + [
            TopicoAvaliado(
                titulo="P9", slide=1, status="omitido",
                trecho_material="", trecho_ensaio="", comentario=""
            )
        ]
        self.assertEqual(_calcular_cobertura(self._feedback(omitido)), 90)
        self.assertEqual(_calcular_cobertura(self._feedback([])), 0)

    def test_resposta_antiga_sem_complementares_e_aceita(self):
        dados = self._feedback([]).model_dump()
        dados.pop("topicos_complementares", None)
        resultado = FeedbackResponse.model_validate(dados)
        self.assertEqual(resultado.topicos_complementares, [])

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


class PromptTests(SimpleTestCase):
    def test_prompt_de_avaliacao_define_criterios_de_fundamentacao(self):
        prompt = prompts.prompt_avaliacao(
            "[Slide 1]\nO viés pode surgir na coleta e no treinamento.",
            "O viés não surge apenas depois da implantação.",
        )
        prompt_lower = re.sub(r"\s+", " ", prompt.lower())
        self.assertIn("paráfrases fiéis", prompt)
        self.assertIn("inferências diretamente decorrentes", prompt)
        self.assertIn("Compare significados", prompt)
        self.assertIn("números, datas, estudos", prompt)
        self.assertIn("contradizer o material", prompt)
        self.assertIn("não equivale a", prompt)
        self.assertIn("não use conhecimento externo", prompt_lower)
        self.assertIn("auditorias eliminam 95%", prompt_lower)
        self.assertIn("surge exclusivamente depois", prompt_lower)
        self.assertIn("elimina todos os riscos", prompt_lower)

    def test_prompt_preserva_os_casos_de_regressao(self):
        prompt = prompts.prompt_avaliacao(
            "[Slide 1]\nA governança define políticas, processos e controles.",
            "A governança organiza regras, procedimentos e mecanismos de acompanhamento.",
        )
        self.assertNotIn("info_nao_sustentada: toda frase ausente", prompt)
        self.assertIn('"info_nao_sustentada"', prompt)
        self.assertIn("não duplique o mesmo apontamento", re.sub(r"\s+", " ", prompt.lower()))

    def test_prompt_separa_principais_e_complementares(self):
        prompt = prompts.prompt_avaliacao(
            "[Slide 1]\nTransparência como princípio de governança.\n"
            "Utilizamos IA para organizar as ideias.",
            "Transparência orienta a governança.",
        )
        self.assertIn("topicos_complementares", prompt)
        self.assertIn("conceitos e definições", prompt)
        self.assertIn("créditos de autoria", prompt)
        self.assertIn("uma página pode ter tópicos principais", prompt.lower())
        self.assertIn("ferramenta como conteúdo principal", prompt.lower())
        self.assertIn("priorizar contradições e lacunas principais", prompt.lower())
