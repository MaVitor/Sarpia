from django.conf import settings
from rest_framework import status as drf_status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.schemas import FeedbackResponse, PaginaTexto, PerguntasResponse, TopicosResponse
from api.serializers import (
    AvaliacaoRequestSerializer,
    PerguntasRequestSerializer,
    TopicosRequestSerializer,
)
from api.services import gemini
from api.services import pdf as pdf_service
from api.services import prompts


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
        paginas = [PaginaTexto(**p) for p in serializer.validated_data["paginas"]]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_topicos(material), TopicosResponse
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc)
        return Response(resultado.model_dump())


class AvaliarView(APIView):
    def post(self, request):
        serializer = AvaliacaoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas = [PaginaTexto(**p) for p in serializer.validated_data["paginas"]]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_avaliacao(material, serializer.validated_data["ensaio"]),
                FeedbackResponse,
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc)
        resultado = resultado.model_copy(
            update={"cobertura_percentual": _calcular_cobertura(resultado)}
        )
        return Response(resultado.model_dump())


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
