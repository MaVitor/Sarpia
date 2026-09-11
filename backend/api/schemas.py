"""Contratos Pydantic usados como response_schema do Gemini (structured output).

São a fonte única do formato do feedback: o SDK do Gemini garante que a resposta
da IA respeita estes modelos. As entradas HTTP são validadas pelos serializers DRF.
"""

from typing import Literal

from pydantic import BaseModel, Field


class PaginaTexto(BaseModel):
    numero: int
    texto: str


class Topico(BaseModel):
    titulo: str
    slide: int
    resumo: str


class TopicosResponse(BaseModel):
    topicos: list[Topico]


class TopicoAvaliado(BaseModel):
    titulo: str
    slide: int
    status: Literal["coberto", "parcial", "omitido"]
    trecho_material: str
    trecho_ensaio: str
    comentario: str


class ErroConteudo(BaseModel):
    descricao: str
    slide: int
    correcao: str
    trecho_material: str


class InfoNaoSustentada(BaseModel):
    trecho_ensaio: str
    observacao: str


class OrdemApresentacao(BaseModel):
    avaliacao: str
    sugestao: str


class FeedbackResponse(BaseModel):
    resumo_geral: str
    cobertura_percentual: int = Field(ge=0, le=100)
    topicos: list[TopicoAvaliado]
    erros_conteudo: list[ErroConteudo]
    info_nao_sustentada: list[InfoNaoSustentada]
    ordem_apresentacao: OrdemApresentacao
    perguntas_banca: list[str]
    proximo_passo: str


class PerguntasResponse(BaseModel):
    perguntas: list[str]
