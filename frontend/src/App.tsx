import { useEffect, useState } from "react";
import LandingPage from "./components/LandingPage";
import AuthPage from "./components/AuthPage";
import MaterialPage from "./components/MaterialPage";
import EssayPage from "./components/EssayPage";
import FeedbackPage from "./components/FeedbackPage";
import HistoryPage from "./components/HistoryPage";
import { SiteFooter, SiteHeader } from "./components/SiteChrome";
import { obterSessao, sair, type AuthUser, type ContextoApresentacao, type FeedbackResponse, type PaginaTexto, type ReferenciaTopicos } from "./lib/api";
import ConfirmDialog from "./components/ConfirmDialog";

type Tela = "inicio" | "auth" | "historico" | "material" | "ensaio" | "feedback";

export default function App() {
  const [tela, setTela] = useState<Tela>("inicio");
  const [usuario, setUsuario] = useState<AuthUser | null>(null);
  const [sessaoCarregando, setSessaoCarregando] = useState(true);
  const [paginas, setPaginas] = useState<PaginaTexto[]>([]);
  const [nomeMaterial, setNomeMaterial] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [referencia, setReferencia] = useState<ReferenciaTopicos | null>(null);
  const [presentationId, setPresentationId] = useState<string | null>(null);
  const [modoMaterial, setModoMaterial] = useState<"pdf" | "roteiro">("pdf");
  const [ensaio, setEnsaio] = useState("");
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);
  const [contexto, setContexto] = useState<ContextoApresentacao>("geral");
  const [acaoPendente, setAcaoPendente] = useState<(() => void) | null>(null);

  async function atualizarSessao() {
    const sessao = await obterSessao();
    setUsuario(sessao.usuario);
    return sessao;
  }
  useEffect(() => {
    void atualizarSessao().then((sessao) => {
      if (sessao.usuario) setTela("historico");
    }).finally(() => setSessaoCarregando(false));
  }, []);

  useEffect(() => {
    if (tela !== "inicio") {
      document.querySelector<HTMLElement>(".flow-title")?.focus();
    }
  }, [tela]);
  useEffect(() => {
    function protegerSaida(event: BeforeUnloadEvent) {
      if (!temRiscoDePerda()) return;
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", protegerSaida);
    return () => window.removeEventListener("beforeunload", protegerSaida);
  });
  function temRiscoDePerda() {
    return (!presentationId && paginas.length > 0) || (ensaio.trim().length > 0 && !feedback);
  }
  function confirmarSaidaRascunho(callback: () => void) {
    if (!temRiscoDePerda()) {
      callback();
      return;
    }
    setAcaoPendente(() => callback);
  }
  function abrirHistorico() {
    confirmarSaidaRascunho(() => setTela("historico"));
  }
  function novaApresentacao() {
    confirmarSaidaRascunho(() => {
      setPaginas([]); setReferencia(null); setPresentationId(null); setFeedback(null); setEnsaio(""); setNomeMaterial(""); setAviso(null); setTela("material");
    });
  }
  function iniciar() { if (usuario) novaApresentacao(); else setTela("auth"); }
  async function logout() {
    await sair();
    setUsuario(null); setPaginas([]); setReferencia(null); setPresentationId(null); setFeedback(null); setEnsaio(""); setNomeMaterial(""); setAviso(null); setTela("inicio");
  }
  function materialAtualizado(novasPaginas: PaginaTexto[], nome: string, novoAviso: string | null) {
    setPaginas(novasPaginas); setNomeMaterial(nome); setAviso(novoAviso); setReferencia(null); setPresentationId(null); setFeedback(null);
  }
  function trocarMaterial() {
    confirmarSaidaRascunho(() => {
      setPaginas([]); setReferencia(null); setPresentationId(null); setFeedback(null); setEnsaio(""); setTela("material");
    });
  }
  if (sessaoCarregando) return <div className="shell" aria-busy="true"><main className="container auth-loading">Consultando sua sessão...</main></div>;
  return <>
    {tela === "inicio" && <LandingPage onStart={iniciar} onAuth={() => setTela("auth")} onHistory={abrirHistorico} onLogo={abrirHistorico} usuario={usuario} />}
    {tela === "auth" && <div className="shell"><SiteHeader onAuth={() => setTela("auth")} /><AuthPage onAuthenticated={async () => { await atualizarSessao(); setTela("historico"); }} /></div>}
    {tela === "historico" && <div className="shell"><SiteHeader usuario={usuario} onLogout={logout} onHistory={abrirHistorico} onLogo={abrirHistorico} onNewPresentation={novaApresentacao} historyActive /><HistoryPage onNewPresentation={novaApresentacao} onResume={(presentation) => { setPaginas(presentation.paginas); setReferencia(presentation.referencia); setPresentationId(presentation.id); setNomeMaterial(presentation.titulo); setContexto(presentation.contexto ?? presentation.referencia.contexto ?? "geral"); setFeedback(null); setEnsaio(""); setTela("ensaio"); }} onFeedback={(presentation, attempt) => { setPaginas(presentation.paginas); setReferencia(presentation.referencia); setPresentationId(presentation.id); setNomeMaterial(presentation.titulo); setContexto(presentation.contexto ?? presentation.referencia.contexto ?? "geral"); setFeedback(attempt.feedback); setEnsaio(attempt.ensaio); setTela("feedback"); }} /></div>}
    {tela !== "inicio" && tela !== "auth" && tela !== "historico" && <div className={`shell ${tela === "feedback" ? "flow-feedback-shell" : ""}`}><SiteHeader usuario={usuario} onLogout={logout} onHistory={abrirHistorico} onLogo={abrirHistorico} onNewPresentation={novaApresentacao} />
      {tela === "material" && <MaterialPage paginas={paginas} referencia={referencia} contexto={contexto} onContexto={(novoContexto) => { setContexto(novoContexto); setReferencia(null); setPresentationId(null); setFeedback(null); }} onMaterial={(novasPaginas, nome, novoAviso, modo) => { materialAtualizado(novasPaginas, nome, novoAviso); setModoMaterial(modo); }} onReferencia={setReferencia} onPresentation={setPresentationId} onContinue={() => setTela("ensaio")} />}
      {tela === "ensaio" && <EssayPage paginas={paginas} presentationId={presentationId} referencia={referencia} contexto={contexto} modo={modoMaterial} ensaio={ensaio} onEnsaio={setEnsaio} onFeedback={(novoFeedback) => { setFeedback(novoFeedback); if (novoFeedback) setTela("feedback"); }} onBack={() => setTela("material")} />}
      {tela === "feedback" && feedback && <FeedbackPage feedback={feedback} materialNome={nomeMaterial} contexto={contexto} onReview={() => setTela("ensaio")} onChangeMaterial={trocarMaterial} onHome={abrirHistorico} />}
      <SiteFooter />
    </div>}
    {feedback && tela === "ensaio" && <button className="sr-only" type="button" onClick={() => setTela("feedback")}>Ver feedback</button>}
    {feedback && tela === "ensaio" && <div className="flow-feedback-ready"><button className="btn" type="button" onClick={() => setTela("feedback")}>Ver feedback</button></div>}
    {nomeMaterial && aviso && tela === "ensaio" && <span className="sr-only">{aviso}</span>}
    <ConfirmDialog open={acaoPendente !== null} title="Sair desta etapa?" description="As alterações ainda não salvas nesta etapa serão descartadas. O material e os feedbacks que já foram salvos na sua conta não serão apagados." onCancel={() => setAcaoPendente(null)} onConfirm={() => { const acao = acaoPendente; setAcaoPendente(null); acao?.(); }} />
  </>;
}
