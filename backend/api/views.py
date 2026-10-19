from django.conf import settings
from rest_framework import status as drf_status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.schemas import (
    FeedbackInternoResponse,
    FeedbackResponse,
    PaginaTexto,
    PerguntasResponse,
    TopicoAvaliado,
    TopicoAvaliadoInterno,
    TopicoReferencia,
    TopicosResponse,
)
from api.serializers import (
    AvaliacaoRequestSerializer,
    PerguntasRequestSerializer,
    TopicosRequestSerializer,
)
from api.services import gemini
from api.services import pdf as pdf_service
from api.services import prompts
from api.services import referencia as referencia_service


def _erro_gemini(exc: gemini.GeminiErro) -> Response:
    return Response({"detail": exc.detail}, status=exc.status)


def _calcular_cobertura(resultado: FeedbackResponse) -> int:
    total = len(resultado.topicos)
    if not total:
        return 0
    cobertos = sum(
        topico.status in {"coberto", "parcial"} for topico in resultado.topicos
    )
    return round(cobertos * 100 / total)


def _compor_topico(
    referencia: TopicoReferencia, avaliado: TopicoAvaliadoInterno
) -> TopicoAvaliado:
    return TopicoAvaliado(
        id=referencia.id,
        titulo=referencia.titulo,
        categoria=referencia.categoria,
        slide=referencia.slide,
        status=avaliado.status,
        trecho_material=avaliado.trecho_material,
        trecho_ensaio=avaliado.trecho_ensaio,
        comentario=avaliado.comentario,
    )


class SaudeView(APIView):
    def get(self, request):
        return Response({"status": "ok", "servico": "sarpia-api", "versao": "0.1.0"})


class MateriaisView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if arquivo is None or not arquivo.name.lower().endswith(".pdf"):
            return Response(
                {"detail": "Envie um arquivo PDF."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        limite_bytes = settings.MAX_PDF_MB * 1024 * 1024
        if not arquivo.size:
            return Response({"detail": "O arquivo PDF está vazio."}, status=400)
        if arquivo.size > limite_bytes:
            return Response(
                {"detail": f"PDF maior que {settings.MAX_PDF_MB} MB."},
                status=drf_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        try:
            paginas, aviso = pdf_service.extrair_texto(
                arquivo.read(), max_paginas=settings.MAX_PAGINAS
            )
        except pdf_service.PDFExtracaoErro as exc:
            return Response(
                {"detail": str(exc)},
                status=drf_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not any(p.texto.strip() for p in paginas):
            return Response(
                {
                    "detail": (
                        "Não foi possível extrair texto. "
                        "PDFs escaneados ainda não são suportados."
                    )
                },
                status=drf_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(
            {
                "total_paginas": len(paginas),
                "paginas": [p.model_dump() for p in paginas],
                "aviso": aviso,
            }
        )


class TopicosView(APIView):
    def post(self, request):
        serializer = TopicosRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas_dict = serializer.validated_data["paginas"]
        paginas = [PaginaTexto(**p) for p in paginas_dict]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_topicos(material), TopicosResponse
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc)
        try:
            referencia = referencia_service.criar_referencia(
                serializer.validated_data["modo"],
                paginas_dict,
                resultado.topicos,
                getattr(resultado, "topicos_complementares", []),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=502)
        return Response(referencia.model_dump())


class AvaliarView(APIView):
    def post(self, request):
        serializer = AvaliacaoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas_dict = serializer.validated_data["paginas"]
        try:
            referencia = referencia_service.validar_referencia(
                serializer.validated_data["referencia"],
                serializer.validated_data["modo"],
                paginas_dict,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        paginas = [PaginaTexto(**p) for p in paginas_dict]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_avaliacao_referencia(
                    material, serializer.validated_data["ensaio"], referencia
                ),
                FeedbackInternoResponse,
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc)
        esperado_principal = {topico.id for topico in referencia.topicos}
        esperado_complementar = {
            topico.id for topico in referencia.topicos_complementares
        }
        ids_principais = [topico.id for topico in resultado.topicos]
        ids_complementares = [topico.id for topico in resultado.topicos_complementares]
        if (
            len(ids_principais) != len(set(ids_principais))
            or len(ids_complementares) != len(set(ids_complementares))
            or set(ids_principais) != esperado_principal
            or set(ids_complementares) != esperado_complementar
        ):
            return Response(
                {"detail": "A resposta da análise não corresponde à referência de tópicos."},
                status=502,
            )
        principais_por_id = {topico.id: topico for topico in referencia.topicos}
        complementares_por_id = {
            topico.id: topico for topico in referencia.topicos_complementares
        }
        avaliados_principais = {item.id: item for item in resultado.topicos}
        avaliados_complementares = {
            item.id: item for item in resultado.topicos_complementares
        }
        principais = [
            _compor_topico(principais_por_id[topico.id], avaliados_principais[topico.id])
            for topico in referencia.topicos
        ]
        complementares = [
            _compor_topico(
                complementares_por_id[topico.id], avaliados_complementares[topico.id]
            )
            for topico in referencia.topicos_complementares
        ]
        publico = FeedbackResponse(
            resumo_geral=resultado.resumo_geral,
            cobertura_percentual=0,
            topicos=principais,
            topicos_complementares=complementares,
            erros_conteudo=resultado.erros_conteudo,
            info_nao_sustentada=resultado.info_nao_sustentada,
            ordem_apresentacao=resultado.ordem_apresentacao,
            perguntas_banca=resultado.perguntas_banca,
            proximo_passo=resultado.proximo_passo,
        )
        return Response(
            publico.model_copy(
                update={"cobertura_percentual": _calcular_cobertura(publico)}
            ).model_dump()
        )


class PerguntasView(APIView):
    def post(self, request):
        serializer = PerguntasRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas = [PaginaTexto(**p) for p in serializer.validated_data["paginas"]]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_perguntas(
                    material, serializer.validated_data["quantidade"]
                ),
                PerguntasResponse,
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc)
        return Response(resultado.model_dump())
