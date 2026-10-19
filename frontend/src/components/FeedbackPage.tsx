import type { FeedbackResponse, TopicoAvaliado } from "../lib/api";
import {
  baixarTexto,
  criarFeedbackExport,
  formatarFeedbackTexto,
  nomeArquivoFeedback,
} from "../lib/feedbackExport";

interface Props { feedback: FeedbackResponse; materialNome: string; onReview: () => void; onChangeMaterial: () => void; onHome: () => void; }
const status: Record<string, string> = { coberto: "Coberto", parcial: "Parcial", omitido: "Omitido" };

export default function FeedbackPage({ feedback, materialNome, onReview, onChangeMaterial, onHome }: Props) {
  const principais = feedback.topicos;
  const complementares = feedback.topicos_complementares ?? [];
  const contagens = principais.reduce(
    (total, topico) => ({ ...total, [topico.status]: total[topico.status] + 1 }),
    { coberto: 0, parcial: 0, omitido: 0 }
  );
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
    <section className="flow-card feedback-summary"><h2>Resumo geral</h2><p>{feedback.resumo_geral}</p><div className="coverage"><strong>{principais.length ? `${feedback.cobertura_percentual}%` : "—"}</strong><div><p>Cobertura dos tópicos principais</p><p>Proporção de tópicos principais identificados como cobertos ou parciais. Não representa nota nem comprovação de domínio do conteúdo.</p>{principais.length ? <p className="coverage-counts">Cobertos: {contagens.coberto} · Parciais: {contagens.parcial} · Omitidos: {contagens.omitido}. Parciais contam como abordados, mas podem conter lacunas ou divergências.</p> : <p>Cobertura não calculável: nenhum tópico principal identificado.</p>}{feedback.erros_conteudo.length > 0 && <div className="coverage-warning" role="alert"><p>Atenção: {feedback.erros_conteudo.length} divergência{feedback.erros_conteudo.length === 1 ? "" : "s"} de conteúdo identificada{feedback.erros_conteudo.length === 1 ? "" : "s"}.</p><p>A cobertura indica os tópicos abordados, não a correção de todas as explicações.</p><a href="#divergencias-conteudo">Ver divergências de conteúdo</a></div>}</div></div></section>
    <section className="flow-card"><h2>Tópicos principais</h2>{principais.length ? <div className="feedback-list">{principais.map((t) => <TopicoCard key={`${t.slide}-${t.titulo}`} topico={t} materialNome={materialNome} />)}</div> : <p className="empty-state">Cobertura não calculável: nenhum tópico principal identificado.</p>}</section>
    {complementares.length > 0 && <section className="flow-card"><h2>Elementos complementares</h2><p className="section-note">Itens contextuais do material; não entram na cobertura dos tópicos principais.</p><div className="feedback-list">{complementares.map((t) => <TopicoCard key={`${t.slide}-${t.titulo}`} topico={t} materialNome={materialNome} />)}</div></section>}
    <section className="flow-card" id="divergencias-conteudo"><h2>Divergências de conteúdo</h2>{feedback.erros_conteudo.length ? <div className="feedback-list">{feedback.erros_conteudo.map((e, i) => <article key={`${e.slide}-${i}`}><h3>Página {e.slide}</h3><p>{e.descricao}</p>{e.trecho_material && <blockquote>“{e.trecho_material}”</blockquote>}<p><strong>Sugestão de revisão:</strong> {e.correcao}</p></article>)}</div> : <p className="empty-state">Nenhuma divergência de conteúdo apontada.</p>}</section>
    <section className="flow-card"><h2>Informações não sustentadas</h2>{feedback.info_nao_sustentada.length ? <div className="feedback-list">{feedback.info_nao_sustentada.map((i, index) => <article key={index}><blockquote>“{i.trecho_ensaio}”</blockquote><p>{i.observacao}</p></article>)}</div> : <p className="empty-state">Nenhuma informação sem base no material foi apontada.</p>}</section>
    <div className="feedback-two-col"><section className="flow-card"><h2>Ordem da apresentação</h2><p>{feedback.ordem_apresentacao.avaliacao}</p><p><strong>Sugestão:</strong> {feedback.ordem_apresentacao.sugestao}</p></section><section className="flow-card"><h2>Perguntas da banca</h2>{feedback.perguntas_banca.length ? <ul>{feedback.perguntas_banca.map((p, i) => <li key={i}>{p}</li>)}</ul> : <p className="empty-state">Nenhuma pergunta foi retornada.</p>}</section></div>
    <section className="flow-card next-step"><h2>Próximo passo</h2><p>{feedback.proximo_passo}</p></section>
    <div className="flow-card export-card"><h2>Exportar feedback</h2><p>Os arquivos usam somente o resultado desta avaliação, que permanece em memória.</p><div className="export-actions"><button className="btn secondary-btn" type="button" onClick={exportarTexto}>Baixar texto</button><button className="btn secondary-btn" type="button" onClick={exportarJson}>Baixar JSON</button><button className="btn secondary-btn" type="button" onClick={() => window.print()}>Imprimir / Salvar PDF</button></div></div>
    <div className="flow-actions feedback-actions"><button className="btn" type="button" onClick={onReview}>Revisar ensaio</button><button className="text-button" type="button" onClick={onChangeMaterial}>Trocar material</button><button className="text-button" type="button" onClick={onHome}>Voltar ao início</button></div>
  </main>;
}

function TopicoCard({ topico, materialNome }: { topico: TopicoAvaliado; materialNome: string }) {
  return <article><div className="feedback-heading"><h3>{topico.titulo}</h3><span className={`status status-${topico.status}`}>{status[topico.status]}</span></div><p>{topico.slide === 1 && materialNome === "Roteiro" ? "Roteiro" : `Página ${topico.slide}`}</p>{topico.trecho_material && <blockquote>“{topico.trecho_material}”</blockquote>}{topico.trecho_ensaio && <p><strong>Seu ensaio:</strong> “{topico.trecho_ensaio}”</p>}<p>{topico.comentario}</p></article>;
}
