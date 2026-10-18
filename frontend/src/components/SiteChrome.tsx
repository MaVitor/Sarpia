export function SiteHeader() {
  return <header><div className="container header-inner">
    <a className="logo-link" href="/" aria-label="Sarpia — página inicial"><img src="/logo.svg" alt="Sarpia" /></a>
    <nav><a href="#como-funciona">Como funciona</a><span className="tagline-mono">Simulador de Apresentação Revisado por IA</span></nav>
  </div></header>;
}

export function SiteFooter() {
  return <footer><div className="container"><p>O Sarpia não substitui professor, orientador ou avaliador humano.</p></div></footer>;
}
