import { useEffect, useRef, useState } from "react";
import type { AuthUser } from "../lib/api";

function iniciais(usuario: AuthUser): string {
  const nome = usuario.nome.trim() || usuario.email.split("@")[0] || "S";
  const partes = nome.split(/\s+/).filter(Boolean);
  return (partes.length > 1 ? `${partes[0][0]}${partes[partes.length - 1][0]}` : nome.slice(0, 2)).toUpperCase();
}

export function SiteHeader({ usuario, onLogout, onAuth, onHistory, onLogo, onNewPresentation, landing = false, historyActive = false }: { usuario?: AuthUser | null; onLogout?: () => Promise<void>; onAuth?: () => void; onHistory?: () => void; onLogo?: () => void; onNewPresentation?: () => void; landing?: boolean; historyActive?: boolean }) {
  const [contaAberta, setContaAberta] = useState(false);
  const contaRef = useRef<HTMLDivElement>(null);
  const contaBotaoRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!contaAberta) return;
    function fecharFora(event: PointerEvent) {
      if (!contaRef.current?.contains(event.target as Node)) setContaAberta(false);
    }
    function fecharEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setContaAberta(false);
        contaBotaoRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", fecharFora);
    document.addEventListener("keydown", fecharEscape);
    return () => {
      document.removeEventListener("pointerdown", fecharFora);
      document.removeEventListener("keydown", fecharEscape);
    };
  }, [contaAberta]);

  return <header><div className="container header-inner">
    <a className="logo-link" href="/" aria-label={usuario ? "Sarpia — minhas apresentações" : "Sarpia — página inicial"} onClick={(event) => { if (onLogo) { event.preventDefault(); onLogo(); } }}><img src="/logo.svg" alt="Sarpia" /></a>
    <nav>{landing && <a href="#como-funciona">Como funciona</a>}{usuario ? <><button className={`text-button header-history${historyActive ? " is-active" : ""}`} type="button" onClick={onHistory} aria-current={historyActive ? "page" : undefined}>Minhas apresentações</button>{onNewPresentation && <button className="btn header-new-presentation" type="button" onClick={onNewPresentation}>Nova apresentação</button>}<div className="account-control" ref={contaRef}><button className="account-trigger" type="button" ref={contaBotaoRef} aria-label={`Abrir conta de ${usuario.nome || usuario.email}`} aria-expanded={contaAberta} aria-controls="account-panel" onClick={() => setContaAberta((aberta) => !aberta)}><span className="account-avatar" aria-hidden="true">{iniciais(usuario)}</span><span className="user-name" title={usuario.nome || usuario.email}>{usuario.nome || usuario.email}</span><span className="account-chevron" aria-hidden="true">⌄</span></button>{contaAberta && <div className="account-panel" id="account-panel"><strong>{usuario.nome || "Sua conta"}</strong><span>{usuario.email}</span><button className="btn header-button" type="button" onClick={() => { setContaAberta(false); void onLogout?.(); }}>Sair</button></div>}</div></> : <button className="btn header-button" type="button" onClick={onAuth}>Entrar</button>}</nav>
  </div></header>;
}

export function SiteFooter() {
  return <footer><div className="container"><p>O Sarpia não substitui professor, orientador ou avaliador humano.</p></div></footer>;
}
