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

        # Clientes
        try:
            cursor.execute('SELECT * FROM "Clientes" LIMIT 30;')
            clientes = cursor.fetchall()
        except Exception as e:
            print(f"Erro Clientes: {e}")
            conn.rollback()

        # Processos sem JOIN para evitar erros de relacionamento/tipagem
        try:
            cursor.execute('SELECT * FROM "Processos" LIMIT 30;')
            processos = cursor.fetchall()
        except Exception as e:
            print(f"Erro Processos: {e}")
            conn.rollback()

        # Agenda
        try:
            cursor.execute('SELECT * FROM "Agenda" LIMIT 30;')
            agenda = cursor.fetchall()
        except Exception as e:
            print(f"Erro Agenda: {e}")
            conn.rollback()

        cursor.close()
        conn.close()
    except Exception as err:
        print(f"Erro Conexao: {err}")

    # Auxiliar para tratar valores vazios/None/False
    def get_val(item, keywords, default="N/A"):
        for k, v in item.items():
            if any(kw in k.lower() for kw in keywords):
                if v not in [None, "", False]:
                    return str(v)
        return default

    # Renderiza Agenda
    agenda_html = ""
    for item in agenda:
        tipo = get_val(item, ['tipo', 'evento'], 'Compromisso')
        desc = get_val(item, ['desc', 'titulo', 'assunto'], 'Sem descrição')
        data = get_val(item, ['data'], 'N/A')
        
        agenda_html += f"""
        <div class="card">
            <h3>⏳ {tipo}</h3>
            <p><strong>Data/Hora:</strong> {data}</p>
            <p><strong>Descrição:</strong> {desc}</p>
        </div>
        """
    if not agenda:
        agenda_html = "<p style='padding:15px;'>Nenhum registro encontrado na Agenda.</p>"

    # Renderiza Processos
    processos_html = ""
    for proc in processos:
        # Busca o código do processo (processonovocod1)
        cod_novo = get_val(proc, ['processonovocod1'], 'Sem Código')
        
        # Busca o número judicial/original
        num_jud = get_val(proc, ['numeroprocesso', 'numprocesso', 'numero'], 'N/A')
        
        # Busca Cliente, Parte Contrária, Ação e Vara
        cliente = get_val(proc, ['nomecliente', 'cliente', 'codcli'])
        parte_contraria = get_val(proc, ['partecontraria', 'contraria', 'reu', 'réu'])
        acao = get_val(proc, ['nomeacao', 'acao', 'ação'])
        vara = get_val(proc, ['vara', 'juizo'])
        
        processos_html += f"""
        <div class="card">
            <h3>📁 Processo: {cod_novo}</h3>
            <p><strong>Nº Judicial:</strong> {num_jud}</p>
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Parte Contrária:</strong> {parte_contraria}</p>
            <p><strong>Ação:</strong> {acao}</p>
            <p><strong>Vara/Juízo:</strong> {vara}</p>
        </div>
        """
    if not processos:
        processos_html = "<p style='padding:15px;'>Nenhum processo encontrado.</p>"

    # Renderiza Clientes
    clientes_html = ""
    for cli in clientes:
        nome = get_val(cli, ['nome', 'cliente', 'razao'], 'Sem Nome')
        doc = get_val(cli, ['cpf', 'cnpj', 'doc'], 'N/A')
        tel = get_val(cli, ['tel', 'cel', 'fone'], 'N/A')
        
        clientes_html += f"""
        <div class="card">
            <h3>👤 {nome}</h3>
            <p><strong>Documento:</strong> {doc}</p>
            <p><strong>Telefone:</strong> {tel}</p>
        </div>
        """
    if not clientes:
        clientes_html = "<p style='padding:15px;'>Nenhum cliente encontrado.</p>"

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
