from typing import Final


CONTEXTOS: Final[tuple[str, ...]] = (
    "geral",
    "seminario",
    "defesa",
    "profissional",
    "pitch",
)

ROTULOS_PERGUNTAS: Final[dict[str, str]] = {
    "geral": "Perguntas do público",
    "seminario": "Perguntas da turma e do professor",
    "defesa": "Perguntas da banca",
    "profissional": "Perguntas da audiência",
    "pitch": "Perguntas sobre a proposta",
}

DESCRICOES_CONTEXTOS: Final[dict[str, str]] = {
    "geral": "uma apresentação geral",
    "seminario": "um trabalho escolar ou seminário",
    "defesa": "uma defesa acadêmica",
    "profissional": "uma apresentação profissional",
    "pitch": "um pitch ou proposta",
}


def rotulo_perguntas(contexto: str) -> str:
    return ROTULOS_PERGUNTAS.get(contexto, ROTULOS_PERGUNTAS["geral"])
