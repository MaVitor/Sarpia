import hashlib
import json
from typing import Any

from django.core import signing

from api.schemas import (
    ReferenciaTopicos,
    TopicoReferencia,
    Topico,
)

_SALT = "sarpia.topicos.referencia.v1"
_VERSAO = "1.0"


def hash_material(modo: str, paginas: list[dict[str, Any]]) -> str:
    representacao = {
        "modo": modo,
        "paginas": [
            {"numero": pagina["numero"], "texto": pagina["texto"]}
            for pagina in paginas
        ],
    }
    conteudo = json.dumps(
        representacao, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def criar_referencia(
    modo: str,
    paginas: list[dict[str, Any]],
    topicos: list[Topico],
    topicos_complementares: list[Topico] | None = None,
) -> ReferenciaTopicos:
    numeros = {pagina["numero"] for pagina in paginas}
    todos = list(topicos) + list(topicos_complementares or [])
    if any(topico.slide not in numeros for topico in todos):
        raise ValueError("A referência contém tópico associado a página inexistente.")

    principais = [
        TopicoReferencia(
            id=f"principal-{indice:03d}",
            titulo=topico.titulo,
            categoria="principal",
            slide=topico.slide,
            resumo=topico.resumo,
        )
        for indice, topico in enumerate(topicos, 1)
    ]
    complementares = [
        TopicoReferencia(
            id=f"complementar-{indice:03d}",
            titulo=topico.titulo,
            categoria="complementar",
            slide=topico.slide,
            resumo=topico.resumo,
        )
        for indice, topico in enumerate(topicos_complementares or [], 1)
    ]
    dados = {
        "versao_contrato": _VERSAO,
        "modo": modo,
        "material_hash": hash_material(modo, paginas),
        "topicos": [topico.model_dump() for topico in principais],
        "topicos_complementares": [
            topico.model_dump() for topico in complementares
        ],
    }
    return ReferenciaTopicos(
        **dados,
        assinatura=signing.dumps(dados, salt=_SALT, compress=True),
    )


def validar_referencia(
    referencia: dict[str, Any],
    modo: str,
    paginas: list[dict[str, Any]],
) -> ReferenciaTopicos:
    assinatura = referencia.get("assinatura")
    dados = {chave: valor for chave, valor in referencia.items() if chave != "assinatura"}
    if not isinstance(assinatura, str):
        raise ValueError("A referência do material não possui assinatura válida.")
    try:
        assinado = signing.loads(assinatura, salt=_SALT)
    except signing.BadSignature as exc:
        raise ValueError("A referência do material não possui assinatura válida.") from exc
    if assinado != dados:
        raise ValueError("A referência do material foi alterada.")
    try:
        resultado = ReferenciaTopicos(**dados, assinatura=assinatura)
    except Exception as exc:
        raise ValueError("A referência do material é incompatível.") from exc
    if resultado.modo != modo:
        raise ValueError("A referência não corresponde ao modo do material.")
    if resultado.material_hash != hash_material(modo, paginas):
        raise ValueError("A referência não corresponde ao material enviado.")
    numeros = {pagina["numero"] for pagina in paginas}
    if any(
        topico.slide not in numeros
        for topico in resultado.topicos + resultado.topicos_complementares
    ):
        raise ValueError("A referência contém página inexistente.")
    ids = [topico.id for topico in resultado.topicos + resultado.topicos_complementares]
    if len(ids) != len(set(ids)):
        raise ValueError("A referência contém IDs duplicados.")
    return resultado
