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
- **Backend:** Django + Django REST Framework (stateless, sem banco no MVP)
- **IA:** Gemini API com rotação de chaves (KeyPool) e structured output
- **PDF:** PyMuPDF
- **Futuro:** PostgreSQL (Django ORM + auth já prontos para essa fase)

## Estrutura do projeto

```
Sarpia/
├── backend/
│   ├── config/                # Projeto Django (settings, urls, wsgi/asgi)
│   ├── api/                   # App Django (sem models no MVP — stateless)
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

> O aviso "you have unapplied database migrations" pode ser ignorado no MVP: não usamos banco de dados nesta fase.

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

## Roadmap (resumo)

- **M1** — Análise de ensaio em texto colado
- **M2** — Upload de PDF textual
- **M3** — Feedback ancorado por slide + perguntas de banca
- **M4** — Deploy (Vercel + Render/Railway)
- **Pós-validação** — áudio, métricas de fala, OCR, contas e histórico

Detalhes em `docs/ROADMAP.md`.

## Privacidade

O backend é **stateless**: nada é salvo em banco de dados no MVP. Arquivos e ensaios trafegam apenas para gerar o feedback. Atenção: no free tier da API Gemini, o Google pode usar prompts e respostas para melhorar seus modelos — não envie materiais confidenciais nesta fase. As chaves da API ficam somente no backend, em variáveis de ambiente, nunca no frontend ou no Git.
