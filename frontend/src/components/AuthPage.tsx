import { useState } from "react";
import { cadastrar, entrar } from "../lib/api";

interface Props {
  onAuthenticated: () => Promise<void>;
}

export default function AuthPage({ onAuthenticated }: Props) {
  const [modo, setModo] = useState<"entrar" | "cadastrar">("entrar");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function enviar(event: React.FormEvent) {
    event.preventDefault();
    setErro("");
    if (modo === "cadastrar" && senha !== confirmacao) {
      setErro("As senhas precisam ser iguais.");
      return;
    }
    setCarregando(true);
    try {
      if (modo === "entrar") await entrar(email, senha);
      else await cadastrar(nome, email, senha, confirmacao);
      await onAuthenticated();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível autenticar.");
    } finally {
      setCarregando(false);
    }
  }

  return <main className="auth-page container">
    <div className="auth-card">
      <p className="eyebrow">Acesso ao Sarpia</p>
      <h1>{modo === "entrar" ? "Entre para ensaiar" : "Crie sua conta"}</h1>
      <form onSubmit={(event) => void enviar(event)}>
        {modo === "cadastrar" && <><label htmlFor="auth-nome">Nome</label><input id="auth-nome" value={nome} onChange={(event) => setNome(event.target.value)} autoComplete="name" required /></>}
        <label htmlFor="auth-email">E-mail</label>
        <input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
        <label htmlFor="auth-senha">Senha</label>
        <input id="auth-senha" type="password" value={senha} onChange={(event) => setSenha(event.target.value)} autoComplete={modo === "entrar" ? "current-password" : "new-password"} required />
        {modo === "cadastrar" && <><label htmlFor="auth-confirmacao">Confirme a senha</label><input id="auth-confirmacao" type="password" value={confirmacao} onChange={(event) => setConfirmacao(event.target.value)} autoComplete="new-password" required /></>}
        {erro && <p className="flow-error" role="alert">{erro}</p>}
        <button className="btn auth-submit" type="submit" disabled={carregando}>{carregando ? "Aguarde..." : modo === "entrar" ? "Entrar" : "Criar conta"}</button>
      </form>
      <button className="text-button auth-toggle" type="button" onClick={() => { setErro(""); setModo(modo === "entrar" ? "cadastrar" : "entrar"); }}>
        {modo === "entrar" ? "Ainda não tenho conta" : "Já tenho uma conta"}
      </button>
    </div>
  </main>;
}
