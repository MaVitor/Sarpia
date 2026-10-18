import type { FeedbackResponse } from "../lib/api";
import {
  baixarTexto,
  criarFeedbackExport,
  formatarFeedbackTexto,
  nomeArquivoFeedback,
} from "../lib/feedbackExport";

interface Props { feedback: FeedbackResponse; materialNome: string; onReview: () => void; onChangeMaterial: () => void; onHome: () => void; }
const status: Record<string, string> = { coberto: "Coberto", parcial: "Parcial", omitido: "Omitido" };

export default function FeedbackPage({ feedback, materialNome, onReview, onChangeMaterial, onHome }: Props) {
  function exportarTexto() {
    const agora = new Date();
    baixarTexto(
      formatarFeedbackTexto(feedback, { nome: materialNome }, agora),
      nomeArquivoFeedback("txt", agora),
      "text/plain"
    );
  }
  function exportarJson() {
    const agora = new Date();
    baixarTexto(
      JSON.stringify(criarFeedbackExport(feedback, { nome: materialNome }, agora), null, 2),
      nomeArquivoFeedback("json", agora),
      "application/json"
    );
  }
  return <main className="flow-page flow-feedback" tabIndex={-1}>
    <p className="flow-kicker">Etapa 3 de 3</p><h1 className="flow-title" tabIndex={-1}>Seu feedback</h1>
    <div className="feedback-report-heading"><h2>Sarpia — Relatório de ensaio</h2><p>Os arquivos incluem trechos do material e do ensaio. Compartilhe-os com cuidado.</p></div>
    <section className="flow-card feedback-summary"><h2>Resumo geral</h2><p>{feedback.resumo_geral}</p><div className="coverage"><strong>{feedback.cobertura_percentual}%</strong><div><p>cobertura do material</p><p>Proporção de tópicos identificados como cobertos ou parciais. Não representa nota nem comprovação de domínio do conteúdo.</p></div></div></section>
    <section className="flow-card"><h2>Tópicos</h2>{feedback.topicos.length ? <div className="feedback-list">{feedback.topicos.map((t) => <article key={`${t.slide}-${t.titulo}`}><div className="feedback-heading"><h3>{t.titulo}</h3><span className={`status status-${t.status}`}>{status[t.status]}</span></div><p>Página {t.slide}</p>{t.trecho_material && <blockquote>“{t.trecho_material}”</blockquote>}{t.trecho_ensaio && <p><strong>Seu ensaio:</strong> “{t.trecho_ensaio}”</p>}<p>{t.comentario}</p></article>)}</div> : <p className="empty-state">Nenhum tópico foi retornado pela análise.</p>}</section>
    <section className="flow-card"><h2>Divergências de conteúdo</h2>{feedback.erros_conteudo.length ? <div className="feedback-list">{feedback.erros_conteudo.map((e, i) => <article key={`${e.slide}-${i}`}><h3>Página {e.slide}</h3><p>{e.descricao}</p>{e.trecho_material && <blockquote>“{e.trecho_material}”</blockquote>}<p><strong>Sugestão de revisão:</strong> {e.correcao}</p></article>)}</div> : <p className="empty-state">Nenhuma divergência de conteúdo apontada.</p>}</section>
    <section className="flow-card"><h2>Informações não sustentadas</h2>{feedback.info_nao_sustentada.length ? <div className="feedback-list">{feedback.info_nao_sustentada.map((i, index) => <article key={index}><blockquote>“{i.trecho_ensaio}”</blockquote><p>{i.observacao}</p></article>)}</div> : <p className="empty-state">Nenhuma informação sem base no material foi apontada.</p>}</section>
    <div className="feedback-two-col"><section className="flow-card"><h2>Ordem da apresentação</h2><p>{feedback.ordem_apresentacao.avaliacao}</p><p><strong>Sugestão:</strong> {feedback.ordem_apresentacao.sugestao}</p></section><section className="flow-card"><h2>Perguntas da banca</h2>{feedback.perguntas_banca.length ? <ul>{feedback.perguntas_banca.map((p, i) => <li key={i}>{p}</li>)}</ul> : <p className="empty-state">Nenhuma pergunta foi retornada.</p>}</section></div>
    <section className="flow-card next-step"><h2>Próximo passo</h2><p>{feedback.proximo_passo}</p></section>
    <div className="flow-card export-card"><h2>Exportar feedback</h2><p>Os arquivos usam somente o resultado desta avaliação, que permanece em memória.</p><div className="export-actions"><button className="btn secondary-btn" type="button" onClick={exportarTexto}>Baixar texto</button><button className="btn secondary-btn" type="button" onClick={exportarJson}>Baixar JSON</button><button className="btn secondary-btn" type="button" onClick={() => window.print()}>Imprimir / Salvar PDF</button></div></div>
    <div className="flow-actions feedback-actions"><button className="btn" type="button" onClick={onReview}>Revisar ensaio</button><button className="text-button" type="button" onClick={onChangeMaterial}>Trocar material</button><button className="text-button" type="button" onClick={onHome}>Voltar ao início</button></div>
  </main>;
}
