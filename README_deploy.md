# Deploy do Monitor B3 Buy-and-Hold no Railway (v8.7.1)

Projeto: Monitor conservador de ações B3 com alertas Telegram + análise buy-and-hold + swing excepcional.

## Pré-requisitos
- Conta gratuita no Railway.app[](https://railway.app)
- Repositório GitHub privado com o projeto (não publique token nem .env!)
- Arquivos na raiz:
  - monitor.py
  - analyze.py
  - railway.json
  - requirements.txt
  - .gitignore (com .env, __pycache__, *.pyc, *.png, etc.)

## Passo a passo (5 minutos)

1. **Crie o repositório no GitHub (se ainda não tiver)**
   - Nome sugerido: `monitor-b3-fabio` (privado!)
   - Não adicione README nem .gitignore agora — vamos subir tudo manualmente.

2. **Suba o código local para o GitHub**
   ```bash
   git init
   git add .
   git commit -m "v8.7.1 - deploy inicial Railway"
   git remote add origin https://github.com/SEU_USUARIO/monitor-b3-fabio.git
   git branch -M main
   git push -u origin main