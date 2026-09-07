import os
import pg8000.native
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Controle Jurídico")

# Configuração de templates e arquivos estáticos (se existirem)
templates = Jinja2Templates(directory="templates")
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Função de conexão segura com o PostgreSQL
def get_db_connection():
    return pg8000.native.Connection(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME"),
        ssl_context=True
    )

# ------------------------------------------------------------------
# ROTA 1: Tela de Entrada (Home / Landing Page)
# ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if os.path.exists("templates/index.html"):
        return templates.TemplateResponse("index.html", {"request": request})
    
    # Fallback caso o arquivo index.html não esteja presente no diretório
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Controle Jurídico</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0d233a 0%, #1e4570 50%, #2a5298 100%);
                color: #ffffff; min-height: 100vh; display: flex;
                flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
            }
            .container { max-width: 500px; width: 100%; display: flex; flex-direction: column; align-items: center; }
            .balanca-svg { width: 180px; height: 180px; margin-bottom: 20px; filter: drop-shadow(0px 4px 10px rgba(0,0,0,0.4)); }
            h1 { font-size: 2.2rem; font-weight: 700; margin-bottom: 8px; }
            .subtitle { font-size: 1.1rem; color: #dcdcdc; margin-bottom: 6px; }
            .instruction { font-size: 0.95rem; color: #b0c4de; margin-bottom: 28px; }
            .btn-iniciar {
                background-color: #ffcc00; color: #0d233a; font-size: 1.25rem; font-weight: bold;
                padding: 16px 40px; border: none; border-radius: 50px; cursor: pointer; text-decoration: none;
                display: inline-flex; align-items: center; justify-content: center; gap: 10px;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35); transition: all 0.3s ease;
            }
            .btn-iniciar:hover { background-color: #e6b800; transform: translateY(-3px); }
        </style>
    </head>
    <body>
        <div class="container">
            <svg class="balanca-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <line x1="50" y1="6" x2="50" y2="82" stroke="#ffcc00" stroke-width="3.5" stroke-linecap="round"/>
                <circle cx="50" cy="6" r="4.5" fill="#ffcc00"/>
                <line x1="12" y1="22" x2="88" y2="22" stroke="#ffcc00" stroke-width="3.5" stroke-linecap="round"/>
                <line x1="12" y1="22" x2="12" y2="42" stroke="#ffcc00" stroke-width="2.1" stroke-linecap="round"/>
                <path d="M 1 42 A 11 16 0 0 0 23 42" fill="none" stroke="#ffcc00" stroke-width="2.1" stroke-linecap="round"/>
                <line x1="88" y1="22" x2="88" y2="42" stroke="#ffcc00" stroke-width="2.1" stroke-linecap="round"/>
                <path d="M 77 42 A 11 16 0 0 0 99 42" fill="none" stroke="#ffcc00" stroke-width="2.1" stroke-linecap="round"/>
                <polygon points="42,82 58,82 72,95 28,95" fill="#ffcc00"/>
            </svg>
            <h1>Controle Jurídico</h1>
            <p class="subtitle">Por Ede Brito</p>
            <p class="instruction">Clique abaixo para iniciar</p>
            <a href="/painel" class="btn-iniciar">🚀 Iniciar Sistema</a>
        </div>
    </body>
    </html>
    """)

# ------------------------------------------------------------------
# ROTA 2: Painel Principal (Dashboard de Gestão)
# ------------------------------------------------------------------
@app.get("/painel", response_class=HTMLResponse)
async def carregar_painel(request: Request):
    total_processos = 0
    total_prazos = 0
    total_audiencias = 0
    total_clientes = 0

    # Busca totalizadora de processos
    try:
        conn = get_db_connection()
        res = conn.run("SELECT COUNT(*) FROM processos")
        if res: total_processos = res[0][0]
        conn.close()
    except Exception:
        pass

    # Busca totalizadora de prazos
    try:
        conn = get_db_connection()
        res = conn.run("SELECT COUNT(*) FROM prazos WHERE concluido = False")
        if res: total_prazos = res[0][0]
        conn.close()
    except Exception:
        pass

    # Busca totalizadora de audiências
    try:
        conn = get_db_connection()
        res = conn.run("SELECT COUNT(*) FROM audiencias")
        if res: total_audiencias = res[0][0]
        conn.close()
    except Exception:
        pass

    # Busca totalizadora de clientes
    try:
        conn = get_db_connection()
        res = conn.run("SELECT COUNT(*) FROM clientes")
        if res: total_clientes = res[0][0]
        conn.close()
    except Exception:
        pass

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel Geral - Controle Jurídico</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            body {{ background-color: #f4f6f9; color: #333; }}
            header {{ background-color: #0d233a; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
            header h1 {{ font-size: 1.3rem; }}
            nav a {{ color: #ffcc00; text-decoration: none; font-weight: bold; font-size: 0.95rem; }}
            
            .container {{ max-width: 1000px; margin: 25px auto; padding: 0 15px; }}
            
            /* Grid de Indicadores Principais */
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; border-left: 5px solid #1e4570; }}
            .stat-card.prazo {{ border-left-color: #d9534f; }}
            .stat-card.audiencia {{ border-left-color: #0275d8; }}
            .stat-card h3 {{ font-size: 2rem; color: #0d233a; margin-bottom: 4px; }}
            .stat-card p {{ font-size: 0.9rem; color: #666; font-weight: 600; }}

            /* Grid de Módulos do Sistema */
            .modules-title {{ font-size: 1.1rem; color: #0d233a; margin-bottom: 15px; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
            .modules-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }}
            .module-btn {{ background-color: #1e4570; color: white; padding: 18px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 3px 8px rgba(0,0,0,0.1); transition: background 0.2s, transform 0.1s; }}
            .module-btn:hover {{ background-color: #0d233a; transform: translateY(-2px); }}
            .module-btn span {{ font-size: 1.1rem; }}
            .badge-icon {{ font-size: 1.3rem; }}
        </style>
    </head>
    <body>
        <header>
            <h1>Painel de Controle Jurídico</h1>
            <nav>
                <a href="/">← Voltar ao Início</a>
            </nav>
        </header>

        <div class="container">
            <!-- Cards Resumo -->
            <div class="stats-grid">
                <div class="stat-card prazo">
                    <h3>⏳ {total_prazos}</h3>
                    <p>Prazos Pendentes</p>
                </div>
                <div class="stat-card audiencia">
                    <h3>📆 {total_audiencias}</h3>
                    <p>Audiências</p>
                </div>
                <div class="stat-card">
                    <h3>📂 {total_processos}</h3>
                    <p>Processos Ativos</p>
                </div>
                <div class="stat-card">
                    <h3>👤 {total_clientes}</h3>
                    <p>Clientes Cadastrados</p>
                </div>
            </div>

            <h2 class="modules-title">Módulos de Gestão</h2>

            <!-- Módulos do Sistema -->
            <div class="modules-grid">
                <a href="/agenda" class="module-btn">
                    <span>⏳ Agenda & Prazos</span>
                    <span class="badge-icon">➔</span>
                </a>
                <a href="/processos" class="module-btn">
                    <span>📂 Gestão de Processos</span>
                    <span class="badge-icon">➔</span>
                </a>
                <a href="/clientes" class="module-btn">
                    <span>👤 Cadastro de Clientes</span>
                    <span class="badge-icon">➔</span>
                </a>
                <a href="/publicacoes" class="module-btn">
                    <span>📬 Publicações PJe</span>
                    <span class="badge-icon">➔</span>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ------------------------------------------------------------------
# ROTAS SECUNDÁRIAS (Placeholders para os módulos)
# ------------------------------------------------------------------
@app.get("/agenda", response_class=HTMLResponse)
async def modulo_agenda():
    return HTMLResponse(content="<h1>⏳ Módulo de Agenda e Prazos</h1><p><a href='/painel'>← Voltar</a></p>")

@app.get("/processos", response_class=HTMLResponse)
async def modulo_processos():
    return HTMLResponse(content="<h1>📂 Módulo de Processos</h1><p><a href='/painel'>← Voltar</a></p>")

@app.get("/clientes", response_class=HTMLResponse)
async def modulo_clientes():
    return HTMLResponse(content="<h1>👤 Módulo de Clientes</h1><p><a href='/painel'>← Voltar</a></p>")

@app.get("/publicacoes", response_class=HTMLResponse)
async def modulo_publicacoes():
    return HTMLResponse(content="<h1>📬 Módulo de Publicações PJe</h1><p><a href='/painel'>← Voltar</a></p>")
