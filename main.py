import os
from datetime import date
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

def formatar_data(raw_data):
    if not raw_data:
        return 'N/A'
    if hasattr(raw_data, 'strftime'):
        dt_obj = raw_data
        if dt_obj.year < 2000:
            try:
                ano_corrigido = int(str(dt_obj.year).zfill(4)[-2:]) + 2000
                dt_obj = dt_obj.replace(year=ano_corrigido)
            except Exception:
                pass
        return dt_obj.strftime('%d/%m/%Y')
    try:
        parts = str(raw_data).split()[0].split('-')
        ano = int(parts[0])
        if ano < 2000:
            ano = int(str(ano).zfill(4)[-2:]) + 2000
        return f"{parts[2]}/{parts[1]}/{ano}"
    except Exception:
        return str(raw_data)

@app.get("/", response_class=HTMLResponse)
async def home():
    clientes, processos, agenda, prazos = [], [], [], []
    hoje = date.today()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Clientes
        try:
            cursor.execute('SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC LIMIT 30;')
            clientes = cursor.fetchall()
        except Exception as e:
            print(f"Erro Clientes: {e}")
            conn.rollback()

        # 2. Processos
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

        # 3. Agenda
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
                WHERE a."Cumprido" IS NULL 
                   OR a."Cumprido" = FALSE 
                   OR CAST(a."Cumprido" AS TEXT) IN ('0', 'false', 'FALSE', 'f', 'F', 'no', 'NO')
                ORDER BY a."Data" ASC, a."Horário" ASC 
                LIMIT 50;
            """)
            agenda = cursor.fetchall()
        except Exception as e:
            print(f"Erro Agenda Join: {e}")
            conn.rollback()

        # 4. Publicações / Prazos (Traz registros com DataCumprimento)
        try:
            cursor.execute("""
                SELECT 
                    pub.*,
                    p."Processo" AS numero_processo,
                    c."Nomecli" AS cliente_nome,
                    c."Empresa" AS cliente_empresa
                FROM "Publicações" pub
                LEFT JOIN "Processos" p ON pub."ProcessoNovoCod1" = p."ProcessoNovoCod1"
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                WHERE pub."DataCumprimento" IS NOT NULL
                ORDER BY pub."DataCumprimento" DESC;
            """)
            prazos = cursor.fetchall()
        except Exception as e:
            print(f"Erro Publicações Join: {e}")
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
        cliente = item.get('cliente_nome') or item.get('cliente_empresa') or item.get('NomeCli') or 'Não informado'
        
        raw_hora = item.get('horario_compromisso') or item.get('Horário')
        hora_fmt = ""
        if raw_hora:
            if hasattr(raw_hora, 'strftime'):
                hora_fmt = raw_hora.strftime('%H:%M')
            else:
                try:
                    hora_fmt = str(raw_hora).strip()[:5]
                except Exception:
                    hora_fmt = str(raw_hora)

        data_fmt = formatar_data(item.get('Data'))
        data_hora_exibicao = f"{data_fmt} - {hora_fmt}" if hora_fmt else data_fmt

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        agenda_html += f"""
        <div class="card">
            <h3>📆 {tipo}</h3>
            <p><strong>Data:</strong> {data_hora_exibicao}</p>
            {f'<p><strong>Processo:</strong> {identificacao_proc}</p>' if identificacao_proc else ''}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Descrição:</strong> {desc}</p>
        </div>
        """
    if not agenda:
        agenda_html = "<p style='padding:15px;'>Nenhum registro pendente na Agenda.</p>"

    # Renderiza Prazos com a nova classificação por DataCumprimento
    prazos_html = ""
    counts = {"vencidos": 0, "vencendo": 0, "a_vencer": 0}

    for prazo in prazos:
        cod_novo = prazo.get('ProcessoNovoCod1') or ''
        num_proc = prazo.get('numero_processo') or ''
        cliente = prazo.get('cliente_nome') or prazo.get('cliente_empresa') or 'Não informado'
        
        dt_cump_raw = prazo.get('DataCumprimento')
        data_cump = formatar_data(dt_cump_raw)
        data_venc = formatar_data(prazo.get('DataVencimento') or prazo.get('Data'))
        manifestacao = prazo.get('Manifestação') or prazo.get('Manifestacao') or 'Não informada'
        publicacao = prazo.get('Publicação') or prazo.get('Publicacao') or prazo.get('Texto') or 'Sem publicação'

        # Trata e corrige o ano de dt_cump_raw
        dt_cump_obj = None
        if dt_cump_raw:
            if hasattr(dt_cump_raw, 'date'):
                dt_cump_obj = dt_cump_raw.date()
            elif isinstance(dt_cump_raw, date):
                dt_cump_obj = dt_cump_raw
            
            if dt_cump_obj and dt_cump_obj.year < 2000:
                try:
                    ano_corrigido = int(str(dt_cump_obj.year).zfill(4)[-2:]) + 2000
                    dt_cump_obj = dt_cump_obj.replace(year=ano_corrigido)
                except Exception:
                    pass

        # Classificação baseada em DataCumprimento vs Hoje
        categoria_prazo = "a_vencer"
        if dt_cump_obj:
            if dt_cump_obj < hoje:
                categoria_prazo = "vencidos"
            elif dt_cump_obj == hoje:
                categoria_prazo = "vencendo"
            else:
                categoria_prazo = "a_vencer"

        counts[categoria_prazo] += 1

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        prazos_html += f"""
        <div class="card card-prazo item-prazo status-{categoria_prazo}">
            <h3>⏳ Data de Cumprimento: {data_cump}</h3>
            <p><strong>Publicação:</strong> {data_venc}</p>
            {f'<p><strong>Processo:</strong> {identificacao_proc}</p>' if identificacao_proc else ''}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Manifestação:</strong> {manifestacao}</p>
            <details class="pub-details">
                <summary>▶ Ver publicação</summary>
                <div class="pub-content">{publicacao}</div>
            </details>
        </div>
        """

    prazos_html += f"""
    <div class="empty-msg msg-vencidos" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento anterior a hoje.</div>
    <div class="empty-msg msg-vencendo" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento para hoje.</div>
    <div class="empty-msg msg-a_vencer" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento posterior a hoje.</div>
    """

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
                --red-deadline: #dc3545;
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
            
            .sub-filter-bar {{
                display: flex;
                gap: 8px;
                margin-bottom: 12px;
            }}
            .btn-sub-filter {{
                flex: 1;
                padding: 8px 4px;
                border: 1px solid #ced4da;
                background-color: #ffffff;
                color: #495057;
                border-radius: 6px;
                font-size: 0.82rem;
                font-weight: 600;
                cursor: pointer;
                text-align: center;
            }}
            .btn-sub-filter.active {{
                background-color: var(--blue-primary);
                color: white;
                border-color: var(--blue-primary);
            }}

            .card {{
                background: white;
                border-radius: 10px;
                padding: 14px;
                margin-bottom: 10px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                border-left: 4px solid var(--blue-primary);
            }}
            .card.card-prazo {{
                border-left-color: var(--red-deadline);
            }}
            .card h3 {{ margin: 0 0 6px 0; color: var(--blue-dark); font-size: 1rem; }}
            .card.card-prazo h3 {{ color: var(--red-deadline); }}
            .card p {{ margin: 3px 0; color: #495057; font-size: 0.9rem; }}

            .pub-details {{
                margin-top: 10px;
                border-top: 1px solid #f0f0f0;
                padding-top: 6px;
            }}
            .pub-details summary {{
                color: var(--blue-primary);
                font-weight: bold;
                font-size: 0.88rem;
                cursor: pointer;
                outline: none;
            }}
            .pub-content {{
                margin-top: 8px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
                font-size: 0.85rem;
                color: #333;
                white-space: pre-wrap;
                line-height: 1.4;
            }}

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
                color: #6c757d; font-size: 0.85rem;
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
            <div id="prazos" class="section active">
                <div class="sub-filter-bar">
                    <button class="btn-sub-filter" onclick="filtrarPrazos('vencidos', this)">Vencidos ({counts['vencidos']})</button>
                    <button class="btn-sub-filter" onclick="filtrarPrazos('vencendo', this)">Vencendo ({counts['vencendo']})</button>
                    <button class="btn-sub-filter active" onclick="filtrarPrazos('a_vencer', this)">A vencer ({counts['a_vencer']})</button>
                </div>
                <div id="prazos-list">
                    {prazos_html}
                </div>
            </div>
            <div id="agenda" class="section">{agenda_html}</div>
            <div id="processos" class="section">{processos_html}</div>
            <div id="clientes" class="section">{clientes_html}</div>
        </div>
        <nav class="bottom-nav">
            <button class="nav-item active" onclick="showTab('prazos', this)">⏳ Prazos</button>
            <button class="nav-item" onclick="showTab('agenda', this)">📆 Agenda</button>
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

            function filtrarPrazos(status, btnElement) {{
                document.querySelectorAll('.btn-sub-filter').forEach(b => b.classList.remove('active'));
                if(btnElement) btnElement.classList.add('active');

                let totalVisivel = 0;
                document.querySelectorAll('.item-prazo').forEach(item => {{
                    if (item.classList.contains('status-' + status)) {{
                        item.style.display = 'block';
                        totalVisivel++;
                    }} else {{
                        item.style.display = 'none';
                    }}
                }});

                document.querySelectorAll('.empty-msg').forEach(msg => msg.style.display = 'none');
                if (totalVisivel === 0) {{
                    const msgEl = document.querySelector('.msg-' + status);
                    if (msgEl) msgEl.style.display = 'block';
                }}
            }}

            document.addEventListener("DOMContentLoaded", function() {{
                const btnAtivo = document.querySelector('.btn-sub-filter.active');
                if (btnAtivo) {{
                    filtrarPrazos('a_vencer', btnAtivo);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
