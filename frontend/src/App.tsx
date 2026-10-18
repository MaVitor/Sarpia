import { useEffect, useState } from "react";
import LandingPage from "./components/LandingPage";
import MaterialPage from "./components/MaterialPage";
import EssayPage from "./components/EssayPage";
import FeedbackPage from "./components/FeedbackPage";
import { SiteFooter, SiteHeader } from "./components/SiteChrome";
import type { FeedbackResponse, PaginaTexto, Topico } from "./lib/api";

type Tela = "inicio" | "material" | "ensaio" | "feedback";

export default function App() {
  const [tela, setTela] = useState<Tela>("inicio");
  const [paginas, setPaginas] = useState<PaginaTexto[]>([]);
  const [nomeMaterial, setNomeMaterial] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [topicos, setTopicos] = useState<Topico[]>([]);
  const [ensaio, setEnsaio] = useState("");
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);

  useEffect(() => {
    if (tela !== "inicio") {
      document.querySelector<HTMLElement>(".flow-title")?.focus();
    }
  }, [tela]);
  function iniciar() { setTela("material"); }
  function materialAtualizado(novasPaginas: PaginaTexto[], nome: string, novoAviso: string | null) {
    setPaginas(novasPaginas); setNomeMaterial(nome); setAviso(novoAviso); setTopicos([]); setFeedback(null);
  }
  function confirmar(descricao: string): boolean { return window.confirm(descricao); }
  function trocarMaterial() {
    if (confirmar("Trocar o material e descartar o feedback atual?")) {
      setPaginas([]); setTopicos([]); setFeedback(null); setEnsaio(""); setTela("material");
    }
  }
  function voltarInicio() {
    if (confirmar("Voltar ao início e descartar o trabalho desta sessão?")) {
      setPaginas([]); setTopicos([]); setFeedback(null); setEnsaio(""); setTela("inicio");
    }
  }
  return <>
    {tela === "inicio" && <LandingPage onStart={iniciar} />}
    {tela !== "inicio" && <div className={`shell ${tela === "feedback" ? "flow-feedback-shell" : ""}`}><SiteHeader />
      {tela === "material" && <MaterialPage paginas={paginas} topicos={topicos} onMaterial={materialAtualizado} onTopicos={setTopicos} onContinue={() => setTela("ensaio")} />}
      {tela === "ensaio" && <EssayPage paginas={paginas} topicos={topicos} ensaio={ensaio} onEnsaio={setEnsaio} onFeedback={(novoFeedback) => { setFeedback(novoFeedback); if (novoFeedback) setTela("feedback"); }} onBack={() => setTela("material")} />}
      {tela === "feedback" && feedback && <FeedbackPage feedback={feedback} materialNome={nomeMaterial} onReview={() => setTela("ensaio")} onChangeMaterial={trocarMaterial} onHome={voltarInicio} />}
      <SiteFooter />
    </div>}
    {feedback && tela === "ensaio" && <button className="sr-only" type="button" onClick={() => setTela("feedback")}>Ver feedback</button>}
    {feedback && tela === "ensaio" && <div className="flow-feedback-ready"><button className="btn" type="button" onClick={() => setTela("feedback")}>Ver feedback</button></div>}
    {nomeMaterial && aviso && tela === "ensaio" && <span className="sr-only">{aviso}</span>}
  </>;
}
