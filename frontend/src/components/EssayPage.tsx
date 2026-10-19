import { useEffect, useRef, useState } from "react";
import { avaliarEnsaio, type PaginaTexto, type ReferenciaTopicos, type FeedbackResponse } from "../lib/api";

interface Props {
  paginas: PaginaTexto[];
  referencia: ReferenciaTopicos | null;
  modo: "pdf" | "roteiro";
  ensaio: string;
  onEnsaio: (texto: string) => void;
  onFeedback: (feedback: FeedbackResponse | null) => void;
  onBack: () => void;
}

export default function EssayPage({ paginas, referencia, modo, ensaio, onEnsaio, onFeedback, onBack }: Props) {
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const avaliacaoAtual = useRef<AbortController | null>(null);
  useEffect(() => () => avaliacaoAtual.current?.abort(), []);
  async function avaliar() {
    if (ensaio.trim().length < 20) { setErro("O ensaio precisa conter pelo menos 20 caracteres."); return; }
    if (ensaio.length > 30000) { setErro("O ensaio excede o limite de 30.000 caracteres."); return; }
    if (!referencia) { setErro("Prepare os tópicos do material antes de avaliar o ensaio."); return; }
    avaliacaoAtual.current?.abort();
    const controlador = new AbortController();
    avaliacaoAtual.current = controlador;
    setErro(""); setCarregando(true);
    try { const resultado = await avaliarEnsaio(paginas, ensaio, referencia, modo, controlador.signal); onFeedback(resultado); }
    catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e instanceof Error ? e.message : "Não foi possível avaliar o ensaio."); }
    finally { setCarregando(false); }
  }
  return <main className="flow-page flow-essay" tabIndex={-1}>
    <p className="flow-kicker">Etapa 2 de 3</p><h1 className="flow-title" tabIndex={-1}>Agora, ensaie</h1>
    <p className="flow-lede">Consulte o material, escreva sua apresentação e envie quando estiver pronto.</p>
    <div className="essay-grid"><aside className="flow-card reference-panel"><h2>Material e tópicos</h2><div className="reference-pages">{paginas.map((p) => <details key={p.numero}><summary>{p.numero === 1 && paginas.length === 1 ? "Roteiro" : `Página ${p.numero}`}</summary><pre>{p.texto}</pre></details>)}</div><ul className="topic-list compact">{referencia?.topicos.map((t) => <li key={t.id}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span></li>)}</ul>{referencia?.topicos_complementares.length ? <><h3>Complementares</h3><ul className="topic-list compact">{referencia.topicos_complementares.map((t) => <li key={t.id}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span></li>)}</ul></> : null}</aside>
      <section className="flow-card essay-editor"><label htmlFor="ensaio">Seu ensaio</label><textarea id="ensaio" value={ensaio} onChange={(e) => { onEnsaio(e.target.value); onFeedback(null); }} rows={22} maxLength={30000} /><div className="essay-count" aria-live="polite">{ensaio.trim() ? ensaio.trim().split(/\s+/).length : 0} palavras · {ensaio.length.toLocaleString("pt-BR")} / 30.000 caracteres</div>{erro && <p className="flow-error" role="alert">{erro}</p>}<div className="flow-actions"><button className="text-button" type="button" onClick={onBack} disabled={carregando}>Voltar ao material</button><button className="btn" type="button" onClick={() => void avaliar()} disabled={carregando}>{carregando ? "Analisando o ensaio..." : "Avaliar meu ensaio"}</button></div></section></div>
  </main>;
}
