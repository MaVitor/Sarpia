import { useEffect, useRef, useState } from "react";
import { enviarMaterial, extrairTopicos, type MaterialResponse, type PaginaTexto, type ReferenciaTopicos } from "../lib/api";

export const MAX_PAGINAS = 20;
export const MAX_MATERIAL_CHARS = 50000;
export const MAX_PDF_MB = 8;

interface Props {
  paginas: PaginaTexto[];
  referencia: ReferenciaTopicos | null;
  onMaterial: (paginas: PaginaTexto[], nome: string, aviso: string | null, modo: "pdf" | "roteiro") => void;
  onReferencia: (referencia: ReferenciaTopicos | null) => void;
  onContinue: () => void;
}

export default function MaterialPage({ paginas, referencia, onMaterial, onReferencia, onContinue }: Props) {
  const [modo, setModo] = useState<"pdf" | "roteiro">("pdf");
  const [arquivo, setArquivo] = useState("");
  const [roteiro, setRoteiro] = useState(paginas.length === 1 && paginas[0].numero === 1 ? paginas[0].texto : "");
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState<"upload" | "topicos" | "">("");
  const [resposta, setResposta] = useState<MaterialResponse | null>(null);
  const [topicosObtidos, setTopicosObtidos] = useState(false);
  const requisicaoAtual = useRef<AbortController | null>(null);
  useEffect(() => () => requisicaoAtual.current?.abort(), []);

  async function selecionar(file: File | undefined) {
    if (!file) return;
    requisicaoAtual.current?.abort();
    const controlador = new AbortController();
    requisicaoAtual.current = controlador;
    setErro(""); setMensagem(""); setCarregando("upload"); onReferencia(null); setTopicosObtidos(false);
    try {
      const resultado = await enviarMaterial(file, controlador.signal);
      setResposta(resultado); setArquivo(file.name);
      onMaterial(resultado.paginas, file.name, resultado.aviso, "pdf");
      setMensagem("PDF enviado e texto extraído.");
    } catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e instanceof Error ? e.message : "Não foi possível enviar o PDF."); }
    finally { setCarregando(""); }
  }
  function usarRoteiro() {
    requisicaoAtual.current?.abort();
    setErro(""); setMensagem(""); setResposta(null); onReferencia(null); setTopicosObtidos(false);
    if (!roteiro.trim()) { setErro("Escreva um roteiro antes de continuar."); return; }
    if (roteiro.length > MAX_MATERIAL_CHARS) { setErro(`O roteiro excede ${MAX_MATERIAL_CHARS.toLocaleString("pt-BR")} caracteres.`); return; }
    onMaterial([{ numero: 1, texto: roteiro }], "Roteiro", null, "roteiro");
    setMensagem("Roteiro pronto para análise.");
  }
  async function identificar() {
    if (!paginas.length) { setErro("Envie um PDF ou escreva um roteiro primeiro."); return; }
    requisicaoAtual.current?.abort();
    const controlador = new AbortController();
    requisicaoAtual.current = controlador;
    setErro(""); setCarregando("topicos");
    try { const resultado = await extrairTopicos(paginas, modo, controlador.signal); onReferencia(resultado); setTopicosObtidos(true); }
    catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e instanceof Error ? e.message : "Não foi possível identificar os tópicos."); }
    finally { setCarregando(""); }
  }
  const materialPronto = paginas.length > 0;
  return <main className="flow-page flow-material" tabIndex={-1}>
    <p className="flow-kicker">Etapa 1 de 3</p><h1 className="flow-title" tabIndex={-1}>Escolha seu material</h1>
    <p className="flow-lede">Material e ensaio serão enviados ao provedor de IA para análise. Nada é salvo no navegador.</p>
    <div className="material-options"><section className={`flow-card ${modo === "pdf" ? "is-selected" : ""}`}><h2>Enviar slides em PDF</h2><p>Até {MAX_PDF_MB} MB e {MAX_PAGINAS} páginas.</p><label className="file-button" htmlFor="material-pdf">{carregando === "upload" ? "Enviando..." : "Escolher PDF"}</label><input id="material-pdf" type="file" accept=".pdf,application/pdf" onChange={(e) => void selecionar(e.target.files?.[0])} disabled={carregando !== ""} /><p className="file-name">{arquivo || "Nenhum arquivo escolhido"}</p>{resposta && <><p>{resposta.total_paginas} páginas extraídas.</p>{resposta.aviso && <p className="flow-notice">{resposta.aviso}</p>}</>}</section>
      <section className={`flow-card ${modo === "roteiro" ? "is-selected" : ""}`}><h2>Colar um roteiro</h2><p>Até {MAX_MATERIAL_CHARS.toLocaleString("pt-BR")} caracteres.</p><label htmlFor="roteiro">Seu roteiro</label><textarea id="roteiro" value={roteiro} maxLength={MAX_MATERIAL_CHARS} onFocus={() => setModo("roteiro")} onChange={(e) => { setRoteiro(e.target.value); setResposta(null); onReferencia(null); setTopicosObtidos(false); }} rows={8} /><span className="char-count">{roteiro.length.toLocaleString("pt-BR")} / {MAX_MATERIAL_CHARS.toLocaleString("pt-BR")}</span><button className="btn secondary-btn" type="button" onClick={usarRoteiro}>Usar roteiro</button></section></div>
    {resposta && <section className="flow-card extracted-card"><h2>Texto extraído</h2><div className="page-list">{resposta.paginas.map((pagina) => <details key={pagina.numero}><summary>Página {pagina.numero}</summary><pre>{pagina.texto || "Nenhum texto extraído nesta página."}</pre></details>)}</div></section>}
    {materialPronto && <div className="flow-actions"><button className="btn" type="button" onClick={() => void identificar()} disabled={carregando !== ""}>{carregando === "topicos" ? "Identificando tópicos..." : "Identificar tópicos"}</button></div>}
    {topicosObtidos && referencia && <section className="flow-card"><h2>Tópicos identificados</h2>{referencia.topicos.length > 0 ? <ul className="topic-list">{referencia.topicos.map((t) => <li key={t.id}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span><p>{t.resumo}</p></li>)}</ul> : <p className="empty-state">A análise não retornou tópicos principais para este material.</p>}{referencia.topicos_complementares.length > 0 && <><h3>Elementos complementares</h3><ul className="topic-list">{referencia.topicos_complementares.map((t) => <li key={t.id}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span><p>{t.resumo}</p></li>)}</ul></>}<button className="btn" type="button" onClick={onContinue}>Continuar para o ensaio</button></section>}
    {mensagem && <p className="flow-status" aria-live="polite">{mensagem}</p>}{erro && <p className="flow-error" role="alert">{erro}</p>}
  </main>;
}
