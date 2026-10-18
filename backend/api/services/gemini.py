"""Integração isolada com o SDK do Gemini."""

import logging
import re
import time
from typing import TypeVar

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiErro(Exception):
    """Erro de integração convertido em resposta segura para a API."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


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


def _registrar_falha(exc: Exception, inicio: float) -> None:
    logger.warning(
        "Falha na integração Gemini: operacao=%s excecao=%s codigo_provedor=%s duracao_ms=%d",
        "generate_content",
        type(exc).__name__,
        _codigo_seguro(exc),
        round((time.monotonic() - inicio) * 1000),
    )


def _eh_transitorio(exc: Exception) -> bool:
    codigo = _codigo_erro(exc)
    return codigo in {408, 429, 500, 502, 503, 504} or "RESOURCE_EXHAUSTED" in str(exc)


def _espera_retry(exc: Exception) -> float:
    valor = getattr(exc, "retry_delay", None) or getattr(exc, "retry_after", None)
    try:
        segundos = float(getattr(valor, "seconds", valor))
    except (TypeError, ValueError):
        segundos = 1.0
    return min(max(segundos, 0.1), 2.0)


def _chamar_gemini(prompt: str, schema: type[T]) -> T:
    client = genai.Client(
        api_key=_chave_configurada(),
        http_options=types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS),
    )
    try:
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
            raise GeminiErro(502, "O serviço de análise retornou uma resposta vazia.")
        try:
            return schema.model_validate_json(texto)
        except (ValidationError, ValueError) as exc:
            raise GeminiErro(
                502, "O serviço de análise retornou dados em formato inválido."
            ) from exc
    finally:
        client.close()


def gerar_estruturado(prompt: str, schema: type[T]) -> T:
    """Executa poucas tentativas para falhas transitórias, sem contornar cotas."""
    tentativas = min(max(settings.GEMINI_MAX_TENTATIVAS, 1), 3)
    for tentativa in range(tentativas):
        inicio = time.monotonic()
        try:
            return _chamar_gemini(prompt, schema)
        except GeminiErro as exc:
            _registrar_falha(exc, inicio)
            raise
        except (genai_errors.ClientError, genai_errors.ServerError, TimeoutError) as exc:
            _registrar_falha(exc, inicio)
            if not _eh_transitorio(exc) or tentativa == tentativas - 1:
                raise GeminiErro(
                    503, "O serviço de análise está temporariamente indisponível."
                ) from exc
            time.sleep(_espera_retry(exc))
        except OSError as exc:
            _registrar_falha(exc, inicio)
            if tentativa == tentativas - 1:
                raise GeminiErro(
                    503, "O serviço de análise está temporariamente indisponível."
                ) from exc
            time.sleep(0.5)
    raise GeminiErro(503, "O serviço de análise está temporariamente indisponível.")
