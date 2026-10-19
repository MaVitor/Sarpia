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


class TopicoReferencia(BaseModel):
    id: str
    titulo: str
    categoria: Literal["principal", "complementar"]
    slide: int
    resumo: str


class ReferenciaTopicos(BaseModel):
    versao_contrato: str
    modo: Literal["pdf", "roteiro"]
    material_hash: str
    topicos: list[TopicoReferencia]
    topicos_complementares: list[TopicoReferencia] = Field(default_factory=list)
    assinatura: str


class TopicosResponse(BaseModel):
    topicos: list[Topico]
    topicos_complementares: list[Topico] = Field(default_factory=list)


class TopicoAvaliado(BaseModel):
    id: str | None = None
    titulo: str
    slide: int
    categoria: Literal["principal", "complementar"] = "principal"
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
    topicos_complementares: list[TopicoAvaliado] = Field(default_factory=list)
    erros_conteudo: list[ErroConteudo]
    info_nao_sustentada: list[InfoNaoSustentada]
    ordem_apresentacao: OrdemApresentacao
    perguntas_banca: list[str]
    proximo_passo: str


class PerguntasResponse(BaseModel):
    perguntas: list[str]


class TopicoAvaliadoInterno(BaseModel):
    id: str
    status: Literal["coberto", "parcial", "omitido"]
    trecho_material: str
    trecho_ensaio: str
    comentario: str


class FeedbackInternoResponse(BaseModel):
    resumo_geral: str
    cobertura_percentual: int = Field(ge=0, le=100)
    topicos: list[TopicoAvaliadoInterno]
    topicos_complementares: list[TopicoAvaliadoInterno] = Field(default_factory=list)
    erros_conteudo: list[ErroConteudo]
    info_nao_sustentada: list[InfoNaoSustentada]
    ordem_apresentacao: OrdemApresentacao
    perguntas_banca: list[str]
    proximo_passo: str
