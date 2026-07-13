# Organizador Financeiro (Flask)

App simples em Flask + SQLite para acompanhar entradas e gastos por categoria.

## Rodar local

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra http://localhost:5000

## Deploy no Render (gratuito)

1. Suba o projeto para o GitHub.
2. Em https://render.com clique em **New +** > **Web Service**.
3. Conecte o repositório.
4. Configurações:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plan: Free
5. Clique em **Create Web Service**. O Render vai gerar a URL pública.

> Dica: no Free do Render o disco é efêmero, então o SQLite pode ser
> reiniciado a cada deploy. Para persistir, ative um **Disk** montado em
> `/var/data` (o app já detecta automaticamente essa pasta).

## Deploy no Railway

1. https://railway.app > **New Project** > **Deploy from GitHub Repo**.
2. Ele detecta o `Procfile` e sobe sozinho.

## Estrutura

```
financas/
├── app.py             # aplicação Flask
├── requirements.txt   # dependências
├── Procfile           # comando de start em produção
├── runtime.txt        # versão do Python
├── render.yaml        # config opcional do Render
├── .gitignore
└── README.md
```
