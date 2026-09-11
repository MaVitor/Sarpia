const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface PaginaTexto {
  numero: number;
  texto: string;
}

export interface MaterialResponse {
  total_paginas: number;
  paginas: PaginaTexto[];
  aviso: string | null;
}

export interface Topico {
  titulo: string;
  slide: number;
  resumo: string;
}

export interface TopicosResponse {
  topicos: Topico[];
}

export interface TopicoAvaliado {
  titulo: string;
  slide: number;
  status: "coberto" | "parcial" | "omitido";
  trecho_material: string;
  trecho_ensaio: string;
  comentario: string;
}

export interface ErroConteudo {
  descricao: string;
  slide: number;
  correcao: string;
  trecho_material: string;
}

export interface InfoNaoSustentada {
  trecho_ensaio: string;
  observacao: string;
}

export interface FeedbackResponse {
  resumo_geral: string;
  cobertura_percentual: number;
  topicos: TopicoAvaliado[];
  erros_conteudo: ErroConteudo[];
  info_nao_sustentada: InfoNaoSustentada[];
  ordem_apresentacao: { avaliacao: string; sugestao: string };
  perguntas_banca: string[];
  proximo_passo: string;
}

async function tratarErro(resposta: Response): Promise<never> {
  let detalhe = `Erro ${resposta.status}`;
  try {
    const corpo = await resposta.json();
    if (corpo?.detail) detalhe = corpo.detail;
  } catch {
    /* mantém o detalhe padrão */
  }
  throw new Error(detalhe);
}

export async function verificarSaude(): Promise<{ status: string }> {
  const r = await fetch(`${API_URL}/api/saude/`);
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function enviarMaterial(arquivo: File): Promise<MaterialResponse> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  const r = await fetch(`${API_URL}/api/materiais/`, { method: "POST", body: form });
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function extrairTopicos(paginas: PaginaTexto[]): Promise<TopicosResponse> {
  const r = await fetch(`${API_URL}/api/topicos/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paginas }),
  });
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function avaliarEnsaio(
  paginas: PaginaTexto[],
  ensaio: string
): Promise<FeedbackResponse> {
  const r = await fetch(`${API_URL}/api/avaliar/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paginas, ensaio }),
  });
  if (!r.ok) await tratarErro(r);
  return r.json();
}
