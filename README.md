# Sarpia

**Simulador de Apresentação Revisado Por IA**

Plataforma web para treinar apresentações, defesas acadêmicas, pitches e reuniões importantes. Você envia seus slides (PDF) ou roteiro, ensaia por texto, e a IA devolve um feedback fundamentado no **seu** material: tópicos esquecidos, erros de conteúdo, trechos confusos e perguntas que uma banca, cliente ou público poderiam fazer.

> Projeto de TCC — Análise e Desenvolvimento de Sistemas (IFRN). Autor: Mateus Vitor.

## Diferencial

Ferramentas de oratória analisam ritmo, clareza e vícios de fala. O Sarpia avalia também **o que** você disse: compara o ensaio com os próprios slides e aponta omissões, erros e informações não sustentadas pelo material.

## Aviso importante

O Sarpia **não atribui nota oficial nem substitui** professor, orientador, coach ou avaliador humano. O feedback é gerado por IA e fundamentado exclusivamente no material enviado.

## Stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** Django + Django REST Framework + django-allauth (sessão, usuários e histórico persistente)
- **IA:** Gemini API com rotação de chaves (KeyPool) e structured output
- **PDF:** PyMuPDF
- **Banco:** SQLite explícito por padrão no desenvolvimento; PostgreSQL quando as variáveis `POSTGRES_*` forem preenchidas

## Estrutura do projeto

```
Sarpia/
├── backend/
│   ├── config/                # Projeto Django (settings, urls, wsgi/asgi)
│   ├── api/                   # App Django (análise e autenticação)
│   │   ├── schemas.py         # Contratos Pydantic = response_schema do Gemini
│   │   ├── serializers.py     # Validação das requisições (DRF)
│   │   ├── views.py           # Endpoints
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── services/          # pdf.py, gemini.py (KeyPool), prompts.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Vite + React + TypeScript
│   ├── src/lib/api.ts         # Cliente HTTP tipado
│   └── src/App.tsx            # Página placeholder com teste de conexão
├── docs/
│   ├── PLANO_TECNICO.md       # Arquitetura, endpoints, KeyPool, riscos
│   ├── PROMPTS.md             # Templates de prompt e caso de teste
│   └── ROADMAP.md             # Fases do MVP e backlog pós-validação
└── README.md
```

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- Uma ou mais chaves gratuitas da API Gemini (Google AI Studio), idealmente de projetos diferentes

## Como rodar (desenvolvimento)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env — preencha GEMINI_API_KEYS
python manage.py runserver
```

API em http://localhost:8000 — a API navegável do DRF responde nos próprios endpoints (ex.: http://localhost:8000/api/saude/).

Após configurar a autenticação, aplique as migrations normalmente:

```bash
python manage.py migrate
```

Para usar PostgreSQL, preencha no `.env` as cinco variáveis `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT`.
Quando qualquer uma delas for preenchida, todas passam a ser obrigatórias e o
backend não faz fallback silencioso para SQLite. Exemplo de criação local:

```sql
CREATE USER sarpia WITH PASSWORD 'troque-esta-senha';
CREATE DATABASE sarpia OWNER sarpia;
```

Depois, execute `python manage.py migrate`. O banco PostgreSQL é independente
do SQLite: contas e sessões existentes no `db.sqlite3` não são transferidas
automaticamente.

O cadastro envia uma mensagem de confirmação para o backend de console quando
`ACCOUNT_EMAIL_VERIFICATION=optional`; a conta pode entrar imediatamente, mas
o e-mail não foi entregue. Em produção, configure um backend SMTP/SES e
`ACCOUNT_EMAIL_VERIFICATION=mandatory` se a confirmação for obrigatória.

As rotas de sessão são `/api/auth/csrf/`, `/api/auth/session/`,
`/api/auth/login/`, `/api/auth/signup/` e `/api/auth/logout/`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # Windows: copy .env.example .env
npm run dev
```

App em http://localhost:5173 — use o botão "Testar conexão com a API".

### Testes

```bash
cd backend
python manage.py test
```

### Histórico

Apresentações preparadas, páginas textuais, referências, ensaios e feedbacks
validados são armazenados por usuário. O histórico permite retomar uma
apresentação com a referência original e consultar ou excluir tentativas.
Uma nova apresentação/referência não sobrescreve avaliações anteriores.
O PDF binário não é armazenado nesta etapa. Não há histórico, materiais ou
feedbacks no `localStorage` ou `sessionStorage`.

## Roadmap (resumo)

- **M1** — Análise de ensaio em texto colado
- **M2** — Upload de PDF textual
- **M3** — Feedback ancorado por slide + perguntas de banca
- **M4** — Deploy (Vercel + Render/Railway)
- **Pós-validação** — áudio, métricas de fala, OCR, contas e histórico

Detalhes em `docs/ROADMAP.md`.

## Privacidade

Usuários, e-mails de confirmação, sessões e o histórico de apresentações são
persistidos pelo Django/allauth e pelos modelos da API. Materiais textuais,
ensaios e feedbacks ficam armazenados na conta até a exclusão da apresentação.
Atenção: no free tier da API Gemini, o Google pode usar prompts e respostas
para melhorar seus modelos — não envie materiais confidenciais nesta fase. As
chaves da API ficam somente no backend, em variáveis de ambiente, nunca no
frontend ou no Git.
