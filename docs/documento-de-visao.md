# Documento de Visão — Sarpia

**Simulador de Apresentação Revisado por IA**

Autor: Mateus Vitor
Orientador: Andre Almeida
Curso: Análise e Desenvolvimento de Sistemas — IFRN

## 1. Introdução

Este documento apresenta a visão geral do projeto Sarpia, desenvolvido como Trabalho de Conclusão de Curso. A ideia é registrar aqui o problema que motivou o projeto, quem será beneficiado, o que o sistema vai fazer e — igualmente importante — o que ele não vai fazer nesta primeira versão. O objetivo é alinhar as expectativas entre autor e orientador e servir de referência ao longo do desenvolvimento.

## 2. O problema

Quem precisa apresentar algo importante (uma defesa de TCC, um pitch para um cliente, o resultado de um projeto numa reunião) quase sempre ensaia. O problema é que ensaiar sozinho tem um limite claro: a pessoa consegue treinar o tom de voz e o tempo, mas não sabe dizer se esqueceu um tópico dos slides, se errou algum conceito ou se explicou algo de um jeito confuso.

A alternativa seria pedir para alguém ouvir o ensaio. Só que essa pessoa precisaria conhecer o conteúdo para dar um feedback útil, e nem sempre existe alguém assim disponível na véspera da apresentação, que é justamente quando o ensaio acontece.

Também existe a problemática envolvendo pessoas ansiosas 

Ferramentas de oratória já existentes focam em como a pessoa fala: ritmo, pausas, vícios de linguagem. O que falta é avaliar o que foi dito, comparando a fala com o material que embasava a apresentação.

## 3. A solução proposta

O Sarpia é uma plataforma web que funciona como esse "amigo que conhece o assunto". O fluxo é simples:

1. O usuário envia os slides da apresentação em PDF ou um roteiro.
2. O sistema lê o material e identifica os tópicos principais.
3. O usuário escreve seu ensaio como se estivesse apresentando.
4. Uma inteligência artificial compara o ensaio com o material e devolve um feedback indicando o que foi coberto corretamente, o que ficou de fora, o que foi explicado errado e o que foi afirmado sem base no material.
5. O sistema ainda sugere perguntas que uma banca, um cliente ou uma plateia poderiam fazer, para o usuário se preparar melhor.
6. O usuário pode ensaiar de novo e comparar a evolução.

O feedback é sempre fundamentado no material enviado. O sistema não atribui nota e não substitui professor, orientador ou avaliador humano. É um auxílio de preparação, não uma avaliação oficial.

## 4. Público-alvo

- Estudantes que precisam apresentar trabalhos e defesas acadêmicas;
- Mestrandos e doutorandos ensaiando qualificação e defesa;
- Profissionais que vão apresentar projetos em reuniões;
- Equipes comerciais treinando pitches para clientes;
- Qualquer pessoa que queira ensaiar uma conversa profissional importante.

O uso não exige conhecimento técnico: quem sabe enviar um PDF e escrever um texto consegue usar a plataforma.

## 5. Escopo do MVP

Para validar a ideia sem perder tempo, a primeira versão cobre apenas o essencial:

- Upload de PDF com texto selecionável (limite de páginas definido);
- Identificação automática dos tópicos do material;
- Ensaio em texto, comparado com os slides;
- Feedback apontando tópicos cobertos, omitidos, erros e afirmações sem base no material, com indicação do slide correspondente;
- Sugestão de perguntas de banca/cliente baseadas no conteúdo;
- Opção de o usuário usar a própria chave de API da IA, se preferir.

**Ficam de fora desta versão:** login e cadastro, banco de dados, histórico de tentativas, ensaio por áudio, análise de voz e vícios de linguagem, OCR para PDFs escaneados e qualquer análise de vídeo ou postura. Essas funcionalidades estão mapeadas como evoluções futuras, caso a validação do MVP confirme que a ideia tem valor.

## 6. Evoluções planejadas

Quando o MVP confirmar a hipótese, as próximas etapas previstas são:

- Ensaio por áudio com transcrição automática;
- Métricas de fala: tempo total, palavras por minuto, pausas e ritmo;
- Detecção de vícios de linguagem ("tipo", "né", "basicamente");
- OCR no servidor para PDFs escaneados;
- Simulação de banca ou cliente com perguntas de acompanhamento;
- Login, histórico de tentativas e painel de evolução.

## 7. Tecnologias previstas

- **Frontend:** React com TypeScript;
- **Backend:** Django com Django REST Framework;
- **Inteligência artificial:** API Gemini (Google), com alternância automática entre chaves quando o limite gratuito de uma delas é atingido;
- **Leitura de PDF:** PyMuPDF;
- **Banco de dados:** PostgreSQL.

## 8. Riscos e limitações

- **Limite das chaves gratuitas da IA:** contornado com a alternância entre chaves e, em produção, com a possibilidade do usuário usar a própria chave;
- **Respostas imprecisas da IA:** o feedback é construído para sempre citar o trecho do material que embasa cada apontamento, e o sistema é orientado a não inventar informações;
- **Privacidade:** na primeira versão nada é armazenado no servidor; o material enviado existe apenas durante o uso. No nível gratuito da API do Gemini, os dados podem ser usados pelo Google para melhorar seus modelos, o que será informado ao usuário;
- **Expectativa do usuário:** o produto deixa claro, em texto visível, que não substitui a orientação de um avaliador humano.
