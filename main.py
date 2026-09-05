import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://controle_processos_lnju_user:J7I5L81oYnOyPcxRIO5FqBkx1RP0HQoX@dpg-dac0l9jtqb8s73dqjh00-a.virginia-postgres.render.com/controle_processos_lnju"
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=RealDictCursor)

@app.get("/", response_class=HTMLResponse)
async def home():
    clientes, processos, agenda = [], [], []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 20;")
            clientes = cursor.fetchall()
        except Exception:
            conn.rollback()

        try:
            cursor.execute("SELECT * FROM processos ORDER BY id DESC LIMIT 20;")
            processos = cursor.fetchall()
        except Exception:
            conn.rollback()

        try:
            cursor.execute("SELECT * FROM agenda ORDER BY data_hora ASC LIMIT 20;")
            agenda = cursor.fetchall()
        except Exception:
            conn.rollback()

        cursor.close()
        conn.close()
    except Exception as err:
        print(f"Erro na conexao com o banco: {err}")

    # Monta os cards de Agenda
    agenda_html = ""
    for item in agenda:
        agenda_html += f"""
        <div class="card">
            <h3>⏳ {item.get('tipo', 'Prazo/Audiência')}</h3>
            <p><strong>Processo:</strong> {item.get('processo_numero', 'N/A')}</p>
            <p><strong>Data/Hora:</strong> {item.get('data_hora', 'N/A')}</p>
            <p><strong>Descrição:</strong> {item.get('descricao', '')}</p>
        </div>
        """
    if not agenda:
        agenda_html = "<p>Nenhuma audiência ou prazo agendado.</p>"

    # Monta os cards de Processos
    processos_html = ""
    for proc in processos:
        processos_html += f"""
        <div class="card">
            <h3>📁 {proc.get('numero_processo', proc.get('numero', 'Sem número'))}</h3>
            <p><strong>Ação:</strong> {proc.get('acao', 'N/A')}</p>
            <p><strong>Vara:</strong> {proc.get('vara', 'N/A')}</p>
        </div>
        """
    if not processos:
        processos_html = "<p>Nenhum processo cadastrado.</p>"

    # Monta os cards de Clientes
    clientes_html = ""
    for cli in clientes:
        clientes_html += f"""
        <div class="card">
            <h3>👤 {cli.get('nome', 'Sem nome')}</h3>
            <p><strong>CPF/CNPJ:</strong> {cli.get('cpf_cnpj', cli.get('cpf', 'N/A'))}</p>
            <p><strong>Telefone:</strong> {cli.get('telefone', 'N/A')}</p>
        </div>
        """
    if not clientes:
        clientes_html = "<p>Nenhum cliente cadastrado.</p>"

    # HTML completo com layout responsivo em azul
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Controle de Processos</title>
        <style>
            :root {{
                --blue-primary: #0d6efd;
                --blue-dark: #0a58ca;
                --bg-body: #f8f9fa;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg-body);
                margin: 0;
                padding-bottom: 70px;
            }}
            header {{
                background-color: var(--blue-dark);
                color: white;
                padding: 16px;
                text-align: center;
                font-weight: bold;
                font-size: 1.2rem;
            }}
            .container {{
                padding: 12px;
                max-width: 600px;
                margin: 0 auto;
            }}
            .section {{ display: none; }}
            .section.active {{ display: block; }}
            .card {{
                background: white;
                border-radius: 10px;
                padding: 14px;
                margin-bottom: 10px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                border-left: 4px solid var(--blue-primary);
            }}
            .card h3 {{ margin: 0 0 6px 0; color: var(--blue-dark); font-size: 1rem; }}
            .card p {{ margin: 3px 0; color: #495057; font-size: 0.9rem; }}
            .bottom-nav {{
                position: fixed;
                bottom: 0; left: 0; right: 0;
                background: white;
                display: flex;
                justify-content: space-around;
                padding: 12px 0;
                border-top: 1px solid #dee2e6;
            }}
            .nav-item {{
                border: none; background: none;
                color: #6c757d; font-size: 0.9rem;
                cursor: pointer;
            }}
            .nav-item.active {{
                color: var(--blue-primary);
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <header>Controle de Processos</header>
        <div class="container">
            <div id="agenda" class="section active">{agenda_html}</div>
            <div id="processos" class="section">{processos_html}</div>
            <div id="clientes" class="section">{clientes_html}</div>
        </div>
        <nav class="bottom-nav">
            <button class="nav-item active" onclick="showTab('agenda', this)">⏳ Agenda</button>
            <button class="nav-item" onclick="showTab('processos', this)">📁 Processos</button>
            <button class="nav-item" onclick="showTab('clientes', this)">👤 Clientes</button>
        </nav>
        <script>
            function showTab(tabId, element) {{
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                element.classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
