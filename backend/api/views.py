import uuid
import re

from django.conf import settings
from django.contrib.auth import logout
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework import status as drf_status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from allauth.headless.account import views as headless_account_views
from allauth.headless.constants import Client

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
from api.models import Attempt, Presentation


def _headless_view(view_class):
    return view_class.as_api_view(client=Client.BROWSER)


def _usuario_publico(user):
    if not user.is_authenticated:
        return None
    return {
        "email": user.email,
        "nome": user.get_full_name() or user.first_name or user.email,
    }


class AuthCsrfView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


class AuthSessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "autenticado": request.user.is_authenticated,
                "usuario": _usuario_publico(request.user),
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return _headless_view(headless_account_views.LoginView)(
            request._request
        )


@method_decorator(csrf_protect, name="dispatch")
class AuthSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = _headless_view(headless_account_views.SignupView)(
            request._request
        )
        user = request._request.user
        if user.is_authenticated:
            nome = str(request.data.get("nome", "")).strip()
            if nome:
                user.first_name = nome[:150]
                user.save(update_fields=["first_name"])
        return response


@method_decorator(csrf_protect, name="dispatch")
class AuthLogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request._request)
        return Response({"autenticado": False, "usuario": None})


def _apresentacao_resumo(apresentacao: Presentation) -> dict:
    return {
        "id": str(apresentacao.id),
        "titulo": apresentacao.title,
        "modo": apresentacao.mode,
        "contexto": apresentacao.context,
        "referencia_versao": apresentacao.reference_version,
        "criada_em": apresentacao.created_at,
        "atualizada_em": apresentacao.updated_at,
        "quantidade_tentativas": apresentacao.attempts.count(),
    }


def _tentativa_publica(tentativa: Attempt) -> dict:
    return {
        "id": str(tentativa.id),
        "ensaio": tentativa.essay,
        "feedback": tentativa.feedback,
        "referencia_versao": tentativa.reference_version,
        "modelo": tentativa.model_name or None,
        "contrato": tentativa.contract_version or None,
        "criada_em": tentativa.created_at,
    }


class ApresentacoesView(APIView):
    def get(self, request):
        apresentacoes = Presentation.objects.filter(owner=request.user)
        try:
            page_number = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            page_number = 1
        page_size = 20
        inicio = (page_number - 1) * page_size
        itens = list(apresentacoes[inicio : inicio + page_size + 1])
        tem_proxima = len(itens) > page_size
        return Response(
            {
                "resultados": [_apresentacao_resumo(item) for item in itens[:page_size]],
                "pagina": page_number,
                "tem_proxima": tem_proxima,
            }
        )


class ApresentacaoDetalheView(APIView):
    def get(self, request, presentation_id):
        apresentacao = get_object_or_404(
            Presentation.objects.filter(owner=request.user), pk=presentation_id
        )
        return Response(
            {
                **_apresentacao_resumo(apresentacao),
                "paginas": apresentacao.pages,
                "referencia": apresentacao.reference,
                "tentativas": [
                    _tentativa_publica(tentativa)
                    for tentativa in apresentacao.attempts.all()
                ],
            }
        )

    def delete(self, request, presentation_id):
        apresentacao = get_object_or_404(
            Presentation.objects.filter(owner=request.user), pk=presentation_id
        )
        apresentacao.delete()
        return Response(status=drf_status.HTTP_204_NO_CONTENT)


class TentativaDetalheView(APIView):
    def get(self, request, presentation_id, attempt_id):
        tentativa = get_object_or_404(
            Attempt.objects.filter(
                presentation__owner=request.user,
                presentation_id=presentation_id,
            ),
            pk=attempt_id,
        )
        return Response(_tentativa_publica(tentativa))

    def delete(self, request, presentation_id, attempt_id):
        tentativa = get_object_or_404(
            Attempt.objects.filter(
                presentation__owner=request.user,
                presentation_id=presentation_id,
            ),
            pk=attempt_id,
        )
        tentativa.delete()
        return Response(status=drf_status.HTTP_204_NO_CONTENT)


def _correlacao(request) -> str:
    valor = request.headers.get("X-Request-ID", "").strip()
    if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", valor):
        return valor
    return uuid.uuid4().hex


def _erro_gemini(exc: gemini.GeminiErro, correlacao: str) -> Response:
    response = Response(
        {"detail": exc.detail, "correlacao": correlacao},
        status=exc.status,
    )
    response["X-Request-ID"] = correlacao
    return response


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
    permission_classes = [AllowAny]

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
        correlacao = _correlacao(request)
        serializer = TopicosRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas_dict = serializer.validated_data["paginas"]
        paginas = [PaginaTexto(**p) for p in paginas_dict]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_topicos(material), TopicosResponse, correlacao
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc, correlacao)
        try:
            referencia = referencia_service.criar_referencia(
                serializer.validated_data["modo"],
                paginas_dict,
                resultado.topicos,
                getattr(resultado, "topicos_complementares", []),
                getattr(resultado, "pessoas_material", []),
                serializer.validated_data["contexto"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=502)
        apresentacao = Presentation.objects.create(
            owner=request.user,
            title=serializer.validated_data["titulo"],
            mode=serializer.validated_data["modo"],
            context=serializer.validated_data["contexto"],
            pages=paginas_dict,
            reference=referencia.model_dump(),
            reference_version=referencia.versao_contrato,
        )
        return Response(
            {**referencia.model_dump(), "presentation_id": str(apresentacao.id)}
        )


class AvaliarView(APIView):
    def post(self, request):
        correlacao = _correlacao(request)
        serializer = AvaliacaoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        apresentacao = None
        if serializer.validated_data.get("presentation_id"):
            apresentacao = get_object_or_404(
                Presentation.objects.filter(owner=request.user),
                pk=serializer.validated_data["presentation_id"],
            )
            paginas_dict = apresentacao.pages
            modo = apresentacao.mode
            contexto = apresentacao.context
            referencia_dados = apresentacao.reference
        else:
            paginas_dict = serializer.validated_data["paginas"]
            modo = serializer.validated_data["modo"]
            referencia_dados = serializer.validated_data["referencia"]
            contexto = serializer.validated_data["contexto"]
        idempotency_key = None
        if apresentacao is not None:
            idempotency_key = (
                serializer.validated_data.get("idempotency_key")
                or request.headers.get("X-Idempotency-Key")
            )
            if not idempotency_key:
                return Response(
                    {"detail": "Informe uma chave de idempotência para salvar a tentativa."},
                    status=400,
                )
            existente = Attempt.objects.filter(
                presentation=apresentacao, idempotency_key=idempotency_key
            ).first()
            if existente:
                return Response(existente.feedback)
        try:
            referencia = referencia_service.validar_referencia(
                referencia_dados,
                modo,
                paginas_dict,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        if referencia.contexto != contexto:
            return Response(
                {"detail": "O contexto não corresponde à referência do material."},
                status=400,
            )
        paginas = [PaginaTexto(**p) for p in paginas_dict]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_avaliacao_referencia(
                    material, serializer.validated_data["ensaio"], referencia
                ),
                FeedbackInternoResponse,
                correlacao,
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc, correlacao)
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
            pessoas_material=referencia.pessoas_material,
        )
        feedback = publico.model_copy(
            update={"cobertura_percentual": _calcular_cobertura(publico)}
        )
        feedback_data = feedback.model_dump()
        if apresentacao is not None:
            try:
                with transaction.atomic():
                    tentativa = Attempt.objects.create(
                        presentation=apresentacao,
                        essay=serializer.validated_data["ensaio"],
                        feedback=feedback_data,
                        reference_version=apresentacao.reference_version,
                        contract_version=referencia.versao_contrato,
                        model_name=getattr(settings, "GEMINI_MODEL", ""),
                        idempotency_key=idempotency_key,
                    )
            except IntegrityError:
                tentativa = Attempt.objects.get(
                    presentation=apresentacao, idempotency_key=idempotency_key
                )
            apresentacao.save(update_fields=["updated_at"])
        return Response(feedback_data)


class PerguntasView(APIView):
    def post(self, request):
        correlacao = _correlacao(request)
        serializer = PerguntasRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paginas = [PaginaTexto(**p) for p in serializer.validated_data["paginas"]]
        material = prompts.formatar_material(paginas)
        try:
            resultado = gemini.gerar_estruturado(
                prompts.prompt_perguntas(
                    material,
                    serializer.validated_data["quantidade"],
                    serializer.validated_data["contexto"],
                ),
                PerguntasResponse,
                correlacao,
            )
        except gemini.GeminiErro as exc:
            return _erro_gemini(exc, correlacao)
        return Response(resultado.model_dump())
