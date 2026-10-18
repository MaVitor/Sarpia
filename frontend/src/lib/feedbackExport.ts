import type { FeedbackResponse } from "./api";

const EXPLICACAO_COBERTURA =
  "Proporção de tópicos identificados como cobertos ou parciais. " +
  "Não representa nota nem comprovação de domínio do conteúdo.";

export interface FeedbackExportMaterial {
  nome: string;
}

export interface FeedbackExport {
  versao_formato: "1.0";
  exportado_em: string;
  material: FeedbackExportMaterial;
  feedback: FeedbackResponse;
}

function linha(rotulo: string, valor: string): string {
  return `${rotulo}: ${valor}`;
}

function trecho(rotulo: string, valor: string): string {
  return valor ? `${rotulo}: “${valor}”` : `${rotulo}: não informado`;
}

export function formatarFeedbackTexto(
  feedback: FeedbackResponse,
  material: FeedbackExportMaterial,
  exportadoEm: Date = new Date()
): string {
  const complementares = feedback.topicos_complementares ?? [];
  const contagens = feedback.topicos.reduce(
    (total, topico) => ({ ...total, [topico.status]: total[topico.status] + 1 }),
    { coberto: 0, parcial: 0, omitido: 0 }
  );
  const topicos = feedback.topicos.length
    ? feedback.topicos.map((topico, indice) => [
        `${indice + 1}. ${topico.titulo}`,
        `Status: ${topico.status}`,
        `Página: ${topico.slide === 1 && material.nome === "Roteiro" ? "Roteiro" : topico.slide}`,
        trecho("Evidência do material", topico.trecho_material),
        trecho("Trecho do ensaio", topico.trecho_ensaio),
        `Comentário: ${topico.comentario}`,
      ].join("\n")).join("\n\n")
    : "Nenhum tópico foi retornado pela análise.";
  const topicosComplementares = complementares.length
    ? complementares.map((topico, indice) => [
        `${indice + 1}. ${topico.titulo}`,
        `Status: ${topico.status}`,
        `Página: ${topico.slide === 1 && material.nome === "Roteiro" ? "Roteiro" : topico.slide}`,
        trecho("Evidência do material", topico.trecho_material),
        trecho("Trecho do ensaio", topico.trecho_ensaio),
        `Comentário: ${topico.comentario}`,
      ].join("\n")).join("\n\n")
    : "Nenhum elemento complementar foi retornado pela análise.";
  const divergencias = feedback.erros_conteudo.length
    ? feedback.erros_conteudo.map((erro, indice) => [
        `${indice + 1}. Página: ${erro.slide}`,
        `Descrição: ${erro.descricao}`,
        trecho("Evidência do material", erro.trecho_material),
        `Sugestão de revisão: ${erro.correcao}`,
      ].join("\n")).join("\n\n")
    : "Nenhuma divergência de conteúdo foi apontada.";
  const informacoes = feedback.info_nao_sustentada.length
    ? feedback.info_nao_sustentada.map((info, indice) => [
        `${indice + 1}. ${trecho("Trecho do ensaio", info.trecho_ensaio)}`,
        `Observação: ${info.observacao}`,
      ].join("\n")).join("\n\n")
    : "Nenhuma informação não sustentada foi apontada.";
  const perguntas = feedback.perguntas_banca.length
    ? feedback.perguntas_banca.map((pergunta, indice) => `${indice + 1}. ${pergunta}`).join("\n")
    : "Nenhuma pergunta foi retornada.";

  return [
    "Sarpia — Relatório de ensaio",
    linha("Exportação realizada em", exportadoEm.toLocaleString("pt-BR")),
    linha("Material", material.nome || "Não informado"),
    "",
    "Resumo geral",
    feedback.resumo_geral,
    "",
    "Cobertura dos tópicos principais",
    feedback.topicos.length
      ? linha("Percentual", `${feedback.cobertura_percentual}%`)
      : "Cobertura não calculável: nenhum tópico principal identificado.",
    EXPLICACAO_COBERTURA,
    feedback.topicos.length
      ? `Quantidade de tópicos principais: ${feedback.topicos.length}`
      : "Nenhum tópico principal identificado.",
    `Cobertos: ${contagens.coberto} | Parciais: ${contagens.parcial} | Omitidos: ${contagens.omitido}`,
    "",
    "Tópicos principais",
    topicos,
    "",
    "Elementos complementares",
    topicosComplementares,
    "",
    "Divergências de conteúdo",
    divergencias,
    "",
    "Informações não sustentadas",
    informacoes,
    "",
    "Ordem da apresentação",
    `Avaliação: ${feedback.ordem_apresentacao.avaliacao}`,
    `Sugestão: ${feedback.ordem_apresentacao.sugestao}`,
    "",
    "Perguntas da banca",
    perguntas,
    "",
    "Próximo passo",
    feedback.proximo_passo,
    "",
    "Aviso",
    "Este feedback é gerado por IA e não substitui professor, orientador ou avaliador humano.",
  ].join("\n");
}

export function criarFeedbackExport(
  feedback: FeedbackResponse,
  material: FeedbackExportMaterial,
  exportadoEm: Date = new Date()
): FeedbackExport {
  return {
    versao_formato: "1.0",
    exportado_em: exportadoEm.toISOString(),
    material: { nome: material.nome || "Não informado" },
    feedback,
  };
}

export function nomeArquivoFeedback(extensao: "txt" | "json", agora: Date = new Date()): string {
  const iso = agora.toISOString();
  const data = `${iso.slice(0, 10).replace(/-/g, "")}-${iso.slice(11, 19).replace(/:/g, "")}`;
  return `sarpia-feedback-${data}.${extensao}`;
}

export function baixarTexto(conteudo: string, nomeArquivo: string, tipo: string): void {
  const blob = new Blob([conteudo], { type: `${tipo};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  window.setTimeout(() => {
    link.remove();
    URL.revokeObjectURL(url);
  }, 1000);
}
