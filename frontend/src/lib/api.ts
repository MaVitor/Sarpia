const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
let csrfToken: string | null = null;

function cookieValue(name: string): string | null {
  const item = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return item ? decodeURIComponent(item.slice(name.length + 1)) : null;
}

async function obterCsrf(): Promise<string> {
  const cookie = cookieValue("csrftoken");
  if (cookie) {
    csrfToken = cookie;
    return cookie;
  }
  if (csrfToken) return csrfToken;
  const resposta = await fetch(`${API_URL}/api/auth/csrf/`, { credentials: "include" });
  if (!resposta.ok) await tratarErro(resposta);
  const dados = (await resposta.json()) as { csrfToken: string };
  csrfToken = cookieValue("csrftoken") ?? dados.csrfToken;
  return csrfToken;
}

async function opcoesProtegidas(init: RequestInit = {}): Promise<RequestInit> {
  const headers = new Headers(init.headers);
  headers.set("X-CSRFToken", await obterCsrf());
  return { ...init, headers, credentials: "include" };
}

async function requisicao(url: string, init: RequestInit = {}): Promise<Response> {
  const metodo = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (metodo !== "GET" && metodo !== "HEAD" && !headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", crypto.randomUUID());
  }
  const opcoes = { ...init, headers };
  return fetch(url, metodo === "GET" || metodo === "HEAD" ? { ...opcoes, credentials: "include" } : await opcoesProtegidas(opcoes));
}

export interface AuthUser {
  email: string;
  nome: string;
}

export interface SessionResponse {
  autenticado: boolean;
  usuario: AuthUser | null;
}

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

export type ContextoApresentacao = "geral" | "seminario" | "defesa" | "profissional" | "pitch";

export const CONTEXTOS_APRESENTACAO: { value: ContextoApresentacao; label: string }[] = [
  { value: "geral", label: "Geral" },
  { value: "seminario", label: "Trabalho escolar ou seminário" },
  { value: "defesa", label: "Defesa acadêmica" },
  { value: "profissional", label: "Apresentação profissional" },
  { value: "pitch", label: "Pitch ou proposta" },
];

export const ROTULOS_PERGUNTAS: Record<ContextoApresentacao, string> = {
  geral: "Perguntas do público",
  seminario: "Perguntas da turma e do professor",
  defesa: "Perguntas da banca",
  profissional: "Perguntas da audiência",
  pitch: "Perguntas sobre a proposta",
};

export interface TopicoReferencia extends Topico {
  id: string;
  categoria: "principal" | "complementar";
}

export interface TopicosResponse {
  versao_contrato: string;
  modo: "pdf" | "roteiro";
  material_hash: string;
  topicos: TopicoReferencia[];
  topicos_complementares: TopicoReferencia[];
  assinatura: string;
  presentation_id: string;
  contexto?: ContextoApresentacao;
  pessoas_material?: { nome: string; papel: string; slide: number; trecho: string }[];
}

export interface TopicoAvaliado {
  id?: string | null;
  titulo: string;
  slide: number;
  categoria?: "principal" | "complementar";
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
  topicos_complementares?: TopicoAvaliado[];
  erros_conteudo: ErroConteudo[];
  info_nao_sustentada: InfoNaoSustentada[];
  ordem_apresentacao: { avaliacao: string; sugestao: string };
  perguntas_banca: string[];
  proximo_passo: string;
  pessoas_material?: { nome: string; papel: string; slide: number; trecho: string }[];
}

export interface ReferenciaTopicos extends TopicosResponse {}

export interface PresentationSummary {
  id: string;
  titulo: string;
  modo: "pdf" | "roteiro";
  referencia_versao: string;
  criada_em: string;
  atualizada_em: string;
  quantidade_tentativas: number;
  contexto?: ContextoApresentacao;
}

export interface HistoryAttempt {
  id: string;
  ensaio: string;
  feedback: FeedbackResponse;
  referencia_versao: string;
  modelo: string | null;
  contrato: string | null;
  criada_em: string;
}

export interface PresentationDetail extends PresentationSummary {
  paginas: PaginaTexto[];
  referencia: ReferenciaTopicos;
  tentativas: HistoryAttempt[];
}

async function tratarErro(resposta: Response): Promise<never> {
  let detalhe = `Erro ${resposta.status}`;
  try {
    const corpo: unknown = await resposta.json();
    if (typeof corpo === "object" && corpo !== null) {
      const dados = corpo as Record<string, unknown>;
      if (typeof dados.detail === "string") {
        detalhe = dados.detail;
      } else {
        const mensagens = Object.entries(dados).flatMap(([campo, valor]) =>
          extrairMensagens(valor, campo)
        );
        if (mensagens.length > 0) detalhe = mensagens.join(" ");
      }
    }
  } catch {
    /* mantém o detalhe padrão */
  }
  throw new Error(detalhe);
}

function extrairMensagens(valor: unknown, campo: string): string[] {
  if (typeof valor === "string") return [`${campo}: ${valor}`];
  if (Array.isArray(valor)) {
    return valor.flatMap((item) => extrairMensagens(item, campo));
  }
  if (typeof valor === "object" && valor !== null) {
    return Object.entries(valor).flatMap(([chave, item]) =>
      extrairMensagens(item, `${campo}.${chave}`)
    );
  }
  return [];
}

export async function verificarSaude(): Promise<{ status: string }> {
  const r = await requisicao(`${API_URL}/api/saude/`);
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function enviarMaterial(arquivo: File, signal?: AbortSignal): Promise<MaterialResponse> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  const r = await requisicao(`${API_URL}/api/materiais/`, { method: "POST", body: form, signal });
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function extrairTopicos(
  paginas: PaginaTexto[],
  modo: "pdf" | "roteiro",
  titulo: string,
  contexto: ContextoApresentacao = "geral",
  signal?: AbortSignal
): Promise<TopicosResponse> {
  const r = await requisicao(`${API_URL}/api/topicos/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paginas, modo, titulo, contexto }),
    signal,
  });
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function avaliarEnsaio(
  ensaio: string,
  presentationId: string | null,
  paginas: PaginaTexto[],
  referencia: ReferenciaTopicos,
  modo: "pdf" | "roteiro",
  _contexto: ContextoApresentacao,
  idempotencyKey: string,
  signal?: AbortSignal
): Promise<FeedbackResponse> {
  const r = await requisicao(`${API_URL}/api/avaliar/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(presentationId ? {
      presentation_id: presentationId,
      ensaio,
      idempotency_key: idempotencyKey,
    } : { paginas, ensaio, referencia, modo, contexto: _contexto }),
    signal,
  });
  if (!r.ok) await tratarErro(r);
  const dados: FeedbackResponse = await r.json();
  return { ...dados, topicos_complementares: dados.topicos_complementares ?? [] };
}

export async function listarApresentacoes(): Promise<{ resultados: PresentationSummary[]; pagina: number; tem_proxima: boolean }> {
  const r = await requisicao(`${API_URL}/api/apresentacoes/`);
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function obterApresentacao(id: string): Promise<PresentationDetail> {
  const r = await requisicao(`${API_URL}/api/apresentacoes/${id}/`);
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function excluirApresentacao(id: string): Promise<void> {
  const r = await requisicao(`${API_URL}/api/apresentacoes/${id}/`, { method: "DELETE" });
  if (!r.ok) await tratarErro(r);
}

export async function excluirTentativa(presentationId: string, attemptId: string): Promise<void> {
  const r = await requisicao(`${API_URL}/api/apresentacoes/${presentationId}/tentativas/${attemptId}/`, { method: "DELETE" });
  if (!r.ok) await tratarErro(r);
}

export async function obterSessao(): Promise<SessionResponse> {
  const r = await requisicao(`${API_URL}/api/auth/session/`);
  if (!r.ok) await tratarErro(r);
  return r.json();
}

export async function entrar(email: string, password: string): Promise<void> {
  const r = await requisicao(`${API_URL}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) await tratarErro(r);
}

export async function cadastrar(nome: string, email: string, password: string, password2: string): Promise<void> {
  const r = await requisicao(`${API_URL}/api/auth/signup/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, email, password, password2 }),
  });
  if (!r.ok) await tratarErro(r);
}

export async function sair(): Promise<void> {
  const r = await requisicao(`${API_URL}/api/auth/logout/`, { method: "POST" });
  if (!r.ok) await tratarErro(r);
  csrfToken = null;
}
