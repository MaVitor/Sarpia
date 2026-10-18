import { useState } from "react";
import { avaliarEnsaio, type PaginaTexto, type Topico, type FeedbackResponse } from "../lib/api";

interface Props {
  paginas: PaginaTexto[];
  topicos: Topico[];
  ensaio: string;
  onEnsaio: (texto: string) => void;
  onFeedback: (feedback: FeedbackResponse | null) => void;
  onBack: () => void;
}

export default function EssayPage({ paginas, topicos, ensaio, onEnsaio, onFeedback, onBack }: Props) {
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  async function avaliar() {
    if (ensaio.trim().length < 20) { setErro("O ensaio precisa conter pelo menos 20 caracteres."); return; }
    if (ensaio.length > 30000) { setErro("O ensaio excede o limite de 30.000 caracteres."); return; }
    setErro(""); setCarregando(true);
    try { onFeedback(await avaliarEnsaio(paginas, ensaio)); }
    catch (e) { setErro(e instanceof Error ? e.message : "Não foi possível avaliar o ensaio."); }
    finally { setCarregando(false); }
  }
  return <main className="flow-page flow-essay" tabIndex={-1}>
    <p className="flow-kicker">Etapa 2 de 3</p><h1 className="flow-title" tabIndex={-1}>Agora, ensaie</h1>
    <p className="flow-lede">Consulte o material, escreva sua apresentação e envie quando estiver pronto.</p>
    <div className="essay-grid"><aside className="flow-card reference-panel"><h2>Material e tópicos</h2><div className="reference-pages">{paginas.map((p) => <details key={p.numero}><summary>{p.numero === 1 && paginas.length === 1 ? "Roteiro" : `Página ${p.numero}`}</summary><pre>{p.texto}</pre></details>)}</div><ul className="topic-list compact">{topicos.map((t) => <li key={`${t.slide}-${t.titulo}`}><strong>{t.titulo}</strong><span>{t.slide === 1 && paginas.length === 1 ? "Roteiro" : `Página ${t.slide}`}</span></li>)}</ul></aside>
      <section className="flow-card essay-editor"><label htmlFor="ensaio">Seu ensaio</label><textarea id="ensaio" value={ensaio} onChange={(e) => { onEnsaio(e.target.value); onFeedback(null); }} rows={22} maxLength={30000} /><div className="essay-count" aria-live="polite">{ensaio.trim() ? ensaio.trim().split(/\s+/).length : 0} palavras · {ensaio.length.toLocaleString("pt-BR")} / 30.000 caracteres</div>{erro && <p className="flow-error" role="alert">{erro}</p>}<div className="flow-actions"><button className="text-button" type="button" onClick={onBack} disabled={carregando}>Voltar ao material</button><button className="btn" type="button" onClick={() => void avaliar()} disabled={carregando}>{carregando ? "Analisando o ensaio..." : "Avaliar meu ensaio"}</button></div></section></div>
  </main>;
}
