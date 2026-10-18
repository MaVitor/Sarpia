import { useState } from "react";
import { enviarMaterial, extrairTopicos, type MaterialResponse, type PaginaTexto, type Topico } from "../lib/api";

export const MAX_PAGINAS = 20;
export const MAX_MATERIAL_CHARS = 50000;
export const MAX_PDF_MB = 8;

interface Props {
  paginas: PaginaTexto[];
  topicos: Topico[];
  onMaterial: (paginas: PaginaTexto[], nome: string, aviso: string | null) => void;
  onTopicos: (topicos: Topico[]) => void;
  onContinue: () => void;
}

export default function MaterialPage({ paginas, topicos, onMaterial, onTopicos, onContinue }: Props) {
  const [modo, setModo] = useState<"pdf" | "roteiro">("pdf");
  const [arquivo, setArquivo] = useState("");
  const [roteiro, setRoteiro] = useState(paginas.length === 1 && paginas[0].numero === 1 ? paginas[0].texto : "");
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState<"upload" | "topicos" | "">("");
  const [resposta, setResposta] = useState<MaterialResponse | null>(null);
  const [topicosObtidos, setTopicosObtidos] = useState(false);

  async function selecionar(file: File | undefined) {
    if (!file) return;
    setErro(""); setMensagem(""); setCarregando("upload"); onTopicos([]); setTopicosObtidos(false);
    try {
      const resultado = await enviarMaterial(file);
      setResposta(resultado); setArquivo(file.name);
      onMaterial(resultado.paginas, file.name, resultado.aviso);
      setMensagem("PDF enviado e texto extraído.");
    } catch (e) { setErro(e instanceof Error ? e.message : "Não foi possível enviar o PDF."); }
    finally { setCarregando(""); }
  }
  function usarRoteiro() {
    setErro(""); setMensagem(""); setResposta(null); onTopicos([]); setTopicosObtidos(false);
    if (!roteiro.trim()) { setErro("Escreva um roteiro antes de continuar."); return; }
    if (roteiro.length > MAX_MATERIAL_CHARS) { setErro(`O roteiro excede ${MAX_MATERIAL_CHARS.toLocaleString("pt-BR")} caracteres.`); return; }
    onMaterial([{ numero: 1, texto: roteiro }], "Roteiro", null);
    setMensagem("Roteiro pronto para análise.");
  }
  async function identificar() {
    if (!paginas.length) { setErro("Envie um PDF ou escreva um roteiro primeiro."); return; }
    setErro(""); setCarregando("topicos");
    try { const resultado = await extrairTopicos(paginas); onTopicos(resultado.topicos); setTopicosObtidos(true); }
    catch (e) { setErro(e instanceof Error ? e.message : "Não foi possível identificar os tópicos."); }
    finally { setCarregando(""); }
  }
  const materialPronto = paginas.length > 0;
  return <main className="flow-page flow-material" tabIndex={-1}>
    <p className="flow-kicker">Etapa 1 de 3</p><h1 className="flow-title" tabIndex={-1}>Escolha seu material</h1>
    <p className="flow-lede">Material e ensaio serão enviados ao provedor de IA para análise. Nada é salvo no navegador.</p>
    <div className="material-options"><section className={`flow-card ${modo === "pdf" ? "is-selected" : ""}`}><h2>Enviar slides em PDF</h2><p>Até {MAX_PDF_MB} MB e {MAX_PAGINAS} páginas.</p><label className="file-button" htmlFor="material-pdf">{carregando === "upload" ? "Enviando..." : "Escolher PDF"}</label><input id="material-pdf" type="file" accept=".pdf,application/pdf" onChange={(e) => void selecionar(e.target.files?.[0])} disabled={carregando !== ""} /><p className="file-name">{arquivo || "Nenhum arquivo escolhido"}</p>{resposta && <><p>{resposta.total_paginas} páginas extraídas.</p>{resposta.aviso && <p className="flow-notice">{resposta.aviso}</p>}</>}</section>
      <section className={`flow-card ${modo === "roteiro" ? "is-selected" : ""}`}><h2>Colar um roteiro</h2><p>Até {MAX_MATERIAL_CHARS.toLocaleString("pt-BR")} caracteres.</p><label htmlFor="roteiro">Seu roteiro</label><textarea id="roteiro" value={roteiro} maxLength={MAX_MATERIAL_CHARS} onFocus={() => setModo("roteiro")} onChange={(e) => { setRoteiro(e.target.value); setResposta(null); onTopicos([]); }} rows={8} /><span className="char-count">{roteiro.length.toLocaleString("pt-BR")} / {MAX_MATERIAL_CHARS.toLocaleString("pt-BR")}</span><button className="btn secondary-btn" type="button" onClick={usarRoteiro}>Usar roteiro</button></section></div>
    {resposta && <section className="flow-card extracted-card"><h2>Texto extraído</h2><div className="page-list">{resposta.paginas.map((pagina) => <details key={pagina.numero}><summary>Página {pagina.numero}</summary><pre>{pagina.texto || "Nenhum texto extraído nesta página."}</pre></details>)}</div></section>}
    {materialPronto && <div className="flow-actions"><button className="btn" type="button" onClick={() => void identificar()} disabled={carregando !== ""}>{carregando === "topicos" ? "Identificando tópicos..." : "Identificar tópicos"}</button></div>}
    {topicosObtidos && <section className="flow-card"><h2>Tópicos identificados</h2>{topicos.length > 0 ? <ul className="topic-list">{topicos.map((t) => <li key={`${t.slide}-${t.titulo}`}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span><p>{t.resumo}</p></li>)}</ul> : <p className="empty-state">A análise não retornou tópicos para este material.</p>}<button className="btn" type="button" onClick={onContinue}>Continuar para o ensaio</button></section>}
    {mensagem && <p className="flow-status" aria-live="polite">{mensagem}</p>}{erro && <p className="flow-error" role="alert">{erro}</p>}
  </main>;
}
