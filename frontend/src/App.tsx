import {
  Award,
  Briefcase,
  FileText,
  GraduationCap,
  PenLine,
  Presentation,
  Upload,
  type LucideIcon,
} from "lucide-react";

const passos: { icone: LucideIcon; num: string; titulo: string; descricao: string }[] = [
  {
    icone: Upload,
    num: "01",
    titulo: "Envie seus slides",
    descricao:
      "Carregue o PDF da sua apresentação. O Sarpia lê o texto dos slides e extrai os tópicos que você precisa cobrir.",
  },
  {
    icone: FileText,
    num: "02",
    titulo: "Escreva o ensaio",
    descricao:
      "Escreva como se estivesse apresentando de verdade. Quanto mais próximo da sua fala, melhor a correção.",
  },
  {
    icone: PenLine,
    num: "03",
    titulo: "Receba o feedback",
    descricao:
      "Veja o que ficou de fora, o que saiu errado, a ordem da apresentação e as perguntas que a banca pode fazer.",
  },
];

const publicos: { icone: LucideIcon; titulo: string; descricao: string }[] = [
  {
    icone: GraduationCap,
    titulo: "Defesas de TCC",
    descricao: "Não deixe nenhum slide importante de fora da sua fala.",
  },
  {
    icone: Briefcase,
    titulo: "Pitches",
    descricao: "Treine clareza e ordem sem perder o foco do investidor.",
  },
  {
    icone: Presentation,
    titulo: "Aulas e seminários",
    descricao: "Organize o conteúdo e antecipe as perguntas da plateia.",
  },
  {
    icone: Award,
    titulo: "Concursos",
    descricao: "Ensaie apresentações orais com base no material exigido.",
  },
];

export default function App() {
  return (
    <div className="shell">
      <header>
        <div className="container header-inner">
          <a className="logo-link" href="/" aria-label="Sarpia — página inicial">
            <img src="/logo.svg" alt="Sarpia" />
          </a>
          <nav>
            <a href="#como-funciona">Como funciona</a>
            <span className="tagline-mono">Simulador de Apresentação Revisado por IA</span>
          </nav>
        </div>
      </header>

      <main className="container">
        <div className="intro-stage">
          <div className="intro-copy">
            <p className="eyebrow">Simulador de Apresentação Revisado por IA</p>
            <h1>Ensaie antes de valer</h1>
            <p className="lede">
              Envie seus slides, escreva seu ensaio e receba uma correção na margem: o
              que ficou de fora, o que saiu errado e o que a banca provavelmente vai
              perguntar.
            </p>
            <div className="cta">
              <button className="btn" type="button">
                Começar um ensaio
              </button>
            </div>
          </div>

          <div className="raven-arrival" aria-hidden="true">
            <div className="raven-float">
              <img className="raven-figure" src="/corvo.svg" alt="" />
            </div>
          </div>
          <img className="raven-branch" src="/galho.svg" alt="" aria-hidden="true" />
          </div>

        <section id="como-funciona">
          <h2>Como funciona</h2>
          <div className="grid-steps">
            {passos.map(({ icone: Icone, num, titulo, descricao }) => (
              <article className="card" key={num}>
                <div className="card-head">
                  <Icone className="icon" aria-hidden />
                  <span className="step-num">{num}</span>
                </div>
                <h3>{titulo}</h3>
                <p className="desc">{descricao}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="exemplo">
          <h2>Exemplo de feedback</h2>
          <p className="section-sub">
            Veja como o Sarpia marca o seu ensaio como um professor com caneta vermelha.
          </p>
          <div className="grid-example">
            <div className="card">
              <p className="mono-label">cobertura do material</p>
              <p className="big-number">58%</p>
              <div className="bar">
                <div style={{ width: "58%" }} />
              </div>
              <p className="note">
                O Sarpia cruza o que você escreveu com os tópicos dos slides e mostra o
                que ficou de fora.
              </p>
            </div>
            <div className="stack">
              <article className="card card-sm">
                <p className="slide-num">slide 04</p>
                <p className="quote">
                  <span className="mark-slide">
                    PUT substitui o recurso inteiro; PATCH atualiza parcialmente.
                  </span>
                </p>
                <p className="said">Você mencionou apenas GET e POST.</p>
                <p className="correction">
                  <PenLine aria-hidden />
                  <span>
                    Inclua a diferença entre PUT e PATCH — a banca costuma cobrar esse
                    detalhe.
                  </span>
                </p>
              </article>
              <article className="card card-sm">
                <p className="question-text">
                  Qual a diferença entre PUT e PATCH na prática?
                </p>
                <p className="question-hint">dica: idempotência e atualização parcial</p>
              </article>
            </div>
          </div>
        </section>

        <section id="para-quem">
          <h2>Para quem</h2>
          <div className="grid-audiences">
            {publicos.map(({ icone: Icone, titulo, descricao }) => (
              <article className="card card-sm audience-card" key={titulo}>
                <Icone className="icon" aria-hidden />
                <div>
                  <h3>{titulo}</h3>
                  <p>{descricao}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="final-cta">
          <h2>Pronto para ensaiar?</h2>
          <p>Nada fica salvo: seu material vive só nesta sessão.</p>
          <div className="cta">
            <button className="btn" type="button">
              Começar agora
            </button>
          </div>
        </section>
      </main>

      <footer>
        <div className="container">
          <p>O Sarpia não substitui professor, orientador ou avaliador humano.</p>
        </div>
      </footer>
    </div>
  );
}