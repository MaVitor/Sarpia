"""Integração isolada com o SDK do Gemini."""

import logging
import re
import time
from typing import TypeVar

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiErro(Exception):
    """Erro de integração convertido em resposta segura para a API."""

    def __init__(self, status: int, detail: str, categoria: str = "indisponibilidade") -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.categoria = categoria


def _chave_configurada() -> str:
    keys = [key.strip() for key in settings.GEMINI_API_KEYS.split(",") if key.strip()]
    if not keys:
        raise GeminiErro(503, "O serviço de análise não está configurado.")
    return keys[0]


def _codigo_erro(exc: Exception) -> int | str | None:
    return getattr(exc, "code", None) or getattr(exc, "status_code", None)


def _codigo_seguro(exc: Exception) -> int | str | None:
    codigo = _codigo_erro(exc)
    if isinstance(codigo, int):
        return codigo
    if isinstance(codigo, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", codigo):
        return codigo
    return None


def _registrar_falha(
    exc: Exception,
    inicio: float,
    categoria: str,
    tentativa: str,
    correlacao: str | None,
) -> None:
    logger.warning(
        "Falha na integração Gemini: correlacao=%s modelo=%s operacao=%s tentativa=%s categoria=%s excecao=%s codigo_provedor=%s duracao_ms=%d",
        correlacao or "-",
        settings.GEMINI_MODEL,
        "generate_content",
        tentativa,
        categoria,
        type(exc).__name__,
        _codigo_seguro(exc),
        round((time.monotonic() - inicio) * 1000),
    )


def _eh_transitorio(exc: Exception) -> bool:
    codigo = _codigo_erro(exc)
    return codigo == 503


def _espera_retry(exc: Exception) -> float:
    valor = getattr(exc, "retry_delay", None) or getattr(exc, "retry_after", None)
    try:
        segundos = float(getattr(valor, "seconds", valor))
    except (TypeError, ValueError):
        segundos = 1.0
    return min(max(segundos, 0.1), 2.0)


def _chamar_gemini(prompt: str, schema: type[T]) -> T:
    client = None
    try:
        client = genai.Client(
            api_key=_chave_configurada(),
            http_options=types.HttpOptions(
                timeout=settings.GEMINI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        resposta = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        texto = getattr(resposta, "text", None)
        if not texto or not texto.strip():
            raise GeminiErro(
                502,
                "O serviço de análise retornou uma resposta vazia.",
                "resposta_invalida",
            )
        try:
            return schema.model_validate_json(texto)
        except (ValidationError, ValueError) as exc:
            raise GeminiErro(
                502,
                "O serviço de análise retornou dados em formato inválido.",
                "resposta_invalida",
            ) from exc
    finally:
        if client is not None:
            client.close()


def _converter_falha(exc: Exception) -> GeminiErro:
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return GeminiErro(
            504,
            "O serviço de IA demorou além do esperado. O material permanece nesta tela; "
            "tente novamente em alguns instantes.",
            "timeout",
        )

    codigo = _codigo_erro(exc)
    if codigo in {401, 403}:
        return GeminiErro(
            503,
            "O serviço de análise não está autorizado ou configurado corretamente.",
            "autenticacao",
        )
    if codigo == 429 or "RESOURCE_EXHAUSTED" in str(exc):
        return GeminiErro(
            429,
            "O serviço de análise atingiu o limite de uso. Tente novamente mais tarde.",
            "limite",
        )
    if codigo == 400:
        return GeminiErro(
            502,
            "O serviço de análise rejeitou a solicitação.",
            "requisicao_invalida",
        )
    if codigo == 504:
        return GeminiErro(
            504,
            "O serviço de IA demorou além do esperado. O material permanece nesta tela; "
            "tente novamente em alguns instantes.",
            "timeout",
        )
    return GeminiErro(
        503,
        "O serviço de análise está temporariamente indisponível.",
        "indisponibilidade",
    )


def gerar_estruturado(
    prompt: str, schema: type[T], correlacao: str | None = None
) -> T:
    """Executa poucas tentativas para falhas transitórias, sem contornar cotas."""
    tentativas = min(max(settings.GEMINI_MAX_TENTATIVAS, 1), 3)
    for tentativa in range(tentativas):
        inicio = time.monotonic()
        tentativa_atual = f"{tentativa + 1}/{tentativas}"
        try:
            return _chamar_gemini(prompt, schema)
        except GeminiErro as exc:
            _registrar_falha(
                exc, inicio, exc.categoria, tentativa_atual, correlacao
            )
            raise
        except httpx.TimeoutException as exc:
            erro = _converter_falha(exc)
            _registrar_falha(
                exc, inicio, erro.categoria, tentativa_atual, correlacao
            )
            raise erro from exc
        except (genai_errors.ClientError, genai_errors.ServerError, TimeoutError) as exc:
            erro = _converter_falha(exc)
            _registrar_falha(
                exc, inicio, erro.categoria, tentativa_atual, correlacao
            )
            if not _eh_transitorio(exc) or tentativa == tentativas - 1:
                raise erro from exc
            time.sleep(_espera_retry(exc))
        except OSError as exc:
            erro = _converter_falha(exc)
            _registrar_falha(
                exc, inicio, erro.categoria, tentativa_atual, correlacao
            )
            if tentativa == tentativas - 1:
                raise erro from exc
            time.sleep(0.5)
    raise GeminiErro(503, "O serviço de análise está temporariamente indisponível.")
