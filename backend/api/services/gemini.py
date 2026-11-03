"""Integração isolada com o SDK do Gemini."""

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import TypeVar

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

_COOLDOWN_CAP_SECONDS = 300.0
_AUTH_FAILURE_COOLDOWN_SECONDS = 300.0
_TRANSIENT_FAILURE_COOLDOWN_SECONDS = 0.1


@dataclass
class _CredentialState:
    index: int
    key: str
    project: str | None
    cooldown_until: float = 0.0
    failures: int = 0
    disabled: bool = False


class CredentialPool:
    """Pool efêmero e process-local de credenciais, sem persistir segredos."""

    def __init__(self, raw_keys: str, raw_projects: str = "") -> None:
        keys = list(dict.fromkeys(key.strip() for key in raw_keys.split(",") if key.strip()))
        projects = [item.strip() or None for item in raw_projects.split(",")]
        self._states = [
            _CredentialState(
                index=index,
                key=key,
                project=projects[index] if index < len(projects) else None,
            )
            for index, key in enumerate(keys)
        ]
        self._cursor = 0
        self._lock = threading.Lock()

    def reserve(self, agora: float | None = None) -> _CredentialState:
        agora = time.monotonic() if agora is None else agora
        with self._lock:
            if not self._states:
                raise GeminiErro(503, "O serviço de análise não está configurado.")
            total = len(self._states)
            for deslocamento in range(total):
                indice = (self._cursor + deslocamento) % total
                estado = self._states[indice]
                if not estado.disabled and estado.cooldown_until <= agora:
                    self._cursor = (indice + 1) % total
                    return estado
        raise GeminiErro(
            503,
            "Nenhuma credencial de análise está disponível no momento. Tente novamente mais tarde.",
            "indisponibilidade",
        )

    def report(self, estado: _CredentialState, exc: Exception) -> None:
        codigo = _codigo_erro(exc)
        agora = time.monotonic()
        with self._lock:
            estado.failures += 1
            if codigo in {401, 403}:
                estado.cooldown_until = agora + _AUTH_FAILURE_COOLDOWN_SECONDS
                if codigo == 401:
                    estado.disabled = True
            elif codigo == 429:
                espera = _espera_retry(exc)
                fim = agora + espera
                if estado.project:
                    for candidato in self._states:
                        if candidato.project == estado.project:
                            candidato.cooldown_until = max(candidato.cooldown_until, fim)
                else:
                    estado.cooldown_until = max(estado.cooldown_until, fim)
            elif codigo == 503:
                espera = min(
                    _TRANSIENT_FAILURE_COOLDOWN_SECONDS * (2 ** min(estado.failures - 1, 4)),
                    _COOLDOWN_CAP_SECONDS,
                )
                estado.cooldown_until = agora + espera

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [
                {
                    "index": estado.index,
                    "project": estado.project,
                    "cooldown_until": estado.cooldown_until,
                    "disabled": estado.disabled,
                }
                for estado in self._states
            ]


_pool_lock = threading.Lock()
_pool: CredentialPool | None = None
_pool_config: tuple[str, str] | None = None


def _credential_pool() -> CredentialPool:
    global _pool, _pool_config
    config = (
        settings.GEMINI_API_KEYS,
        getattr(settings, "GEMINI_KEY_PROJECTS", ""),
    )
    with _pool_lock:
        if _pool is None or _pool_config != config:
            _pool = CredentialPool(*config)
            _pool_config = config
        return _pool


def _reset_credential_pool() -> None:
    """Recria o pool no próximo uso; destinado a testes isolados."""
    global _pool, _pool_config
    with _pool_lock:
        _pool = None
        _pool_config = None


class GeminiErro(Exception):
    """Erro de integração convertido em resposta segura para a API."""

    def __init__(self, status: int, detail: str, categoria: str = "indisponibilidade") -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.categoria = categoria


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
    if valor is None:
        valor = _retry_delay_from_details(getattr(exc, "details", None))
    try:
        segundos = float(getattr(valor, "seconds", valor))
    except (TypeError, ValueError):
        segundos = 1.0
    return min(max(segundos, 0.1), 2.0)


def _retry_delay_from_details(details: object) -> object | None:
    if isinstance(details, dict):
        for key in ("retryDelay", "retry_delay", "retryAfter", "retry_after"):
            if key in details:
                valor = details[key]
                if isinstance(valor, dict) and "seconds" in valor:
                    return float(valor["seconds"]) + float(valor.get("nanos", 0)) / 1e9
                if isinstance(valor, str):
                    correspondencia = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)s\s*", valor)
                    if correspondencia:
                        return float(correspondencia.group(1))
                return valor
        for valor in details.values():
            encontrado = _retry_delay_from_details(valor)
            if encontrado is not None:
                return encontrado
    elif isinstance(details, (list, tuple)):
        for valor in details:
            encontrado = _retry_delay_from_details(valor)
            if encontrado is not None:
                return encontrado
    return None


def _chamar_gemini(
    prompt: str, schema: type[T], credencial: _CredentialState | None = None
) -> T:
    client = None
    try:
        if credencial is None:
            credencial = _credential_pool().reserve()
        client = genai.Client(
            api_key=credencial.key,
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
        categoria = (
            "limite_diario"
            if re.search(r"\b(daily|per[_ -]?day|day)\b", str(exc), re.IGNORECASE)
            else "limite"
        )
        return GeminiErro(
            429,
            "O serviço de análise atingiu o limite de uso. Tente novamente mais tarde.",
            categoria,
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
    orcamento_ms = max(
        int(getattr(settings, "GEMINI_ORCAMENTO_MS", settings.GEMINI_TIMEOUT_MS)),
        1,
    )
    inicio_operacao = time.monotonic()
    credencial_retry: _CredentialState | None = None
    for tentativa in range(tentativas):
        inicio = time.monotonic()
        tentativa_atual = f"{tentativa + 1}/{tentativas}"
        if (time.monotonic() - inicio_operacao) * 1000 >= orcamento_ms:
            raise GeminiErro(
                504,
                "O serviço de IA demorou além do esperado. O material permanece nesta tela; "
                "tente novamente em alguns instantes.",
                "timeout",
            )
        credencial = credencial_retry or _credential_pool().reserve()
        credencial_retry = None
        try:
            return _chamar_gemini(prompt, schema, credencial)
        except GeminiErro as exc:
            if exc.categoria != "timeout":
                _credential_pool().report(credencial, exc)
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
            _credential_pool().report(credencial, exc)
            _registrar_falha(
                exc, inicio, erro.categoria, tentativa_atual, correlacao
            )
            if not _eh_transitorio(exc) or tentativa == tentativas - 1:
                raise erro from exc
            credencial_retry = credencial
            time.sleep(_espera_retry(exc))
        except OSError as exc:
            erro = _converter_falha(exc)
            _credential_pool().report(credencial, exc)
            _registrar_falha(
                exc, inicio, erro.categoria, tentativa_atual, correlacao
            )
            if tentativa == tentativas - 1:
                raise erro from exc
            time.sleep(0.5)
    raise GeminiErro(503, "O serviço de análise está temporariamente indisponível.")
