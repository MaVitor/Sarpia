import { useState } from "react";
import { verificarSaude } from "./lib/api";

export default function App() {
  const [statusApi, setStatusApi] = useState("não verificado");
  const [verificando, setVerificando] = useState(false);

  async function checarApi() {
    setVerificando(true);
    try {
      await verificarSaude();
      setStatusApi("online ✅");
    } catch {
      setStatusApi("offline ❌ (o backend está rodando?)");
    } finally {
      setVerificando(false);
    }
  }

  return (
    <main className="container">
      <h1>Sarpia</h1>
      <p className="tagline">Simulador de Apresentação Revisado Por IA</p>
      <p className="aviso">
        MVP em desenvolvimento — o Sarpia não substitui professor, orientador ou
        avaliador humano.
      </p>

      <section className="etapas">
        <div className="card">
          <h2>1. Envie o material</h2>
          <p>PDF com texto selecionável (em breve).</p>
        </div>
        <div className="card">
          <h2>2. Ensaie por texto</h2>
          <p>Escreva sua explicação como se estivesse apresentando (em breve).</p>
        </div>
        <div className="card">
          <h2>3. Receba o feedback</h2>
          <p>Cobertura, erros, lacunas e perguntas de banca (em breve).</p>
        </div>
      </section>

      <button onClick={checarApi} disabled={verificando}>
        {verificando ? "Verificando..." : "Testar conexão com a API"}
      </button>
      <p>Status da API: {statusApi}</p>
    </main>
  );
}
