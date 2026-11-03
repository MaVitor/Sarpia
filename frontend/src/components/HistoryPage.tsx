import { useEffect, useState } from "react";
import {
  excluirApresentacao,
  listarApresentacoes,
  obterApresentacao,
  type HistoryAttempt,
  type PresentationDetail,
  type PresentationSummary,
} from "../lib/api";
import ConfirmDialog from "./ConfirmDialog";

function formatarTentativas(quantidade: number): string {
  return `${quantidade} ${quantidade === 1 ? "tentativa" : "tentativas"}`;
}

interface Props {
  onResume: (presentation: PresentationDetail) => void;
  onFeedback: (presentation: PresentationDetail, attempt: HistoryAttempt) => void;
  onNewPresentation: () => void;
}

export default function HistoryPage({ onResume, onFeedback, onNewPresentation }: Props) {
  const [items, setItems] = useState<PresentationSummary[]>([]);
  const [selected, setSelected] = useState<PresentationDetail | null>(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [exclusaoPendente, setExclusaoPendente] = useState<string | null>(null);
  const [exclusaoProcessando, setExclusaoProcessando] = useState(false);
  const [exclusaoErro, setExclusaoErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const resposta = await listarApresentacoes();
      setItems(resposta.resultados);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível carregar o histórico.");
    } finally {
      setCarregando(false);
    }
  }
  useEffect(() => { void carregar(); }, []);

  async function abrir(id: string) {
    try {
      setSelected(await obterApresentacao(id));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível abrir a apresentação.");
    }
  }
  async function confirmarExclusao() {
    if (!exclusaoPendente || exclusaoProcessando) return;
    const id = exclusaoPendente;
    setExclusaoProcessando(true);
    setExclusaoErro("");
    try {
      await excluirApresentacao(id);
      setExclusaoPendente(null);
      setSelected(null);
      await carregar();
    } catch (e) {
      setExclusaoErro(e instanceof Error ? e.message : "Não foi possível excluir a apresentação.");
    } finally {
      setExclusaoProcessando(false);
    }
  }

  return <main className="flow-page history-page" tabIndex={-1}>
    <h1 className="flow-title" tabIndex={-1}>Minhas apresentações</h1>
    <p className="flow-lede">Retome seus ensaios e consulte os feedbacks das apresentações salvas.</p>
    {erro && <p className="flow-error" role="alert">{erro}</p>}
    {carregando ? <p className="flow-status">Carregando histórico...</p> : !items.length ? <section className="flow-card empty-history"><div className="empty-history-content"><h2>Você ainda não tem apresentações salvas</h2><p>Adicione um material para preparar seu primeiro ensaio.</p><button className="btn" type="button" onClick={onNewPresentation}>Nova apresentação</button></div></section> : <><div className="history-toolbar"><p>Você pode retomar uma apresentação ou consultar um feedback anterior.</p><button className="btn" type="button" onClick={onNewPresentation}>Nova apresentação</button></div><div className="history-list">{items.map((item) => <article className="flow-card history-item" key={item.id}><div className="history-item-copy"><h2 title={item.titulo}>{item.titulo}</h2><p>{new Date(item.atualizada_em).toLocaleString("pt-BR")} · {formatarTentativas(item.quantidade_tentativas)}</p></div><div className="history-actions"><button className="history-action-button history-open-button" type="button" onClick={() => void abrir(item.id)}>Abrir</button><button className="history-action-button history-delete-button" type="button" onClick={() => setExclusaoPendente(item.id)}>Excluir</button></div></article>)}</div></>}
    {selected && <section className="flow-card history-detail"><div className="history-detail-heading"><div><h2>{selected.titulo}</h2><p>{selected.paginas.length} página(s) · referência {selected.referencia_versao}</p></div><button className="btn" type="button" onClick={() => onResume(selected)}>Novo ensaio</button></div><h3>Tentativas anteriores</h3>{selected.tentativas.length ? <ol className="attempt-list">{selected.tentativas.map((attempt) => <li key={attempt.id}><span>{new Date(attempt.criada_em).toLocaleString("pt-BR")}</span><button className="text-button" type="button" onClick={() => onFeedback(selected, attempt)}>Consultar feedback</button></li>)}</ol> : <p className="empty-state">Ainda não há tentativas para esta apresentação.</p>}</section>}
    <ConfirmDialog open={exclusaoPendente !== null} title="Excluir apresentação?" description="A apresentação e todas as tentativas salvas serão excluídas." warning="Essa ação não pode ser desfeita." cancelLabel="Cancelar" confirmLabel="Excluir apresentação" confirmVariant="destructive" busy={exclusaoProcessando} busyLabel="Excluindo…" error={exclusaoErro} onCancel={() => { if (!exclusaoProcessando) { setExclusaoPendente(null); setExclusaoErro(""); } }} onConfirm={() => void confirmarExclusao()} />
  </main>;
}
