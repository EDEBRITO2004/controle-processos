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

        # 1. Busca Clientes
        try:
            cursor.execute('SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC LIMIT 30;')
            clientes = cursor.fetchall()
        except Exception as e:
            print(f"Erro Clientes: {e}")
            conn.rollback()

        # 2. Busca Processos
        try:
            cursor.execute("""
                SELECT 
                    p."ProcessoNovoCod1",
                    p."Processo",
                    p."Parte Contrária" AS parte_contraria,
                    p."Vara",
                    c."Nomecli" AS cliente_nome,
                    c."Empresa" AS cliente_empresa,
                    a."Ação" AS acao_nome
                FROM "Processos" p
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                LEFT JOIN "Ações" a ON p."Ação" = a."Código"
                ORDER BY p."Código" DESC
                LIMIT 30;
            """)
            processos = cursor.fetchall()
        except Exception as e:
            print(f"Erro Processos Join: {e}")
            conn.rollback()
        # Busca Agenda com Horário
        try:
            cursor.execute("""
                SELECT 
                    a.*,
                    a."Horário" AS horario_compromisso,
                    p."Processo" AS numero_processo,
                    c."Nomecli" AS cliente_nome,
                    c."Empresa" AS cliente_empresa
                FROM "Agenda" a
                LEFT JOIN "Processos" p ON a."ProcessoNovoCod1" = p."ProcessoNovoCod1"
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                WHERE a."Cumprido" = FALSE OR a."Cumprido" IS NULL 
                ORDER BY a."Data" ASC, a."Horário" ASC 
                LIMIT 30;
            """)
            agenda = cursor.fetchall()
        except Exception as e:
            print(f"Erro Agenda Join: {e}")
            conn.rollback()



        cursor.close()
        conn.close()
    except Exception as err:
        print(f"Erro Conexao: {err}")

    # Renderiza Agenda
    agenda_html = ""
    for item in agenda:
        tipo = item.get('Tipo') or 'Compromisso'
        desc = item.get('Tarefa') or item.get('Observações') or 'Sem descrição'
        cod_novo = item.get('ProcessoNovoCod1') or ''
        num_proc = item.get('numero_processo') or ''
        
        # Cliente vindo do JOIN ou da própria tabela Agenda
        cliente = item.get('cliente_nome') or item.get('cliente_empresa') or item.get('NomeCli') or 'Não informado'
        
        # Formatação de Data (DD/MM/AAAA)
        raw_data = item.get('Data')
        data_fmt = 'N/A'
        if raw_data:
            if hasattr(raw_data, 'strftime'):
                data_fmt = raw_data.strftime('%d/%m/%Y')
            else:
                try:
                    parts = str(raw_data).split()[0].split('-')
                    data_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
                except Exception:
                    data_fmt = str(raw_data)

        # Monta a identificação do processo
        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        agenda_html += f"""
        <div class="card">
            <h3>⏳ {tipo}</h3>
            <p><strong>Data:</strong> {data_fmt}</p>
            {f'<p><strong>Processo:</strong> {identificacao_proc}</p>' if identificacao_proc else ''}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Descrição:</strong> {desc}</p>
        </div>
        """
    if not agenda:
        agenda_html = "<p style='padding:15px;'>Nenhum registro pendente na Agenda.</p>"

    # Renderiza Processos
    processos_html = ""
    for proc in processos:
        cod_novo = proc.get('ProcessoNovoCod1') or 'Sem Cód. Novo'
        num_proc = proc.get('Processo') or ''
        cliente = proc.get('cliente_nome') or proc.get('cliente_empresa') or 'Não informado'
        parte_contraria = proc.get('parte_contraria') or 'Não informada'
        acao = proc.get('acao_nome') or 'Não informada'
        vara = proc.get('Vara') or 'Não informada'
        
        processos_html += f"""
        <div class="card">
            <h3>📁 {cod_novo}</h3>
            {f'<p><strong>Nº Processo:</strong> {num_proc}</p>' if num_proc else ''}
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
        nome = cli.get('Nomecli') or cli.get('Empresa') or 'Sem Nome'
        doc = cli.get('CPF_CNPJ') or 'N/A'
        tel = cli.get('NúmeroTelefone') or 'N/A'
        
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
