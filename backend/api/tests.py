import re
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import fitz
import httpx
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from pydantic import BaseModel
from rest_framework.test import APIClient

from api.schemas import (
    FeedbackInternoResponse,
    FeedbackResponse,
    OrdemApresentacao,
    Topico,
    TopicoAvaliado,
    TopicoAvaliadoInterno,
    TopicosResponse,
)
from api.services import pdf
from api.services import gemini
from api.services.gemini import GeminiErro
from api.services import prompts
from api.services.referencia import criar_referencia
from api.views import _calcular_cobertura


class SaudeTests(SimpleTestCase):
    def test_saude_retorna_ok(self):
        resposta = self.client.get("/api/saude/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "ok")


class ApiValidacaoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            user=get_user_model().objects.create_user(
                username="validacao", email="validacao@example.com", password="Senha-forte-123"
            )
        )
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


class PDFTests(TestCase):
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
        self.client.force_authenticate(
            user=get_user_model().objects.create_user(
                username="pdf", email="pdf@example.com", password="Senha-forte-123"
            )
        )


class GeminiViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            user=get_user_model().objects.create_user(
                username="gemini", email="gemini@example.com", password="Senha-forte-123"
            )
        )
        self.paginas = [{"numero": 1, "texto": "Material de referência."}]
        referencia = criar_referencia(
            "pdf",
            self.paginas,
            [Topico(titulo="A", slide=1, resumo="Resumo A")],
        )
        self.referencia = referencia.model_dump()
        self.payload = {
            "paginas": self.paginas,
            "ensaio": "Este é um ensaio suficientemente longo para análise.",
            "modo": "pdf",
            "referencia": self.referencia,
        }

    @staticmethod
    def _feedback(topicos):
        return FeedbackInternoResponse(
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

    @staticmethod
    def _avaliado(id_, status="coberto"):
        return TopicoAvaliadoInterno(
            id=id_,
            status=status,
            trecho_material="",
            trecho_ensaio="",
            comentario="",
        )

    def test_avaliacao_calcula_cobertura_no_backend(self):
        resultado = self._feedback(
            [
                self._avaliado("principal-001", "coberto"),
            ]
        )
        with patch("api.views.gemini.gerar_estruturado", return_value=resultado):
            resposta = self.client.post("/api/avaliar/", self.payload, format="json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["cobertura_percentual"], 100)

    def test_preparacao_atribui_ids_e_preserva_referencia(self):
        resultado = TopicosResponse(
            topicos=[Topico(titulo="Principal", slide=1, resumo="P")],
            topicos_complementares=[
                Topico(titulo="Crédito", slide=1, resumo="C")
            ],
        )
        with patch("api.views.gemini.gerar_estruturado", return_value=resultado):
            resposta = self.client.post(
                "/api/topicos/",
                {"paginas": self.paginas, "modo": "pdf"},
                format="json",
            )
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual([item["id"] for item in corpo["topicos"]], ["principal-001"])
        self.assertEqual(
            [item["id"] for item in corpo["topicos_complementares"]],
            ["complementar-001"],
        )
        self.assertNotEqual(corpo["assinatura"], "")

    def test_referencia_adulterada_e_material_diferente_nao_chamam_gemini(self):
        adulterada = {**self.referencia, "material_hash": "adulterado"}
        for payload in (
            {**self.payload, "referencia": adulterada},
            {
                **self.payload,
                "paginas": [{"numero": 1, "texto": "Outro material."}],
            },
        ):
            with patch("api.views.gemini.gerar_estruturado") as gerar:
                resposta = self.client.post("/api/avaliar/", payload, format="json")
            self.assertEqual(resposta.status_code, 400)
            gerar.assert_not_called()

    def test_ids_desconhecidos_ausentes_e_duplicados_sao_rejeitados(self):
        cenarios = (
            [self._avaliado("desconhecido")],
            [],
            [self._avaliado("principal-001"), self._avaliado("principal-001")],
        )
        for itens in cenarios:
            with patch(
                "api.views.gemini.gerar_estruturado",
                return_value=self._feedback(itens),
            ):
                resposta = self.client.post("/api/avaliar/", self.payload, format="json")
            self.assertEqual(resposta.status_code, 502)

    def test_retorno_em_outra_ordem_e_recomposto_na_ordem_da_referencia(self):
        paginas = [{"numero": 1, "texto": "Material de referência."}]
        referencia = criar_referencia(
            "pdf",
            paginas,
            [
                Topico(titulo="A", slide=1, resumo="A"),
                Topico(titulo="B", slide=1, resumo="B"),
            ],
        )
        payload = {
            **self.payload,
            "referencia": referencia.model_dump(),
        }
        resultado = self._feedback(
            [self._avaliado("principal-002"), self._avaliado("principal-001")]
        )
        with patch("api.views.gemini.gerar_estruturado", return_value=resultado):
            resposta = self.client.post("/api/avaliar/", payload, format="json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([item["id"] for item in resposta.json()["topicos"]], [
            "principal-001", "principal-002"
        ])

    def test_duas_avaliacoes_preservam_metadados_da_mesma_referencia(self):
        paginas = [
            {"numero": 1, "texto": "Conceito A."},
            {"numero": 2, "texto": "Conceito B e crédito."},
        ]
        referencia = criar_referencia(
            "pdf",
            paginas,
            [
                Topico(titulo="Conceito A", slide=1, resumo="A"),
                Topico(titulo="Conceito B", slide=2, resumo="B"),
            ],
            [Topico(titulo="Crédito", slide=2, resumo="C")],
        )
        payload = {
            "paginas": paginas,
            "ensaio": "Este é um ensaio suficientemente longo para análise.",
            "modo": "pdf",
            "referencia": referencia.model_dump(),
        }
        primeira = self._feedback(
            [
                self._avaliado("principal-001", "coberto").model_copy(
                    update={"trecho_ensaio": "Trecho um", "comentario": "Comentário um"}
                ),
                self._avaliado("principal-002", "parcial").model_copy(
                    update={"trecho_ensaio": "Trecho dois", "comentario": "Comentário dois"}
                ),
            ]
        ).model_copy(
            update={
                "topicos_complementares": [
                    self._avaliado("complementar-001", "omitido").model_copy(
                        update={"comentario": "Complementar um"}
                    )
                ]
            }
        )
        segunda = self._feedback(
            [
                self._avaliado("principal-002", "coberto").model_copy(
                    update={"trecho_ensaio": "Outro trecho dois", "comentario": "Outro comentário dois"}
                ),
                self._avaliado("principal-001", "omitido").model_copy(
                    update={"trecho_ensaio": "", "comentario": "Outro comentário um"}
                ),
            ]
        ).model_copy(
            update={
                "topicos_complementares": [
                    self._avaliado("complementar-001", "coberto").model_copy(
                        update={"trecho_ensaio": "Trecho complementar", "comentario": "Outro complementar"}
                    )
                ]
            }
        )

        with patch(
            "api.views.gemini.gerar_estruturado",
            side_effect=[primeira, segunda],
        ):
            primeira_resposta = self.client.post("/api/avaliar/", payload, format="json")
            segunda_resposta = self.client.post("/api/avaliar/", payload, format="json")

        self.assertEqual(primeira_resposta.status_code, 200)
        self.assertEqual(segunda_resposta.status_code, 200)
        primeira_json = primeira_resposta.json()
        segunda_json = segunda_resposta.json()

        for campo in ("id", "titulo", "categoria", "slide"):
            self.assertEqual(
                [item[campo] for item in primeira_json["topicos"]],
                [item[campo] for item in segunda_json["topicos"]],
            )
            self.assertEqual(
                [item[campo] for item in primeira_json["topicos_complementares"]],
                [item[campo] for item in segunda_json["topicos_complementares"]],
            )
        self.assertEqual(
            [item["id"] for item in primeira_json["topicos"]],
            ["principal-001", "principal-002"],
        )
        self.assertEqual(
            [item["id"] for item in primeira_json["topicos_complementares"]],
            ["complementar-001"],
        )
        self.assertEqual(len(primeira_json["topicos"]), len(segunda_json["topicos"]))
        self.assertEqual(
            len(primeira_json["topicos_complementares"]),
            len(segunda_json["topicos_complementares"]),
        )
        self.assertNotEqual(
            [item["status"] for item in primeira_json["topicos"]],
            [item["status"] for item in segunda_json["topicos"]],
        )
        self.assertNotEqual(
            [item["comentario"] for item in primeira_json["topicos"]],
            [item["comentario"] for item in segunda_json["topicos"]],
        )
        self.assertNotEqual(
            [item["trecho_ensaio"] for item in primeira_json["topicos"]],
            [item["trecho_ensaio"] for item in segunda_json["topicos"]],
        )

    def test_adulteracao_de_titulo_ou_categoria_rejeitada_antes_do_gemini(self):
        for campo, valor in (
            ("titulo", "Título adulterado"),
            ("categoria", "complementar"),
        ):
            adulterada = referencia = self.referencia.copy()
            adulterada["topicos"] = [dict(item) for item in referencia["topicos"]]
            adulterada["topicos"][0][campo] = valor
            with patch("api.views.gemini.gerar_estruturado") as gerar:
                resposta = self.client.post(
                    "/api/avaliar/",
                    {**self.payload, "referencia": adulterada},
                    format="json",
                )
            self.assertEqual(resposta.status_code, 400)
            gerar.assert_not_called()

    def test_cobertura_usa_apenas_topicos_principais(self):
        principais = [
            TopicoAvaliado(
                titulo=f"P{i}", slide=1, status="coberto",
                trecho_material="", trecho_ensaio="", comentario="",
            )
            for i in range(10)
        ]
        complementares = [
            TopicoAvaliado(
                titulo="Crédito", slide=1, status="omitido",
                trecho_material="", trecho_ensaio="", comentario=""
            )
        ]
        resultado = FeedbackResponse(
            resumo_geral="Resumo", cobertura_percentual=99, topicos=principais,
            erros_conteudo=[], info_nao_sustentada=[],
            ordem_apresentacao=OrdemApresentacao(avaliacao="a", sugestao="b"),
            perguntas_banca=[], proximo_passo="c",
        ).model_copy(
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
                FeedbackResponse(
                    resumo_geral="Resumo", cobertura_percentual=99, topicos=parcial,
                    erros_conteudo=[], info_nao_sustentada=[],
                    ordem_apresentacao=OrdemApresentacao(avaliacao="a", sugestao="b"),
                    perguntas_banca=[], proximo_passo="c",
                ).model_copy(
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
        self.assertEqual(_calcular_cobertura(FeedbackResponse(
            resumo_geral="Resumo", cobertura_percentual=99, topicos=omitido,
            erros_conteudo=[], info_nao_sustentada=[],
            ordem_apresentacao=OrdemApresentacao(avaliacao="a", sugestao="b"),
            perguntas_banca=[], proximo_passo="c",
        )), 90)
        self.assertEqual(_calcular_cobertura(FeedbackResponse(
            resumo_geral="Resumo", cobertura_percentual=99, topicos=[],
            erros_conteudo=[], info_nao_sustentada=[],
            ordem_apresentacao=OrdemApresentacao(avaliacao="a", sugestao="b"),
            perguntas_banca=[], proximo_passo="c",
        )), 0)

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



class GeminiServiceTests(SimpleTestCase):
    def setUp(self):
        gemini._reset_credential_pool()

    def test_pool_deduplica_e_faz_round_robin(self):
        pool = gemini.CredentialPool("ficticia-a, ficticia-b, ficticia-a")
        selecionadas = [pool.reserve().index for _ in range(4)]
        self.assertEqual(selecionadas, [0, 1, 0, 1])

    def test_pool_propaga_cooldown_de_quota_no_projeto_conhecido(self):
        pool = gemini.CredentialPool(
            "ficticia-a, ficticia-b, ficticia-c", "projeto-a, projeto-a, projeto-b"
        )
        primeira = pool.reserve()
        pool.report(primeira, gemini.genai_errors.ServerError(
            429, {"error": {"message": "limite temporário"}}
        ))
        self.assertEqual(pool.reserve().project, "projeto-b")
        self.assertEqual(
            [item["cooldown_until"] > 0 for item in pool.snapshot()],
            [True, True, False],
        )

    def test_pool_concorrente_nao_reserva_a_mesma_posicao_em_paralelo(self):
        pool = gemini.CredentialPool("ficticia-a, ficticia-b")
        with ThreadPoolExecutor(max_workers=2) as executor:
            indices = list(executor.map(lambda _: pool.reserve().index, range(2)))
        self.assertEqual(sorted(indices), [0, 1])

    @override_settings(
        GEMINI_API_KEYS="ficticia-a, ficticia-b",
        GEMINI_MAX_TENTATIVAS=3,
        GEMINI_ORCAMENTO_MS=1,
    )
    def test_orcamento_global_impede_tentativas_adicionais(self):
        with patch(
            "api.services.gemini.time.monotonic",
            side_effect=[0.0, 0.002, 0.002, 0.002],
        ):
            with patch("api.services.gemini._chamar_gemini") as chamar:
                with self.assertRaises(GeminiErro) as contexto:
                    gemini.gerar_estruturado("prompt privado", FeedbackResponse)
        self.assertEqual(contexto.exception.status, 504)
        chamar.assert_not_called()

    def test_cliente_sdk_usa_uma_tentativa_de_rede(self):
        class Resultado(BaseModel):
            valor: int

        cliente = type("ClienteFalso", (), {})()
        cliente.models = type("ModelosFalsos", (), {})()
        cliente.models.generate_content = lambda **kwargs: type(
            "RespostaFalsa", (), {"text": '{"valor": 7}'}
        )()
        cliente.close = lambda: None
        with override_settings(GEMINI_API_KEYS="chave-de-teste", GEMINI_TIMEOUT_MS=60000):
            with patch("api.services.gemini.genai.Client", return_value=cliente) as factory:
                resultado = gemini._chamar_gemini("prompt privado", Resultado)

        opcoes = factory.call_args.kwargs["http_options"]
        self.assertEqual(opcoes.timeout, 60000)
        self.assertEqual(opcoes.retry_options.attempts, 1)
        self.assertEqual(resultado.valor, 7)

    def test_resposta_valida_nao_e_repetida(self):
        resultado_esperado = FeedbackResponse(
            resumo_geral="Resumo",
            cobertura_percentual=0,
            topicos=[],
            erros_conteudo=[],
            info_nao_sustentada=[],
            ordem_apresentacao={"avaliacao": "ok", "sugestao": "ok"},
            perguntas_banca=[],
            proximo_passo="ok",
        )
        with patch(
            "api.services.gemini._chamar_gemini",
            return_value=resultado_esperado,
        ) as chamar:
            resultado = gemini.gerar_estruturado(
                "prompt privado", FeedbackResponse
            )

        self.assertEqual(resultado, resultado_esperado)
        chamar.assert_called_once()

    @override_settings(GEMINI_API_KEYS="chave-de-teste", GEMINI_MAX_TENTATIVAS=2)
    def test_timeout_httpx_retorna_504_sem_repetir(self):
        timeout = httpx.ReadTimeout("tempo excedido")
        with patch("api.services.gemini._chamar_gemini", side_effect=timeout) as chamar:
            with self.assertRaises(GeminiErro) as contexto:
                gemini.gerar_estruturado("prompt privado", FeedbackResponse)

        self.assertEqual(contexto.exception.status, 504)
        self.assertEqual(contexto.exception.categoria, "timeout")
        self.assertIn("permanece nesta tela", contexto.exception.detail)
        chamar.assert_called_once()

    @override_settings(GEMINI_API_KEYS="chave-de-teste", GEMINI_MAX_TENTATIVAS=2)
    def test_server_error_503_repete_apenas_dentro_do_limite(self):
        erro = gemini.genai_errors.ServerError(503, {"error": {"message": "indisponível"}})
        with patch("api.services.gemini._chamar_gemini", side_effect=erro) as chamar:
            with patch("api.services.gemini.time.sleep"):
                with self.assertRaises(GeminiErro) as contexto:
                    gemini.gerar_estruturado("prompt privado", FeedbackResponse)

        self.assertEqual(contexto.exception.status, 503)
        self.assertEqual(contexto.exception.categoria, "indisponibilidade")
        self.assertEqual(chamar.call_count, 2)

    @override_settings(GEMINI_API_KEYS="chave-de-teste", GEMINI_MAX_TENTATIVAS=2)
    def test_server_error_504_e_limite_nao_repetem_a_chamada(self):
        for codigo, categoria in ((504, "timeout"), (429, "limite")):
            erro = gemini.genai_errors.ServerError(
                codigo, {"error": {"message": "falha controlada"}}
            )
            with self.subTest(codigo=codigo):
                with patch("api.services.gemini._chamar_gemini", side_effect=erro) as chamar:
                    with self.assertRaises(GeminiErro) as contexto:
                        gemini.gerar_estruturado("prompt privado", FeedbackResponse)
                self.assertEqual(contexto.exception.status, codigo)
                self.assertEqual(contexto.exception.categoria, categoria)
                chamar.assert_called_once()

    @override_settings(GEMINI_API_KEYS="chave-de-teste", GEMINI_MAX_TENTATIVAS=2)
    def test_falha_de_autenticacao_nao_e_tratada_como_limite(self):
        erro = gemini.genai_errors.ClientError(
            401, {"error": {"message": "credencial inválida"}}
        )
        with patch("api.services.gemini._chamar_gemini", side_effect=erro) as chamar:
            with self.assertRaises(GeminiErro) as contexto:
                gemini.gerar_estruturado("prompt privado", FeedbackResponse)

        self.assertEqual(contexto.exception.status, 503)
        self.assertEqual(contexto.exception.categoria, "autenticacao")
        chamar.assert_called_once()


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

    def test_prompt_separa_papeis_de_autoria_e_referencias(self):
        prompt = prompts.prompt_topicos(
            "[Slide 1]\nAutoria: Ana Lima e Bruno Costa.\n"
            "[Slide 2]\nReferência: Maria Silva (2020)."
        )
        prompt_lower = re.sub(r"\s+", " ", prompt.lower())
        self.assertIn("pessoas_material", prompt)
        self.assertIn("autoria do trabalho/material", prompt_lower)
        self.assertIn("autor de obra citada", prompt_lower)
        self.assertIn("não trate autores de referências como integrantes", prompt_lower)
        self.assertIn("não entram em", prompt_lower)

    def test_prompt_perguntas_respeita_contexto_selecionado(self):
        prompt = prompts.prompt_perguntas(
            "[Slide 1]\nA apresentação explica o produto.",
            3,
            "profissional",
        )
        self.assertIn("perguntas da audiência", prompt.lower())
        self.assertIn("apresentação profissional", prompt.lower())
        self.assertNotIn("investidores", prompt.lower().split("não presuma", 1)[0])

    def test_referencia_antiga_usa_contexto_geral_por_padrao(self):
        referencia = criar_referencia(
            "pdf",
            [{"numero": 1, "texto": "Conteúdo"}],
            [Topico(titulo="Conteúdo", slide=1, resumo="Resumo")],
        )
        self.assertEqual(referencia.contexto, "geral")
        self.assertEqual(referencia.pessoas_material, [])

    def test_prompt_estavel_orienta_contradicao_e_correcao_acionavel(self):
        referencia = criar_referencia(
            "pdf",
            [{"numero": 6, "texto": "O viés pode surgir na coleta e no treinamento."}],
            [Topico(titulo="Origem do viés", slide=6, resumo="Possíveis origens")],
        )
        prompt = prompts.prompt_avaliacao_referencia(
            "[Slide 6]\nO viés pode surgir na coleta e no treinamento.",
            "Pode surgir na coleta. Surge exclusivamente depois da produção.",
            referencia,
        )
        prompt_lower = re.sub(r"\s+", " ", prompt.lower())
        self.assertIn("reconheça a parte correta", prompt_lower)
        self.assertIn("não duplique automaticamente", prompt_lower)
        self.assertIn('status "parcial"', prompt_lower)
        self.assertIn("trecho exato do ensaio", prompt_lower)
        self.assertIn("corrigir o trecho do ensaio referente à página n", prompt_lower)
        self.assertIn("nunca recomendar uma nova afirmação absoluta", prompt_lower)
        self.assertIn("não se limita à fase de produção", prompt_lower)
