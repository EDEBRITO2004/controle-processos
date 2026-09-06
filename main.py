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
            cursor.execute('SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC LIMIT 100;')
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
                    p."CodCli",
                    p."Parte Contrária" AS parte_contraria,
                    p."Vara",
                    c."Nomecli" AS cliente_nome,
                    c."Empresa" AS cliente_empresa,
                    a."Ação" AS acao_nome
                FROM "Processos" p
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                LEFT JOIN "Ações" a ON p."Ação" = a."Código"
                ORDER BY p."Código" DESC
                LIMIT 100;
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

        # 4. Publicações / Prazos
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

    # Mapeia processos por Cliente (CodCli)
    processos_por_cliente = {}
    for proc in processos:
        cod_cli = proc.get('CodCli')
        if cod_cli:
            if cod_cli not in processos_por_cliente:
                processos_por_cliente[cod_cli] = []
            processos_por_cliente[cod_cli].append(proc)

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

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""

        agenda_html += f"""
        <div class="card">
            <h3>📆 {tipo}</h3>
            <p><strong>Data:</strong> {data_hora_exibicao}</p>
            {proc_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Descrição:</strong> {desc}</p>
        </div>
        """
    if not agenda:
        agenda_html = "<p style='padding:15px;'>Nenhum registro pendente na Agenda.</p>"

    # Renderiza Prazos
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

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""

        prazos_html += f"""
        <div class="card card-prazo item-prazo status-{categoria_prazo}">
            <h3>⏳ Data Cumprimento: {data_cump}</h3>
            <p><strong>Vencimento:</strong> {data_venc}</p>
            {proc_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Manifestação:</strong> {manifestacao}</p>
            <details class="pub-details">
                <summary>▶ Ver publicação</summary>
                <div class="pub-content">{publicacao}</div>
            </details>
        </div>
        """

    prazos_html += """
    <div class="empty-msg msg-vencidos" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento anterior a hoje.</div>
    <div class="empty-msg msg-vencendo" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento para hoje.</div>
    <div class="empty-msg msg-a_vencer" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo com Data Cumprimento posterior a hoje.</div>
    """

    # Renderiza Processos (Com campo de busca)
    processos_html = """
    <div class="search-box">
        <input type="text" id="search-processos" placeholder="🔍 Buscar processo, cliente, ação..." onkeyup="filtrarProcessos()">
    </div>
    <div id="lista-processos">
    """
    for proc in processos:
        cod_novo = proc.get('ProcessoNovoCod1') or 'Sem Cód. Novo'
        num_proc = proc.get('Processo') or ''
        cliente = proc.get('cliente_nome') or proc.get('cliente_empresa') or 'Não informado'
        parte_contraria = proc.get('parte_contraria') or 'Não informada'
        acao = proc.get('acao_nome') or 'Não informada'
        vara = proc.get('Vara') or 'Não informada'
        
        texto_busca = f"{cod_novo} {num_proc} {cliente} {parte_contraria} {acao} {vara}".lower()
        proc_num_line = f"<p><strong>Nº Processo:</strong> {num_proc}</p>" if num_proc else ""

        processos_html += f"""
        <div class="card card-item-processo" data-search="{texto_busca}">
            <h3>📁 {cod_novo}</h3>
            {proc_num_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Parte Contrária:</strong> {parte_contraria}</p>
            <p><strong>Ação:</strong> {acao}</p>
            <p><strong>Vara/Juízo:</strong> {vara}</p>
        </div>
        """
    processos_html += "</div>"
    if not processos:
        processos_html = "<p style='padding:15px;'>Nenhum processo encontrado.</p>"

    # Renderiza Clientes (Com busca + details expansível)
    clientes_html = """
    <div class="search-box">
        <input type="text" id="search-clientes" placeholder="🔍 Buscar por nome, CPF/CNPJ, cidade..." onkeyup="filtrarClientes()">
    </div>
    <div id="lista-clientes">
    """
    for cli in clientes:
        cod_cli = cli.get('CodCli')
        nome = cli.get('Nomecli') or cli.get('Empresa') or 'Sem Nome'
        doc = cli.get('CPF_CNPJ') or cli.get('Cpf_Cnpj') or cli.get('CPF') or 'N/A'
        rg = cli.get('RG') or cli.get('Rg') or 'N/A'
        tel = cli.get('NúmeroTelefone') or cli.get('Telefone') or cli.get('Celular') or 'N/A'
        
        rua = cli.get('Endereço') or cli.get('Endereco') or ''
        num = cli.get('Número') or cli.get('Numero') or ''
        bairro = cli.get('Bairro') or ''
        cidade = cli.get('Cidade') or ''
        uf = cli.get('Estado') or cli.get('UF') or ''
        
        partes_end = [p for p in [rua, num, bairro, cidade, uf] if p]
        endereco_completo = ", ".join(partes_end) if partes_end else "Não informado"

        procs_cli = processos_por_cliente.get(cod_cli, [])
        procs_html = ""
        if procs_cli:
            for p_item in procs_cli:
                c_num = p_item.get('ProcessoNovoCod1') or 'Sem Cód.'
                num_p = p_item.get('Processo') or ''
                a_nome = p_item.get('acao_nome') or 'Ação N/I'
                
                ident = c_num
                if num_p and num_p != c_num:
                    ident += f" ({num_p})"
                procs_html += f"<li><strong>{ident}</strong> - {a_nome}</li>"
            procs_html = f"<ul class='sub-proc-list'>{procs_html}</ul>"
        else:
            procs_html = "<p style='font-size:0.85rem; color:#6c757d; margin-top:4px;'>Nenhum processo vinculado.</p>"

        texto_busca = f"{nome} {doc} {rg} {tel} {endereco_completo}".lower()

        clientes_html += f"""
        <div class="card card-item-cliente" data-search="{texto_busca}">
            <details class="pub-details">
                <summary style="cursor:pointer; outline:none;">
                    <div style="font-size:1.05rem; font-weight:bold; color:var(--blue-dark); margin-bottom:4px;">👤 {nome}</div>
                    <div style="font-size:0.88rem; color:#495057; font-weight:normal;"><strong>Documento:</strong> {doc}</div>
                    <div style="font-size:0.88rem; color:#495057; font-weight:normal;"><strong>Telefone:</strong> {tel}</div>
                </summary>
                <div class="pub-content" style="margin-top:10px;">
                    <p><strong>RG:</strong> {rg}</p>
                    <p><strong>Endereço:</strong> {endereco_completo}</p>
                    <hr style="border:0; border-top:1px solid #e0e0e0; margin:8px 0;">
                    <p><strong>Processos Relacionados:</strong></p>
                    {procs_html}
                </div>
            </details>
        </div>
        """
    clientes_html += "</div>"
    if not clientes:
        clientes_html = "<p style='padding:15px;'>Nenhum cliente encontrado.</p>"

    cnt_vencidos = counts['vencidos']
    cnt_vencendo = counts['vencendo']
    cnt_a_vencer = counts['a_vencer']

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
            
            .search-box {{
                margin-bottom: 12px;
            }}
            .search-box input {{
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #ced4da;
                border-radius: 8px;
                font-size: 0.9rem;
                box-sizing: border-box;
                outline: none;
            }}
            .search-box input:focus {{
                border-color: var(--blue-primary);
                box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
            }}

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
                margin-top: 2px;
            }}
            .pub-details summary {{
                color: var(--blue-dark);
                font-weight: bold;
                font-size: 1rem;
                cursor: pointer;
                outline: none;
                list-style: none;
            }}
            .pub-details summary::-webkit-details-marker {{
                display: none;
            }}
            .pub-content {{
                margin-top: 10px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
                font-size: 0.88rem;
                color: #333;
                line-height: 1.4;
            }}

            .sub-proc-list {{
                margin: 4px 0 0 0;
                padding-left: 18px;
                font-size: 0.85rem;
                color: #495057;
            }}
            .sub-proc-list li {{
                margin-bottom: 4px;
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
                    <button class="btn-sub-filter" onclick="filtrarPrazos('vencidos', this)">Vencidos ({cnt_vencidos})</button>
                    <button class="btn-sub-filter" onclick="filtrarPrazos('vencendo', this)">Vencendo ({cnt_vencendo})</button>
                    <button class="btn-sub-filter active" onclick="filtrarPrazos('a_vencer', this)">A vencer ({cnt_a_vencer})</button>
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
            function showTab
