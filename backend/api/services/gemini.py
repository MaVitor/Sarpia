import threading
from datetime import datetime, time, timedelta
from typing import TypeVar
from zoneinfo import ZoneInfo

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
TZ_PACIFICO = ZoneInfo("America/Los_Angeles")


class GeminiErro(Exception):
    """Erro de integração com o Gemini, já com status HTTP e mensagem ao usuário."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _proxima_meia_noite_pacifico() -> datetime:
    """A cota diária (RPD) do free tier zera à meia-noite no horário do Pacífico."""
    agora = datetime.now(TZ_PACIFICO)
    amanha = (agora + timedelta(days=1)).date()
    return datetime.combine(amanha, time.min, tzinfo=TZ_PACIFICO)


class KeyPool:
    """Rotação round-robin de chaves Gemini com cooldown até o reset diário.

    Atenção: os limites do free tier são por PROJETO do Google Cloud, não por
    chave. A rotação só aumenta a cota se cada chave vier de um projeto diferente.
    """

    def __init__(self, keys: list[str]) -> None:
        self._keys = keys
        self._cooldown: dict[str, datetime] = {}
        self._indice = 0
        self._lock = threading.Lock()

    def adquirir(self) -> str | None:
        with self._lock:
            agora = datetime.now(TZ_PACIFICO)
            for _ in range(len(self._keys)):
                key = self._keys[self._indice % len(self._keys)]
                self._indice += 1
                if self._cooldown.get(key, agora - timedelta(seconds=1)) < agora:
                    return key
        return None

    def reportar_limite(self, key: str) -> None:
        with self._lock:
            self._cooldown[key] = _proxima_meia_noite_pacifico()


_pool: KeyPool | None = None
_pool_lock = threading.Lock()


def _lista_keys() -> list[str]:
    return [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]


def _get_pool() -> KeyPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            keys = _lista_keys()
            if not keys:
                raise GeminiErro(
                    500,
                    "Nenhuma chave Gemini configurada. Preencha GEMINI_API_KEYS no .env.",
                )
            _pool = KeyPool(keys)
    return _pool


def _chamar_gemini(key: str, prompt: str, schema: type[T]) -> T:
    client = genai.Client(api_key=key)
    resposta = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return schema.model_validate_json(resposta.text)


def _eh_limite(exc: Exception) -> bool:
    codigo = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return codigo == 429 or "RESOURCE_EXHAUSTED" in str(exc)


def gerar_estruturado(prompt: str, schema: type[T]) -> T:
    """Chama o Gemini tentando cada chave disponível até conseguir ou esgotar todas."""
    pool = _get_pool()
    tentativas = max(1, len(_lista_keys()))
    for _ in range(tentativas):
        key = pool.adquirir()
        if key is None:
            break
        try:
            return _chamar_gemini(key, prompt, schema)
        except genai_errors.ClientError as exc:
            if _eh_limite(exc):
                pool.reportar_limite(key)
                continue
            raise GeminiErro(502, f"Erro na API Gemini: {exc}")
    raise GeminiErro(
        503,
        "Limite diário das chaves atingido. A cota do free tier reinicia à "
        "meia-noite no horário do Pacífico (por volta das 4h-5h em Brasília).",
    )
