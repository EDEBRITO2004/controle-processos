# -*- coding: utf-8 -*-
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

# Helper para buscar valor em dicionario testando varios nomes de chaves/colunas
def get_val(row, *keys):
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Controle de Processos</title>
    <style>
        :root {
            --blue-primary: #0d6efd;
            --blue-dark: #0a58ca;
            --red-deadline: #dc3545;
            --bg-body: #f8f9fa;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-body);
            margin: 0;
            padding-bottom: 70px;
        }
        header {
            background-color: var(--blue-dark);
            color: white;
            padding: 16px;
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
        }
        .container {
            padding: 12px;
            max-width: 600px;
            margin: 0 auto;
        }
        .section { display: none; }
        .section.active { display: block; }

        .search-box {
            margin-bottom: 12px;
        }
        .search-box input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ced4da;
            border-radius: 8px;
            font-size: 0.9rem;
            box-sizing: border-box;
            outline: none;
        }
        .search-box input:focus {
            border-color: var(--blue-primary);
            box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
        }

        .sub-filter-bar {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .btn-sub-filter {
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
        }
        .btn-sub-filter.active {
            background-color: var(--blue-primary);
            color: white;
            border-color: var(--blue-primary);
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border-left: 4px solid var(--blue-primary);
        }
        .card.card-prazo {
            border-left-color: var(--red-deadline);
        }
        .card h3 { margin: 0 0 6px 0; color: var(--blue-dark); font-size: 1rem; }
        .card.card-prazo h3 { color: var(--red-deadline); }
        .card p { margin: 3px 0; color: #495057; font-size: 0.9rem; }

        .pub-details {
            margin-top: 6px;
        }
        .pub-details summary {
            color: var(--blue-dark);
            font-weight: bold;
            font-size: 0.9rem;
            cursor: pointer;
            outline: none;
            list-style: none;
        }
        .pub-details summary::-webkit-details-marker {
            display: none;
        }
        .pub-content {
            margin-top: 8px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 6px;
            font-size: 0.88rem;
            color: #333;
            line-height: 1.4;
            white-space: pre-wrap;
        }

        .sub-proc-list {
            margin: 4px 0 0 0;
            padding-left: 18px;
            font-size: 0.85rem;
            color: #495057;
        }
        .sub-proc-list li {
            margin-bottom: 4px;
        }

        .bottom-nav {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: white;
            display: flex;
            justify-content: space-around;
            padding: 12px 0;
            border-top: 1px solid #dee2e6;
        }
        .nav-item {
            border: none; background: none;
            color: #6c757d; font-size: 0.85rem;
            cursor: pointer;
        }
        .nav-item.active {
            color: var(--blue-primary);
            font-weight: bold;
        }
    </style>
</head>
<body>
    <header>Controle de Processos</header>
    <div class="container">
        <div id="prazos" class="section active">
            <div class="sub-filter-bar">
                <button class="btn-sub-filter" onclick="filtrarPrazos('vencidos', this)">Vencidos ({{CNT_VENCIDOS}})</button>
                <button class="btn-sub-filter" onclick="filtrarPrazos('vencendo', this)">Vencendo ({{CNT_VENCENDO}})</button>
                <button class="btn-sub-filter active" onclick="filtrarPrazos('a_vencer', this)">A vencer ({{CNT_A_VENCER}})</button>
            </div>
            <div id="prazos-list">
                {{PRAZOS_HTML}}
            </div>
        </div>
        <div id="agenda" class="section">{{AGENDA_HTML}}</div>
        <div id="processos" class="section">{{PROCESSOS_HTML}}</div>
        <div id="clientes" class="section">{{CLIENTES_HTML}}</div>
    </div>
    <nav class="bottom-nav">
        <button class="nav-item active" onclick="showTab('prazos', this)">⏳ Prazos</button>
        <button class="nav-item" onclick="showTab('agenda', this)">📆 Agenda</button>
        <button class="nav-item" onclick="showTab('processos', this)">📁 Processos</button>
        <button class="nav-item" onclick="showTab('clientes', this)">👥 Clientes</button>
    </nav>

    <script>
        function showTab(tabId, btnEl) {
            document.querySelectorAll('.section').forEach(function (sec) {
                sec.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');

            document.querySelectorAll('.nav-item').forEach(function (btn) {
                btn.classList.remove('active');
            });
            if (btnEl) {
                btnEl.classList.add('active');
            }
        }

        function filtrarPrazos(categoria, btnEl) {
            document.querySelectorAll('#prazos .btn-sub-filter').forEach(function (btn) {
                btn.classList.remove('active');
            });
            if (btnEl) {
                btnEl.classList.add('active');
            }

            var itens = document.querySelectorAll('#prazos-list .item-prazo');
            var visiveis = 0;
            itens.forEach(function (item) {
                if (item.classList.contains('status-' + categoria)) {
                    item.style.display = '';
                    visiveis++;
                } else {
                    item.style.display = 'none';
                }
            });

            document.querySelectorAll('#prazos-list .empty-msg').forEach(function (msg) {
                msg.style.display = 'none';
            });
            if (visiveis === 0) {
                var msg = document.querySelector('#prazos-list .msg-' + categoria);
                if (msg) {
                    msg.style.display = 'block';
                }
            }
        }

        function filtrarProcessos() {
            var termo = document.getElementById('search-processos').value.toLowerCase();
            document.querySelectorAll('#lista-processos .card-item-processo').forEach(function (card) {
                var texto = card.getAttribute('data-search') || '';
                card.style.display = texto.includes(termo) ? '' : 'none';
            });
        }

        function filtrarClientes() {
            var termo = document.getElementById('search-clientes').value.toLowerCase();
            document.querySelectorAll('#lista-clientes .card-item-cliente').forEach(function (card) {
                var texto = card.getAttribute('data-search') || '';
                card.style.display = texto.includes(termo) ? '' : 'none';
            });
        }

        document.addEventListener('DOMContentLoaded', function () {
            filtrarPrazos('a_vencer', document.querySelector('#prazos .btn-sub-filter.active'));
        });
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def home():
    clientes, processos, agenda, prazos = [], [], [], []
    hoje = date.today()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Clientes
        try:
            cursor.execute('SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC;')
            clientes = cursor.fetchall()
        except Exception as e:
            print(f"Erro Clientes: {e}")
            conn.rollback()

        # 2. Processos (incluindo JOIN com a tabela Sistemas)
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
                    a."Ação" AS acao_nome,
                    s."Sistema" AS sistema_nome,
                    s."Link" AS sistema_link
                FROM "Processos" p
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                LEFT JOIN "Ações" a ON p."Ação" = a."Código"
                LEFT JOIN "Sistemas" s ON p."Sistema" = s."Código"
                ORDER BY p."Código" DESC;
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
                ORDER BY a."Data" ASC, a."Horário" ASC;
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
                    p."ProcessoNovoCod1" AS proc_cod_vinculado,
                    p."Processo" AS numero_processo,
                    c."Nomecli" AS cliente_nome,
                    c."Empresa" AS cliente_empresa
                FROM "Publicações" pub
                LEFT JOIN "Processos" p 
                    ON TRIM(UPPER(pub."ProcessoNovoCod1")) = TRIM(UPPER(p."ProcessoNovoCod1"))
                LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
                ORDER BY "DataCumprimento" ASC;
            """)
            prazos = cursor.fetchall()
        except Exception as e:
            print(f"Erro Publicações Join: {e}")
            conn.rollback()

        cursor.close()
        conn.close()
    except Exception as err:
        print(f"Erro Conexao: {err}")

    # Mapeia processos por Cliente
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
        tipo = get_val(item, 'Tipo') or 'Compromisso'
        desc = get_val(item, 'Tarefa', 'Observações') or 'Sem descrição'
        cod_novo = get_val(item, 'ProcessoNovoCod1') or ''
        num_proc = get_val(item, 'numero_processo', 'Processo') or ''
        cliente = get_val(item, 'cliente_nome', 'cliente_empresa', 'NomeCli') or 'Não informado'

        raw_hora = get_val(item, 'horario_compromisso', 'Horário')
        hora_fmt = ""
        if raw_hora:
            if hasattr(raw_hora, 'strftime'):
                hora_fmt = raw_hora.strftime('%H:%M')
            else:
                try:
                    hora_fmt = str(raw_hora).strip()[:5]
                except Exception:
                    hora_fmt = str(raw_hora)

        data_fmt = formatar_data(get_val(item, 'Data'))
        data_hora_exibicao = f"{data_fmt} - {hora_fmt}" if hora_fmt else data_fmt

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""

        agenda_html += (
            '<div class="card">'
            f'<h3>📆 {tipo}</h3>'
            f'<p><strong>Data:</strong> {data_hora_exibicao}</p>'
            f'{proc_line}'
            f'<p><strong>Cliente:</strong> {cliente}</p>'
            f'<p><strong>Descrição:</strong> {desc}</p>'
            '</div>'
        )
    if not agenda:
        agenda_html = "<p style='padding:15px;'>Nenhum registro pendente na Agenda.</p>"

    # Renderiza Prazos
    prazos_html = ""
    counts = {"vencidos": 0, "vencendo": 0, "a_vencer": 0}

    for prazo in prazos:
        cumprido_flag = get_val(prazo, 'Cumprido')
        if cumprido_flag in [True, 1, '1', 'true', 'TRUE', 't', 'T', 'yes', 'YES']:
            continue

        cod_novo = get_val(prazo, 'ProcessoNovoCod1', 'proc_cod_vinculado') or ''
        num_proc = get_val(prazo, 'numero_processo', 'Processo') or ''
        cliente = get_val(prazo, 'cliente_nome', 'cliente_empresa') or 'Não informado'

        dt_ref_raw = get_val(prazo, 'DataCumprimento')
        data_cumprimento_fmt = formatar_data(dt_ref_raw)
        data_publicacao_fmt = formatar_data(get_val(prazo, 'Data'))

        manifestacao = get_val(prazo, 'Manifestação') or 'Não informada'
        publicacao = get_val(prazo, 'Publicação', 'Observações') or 'Sem texto de publicação'
        prazo_desc = get_val(prazo, 'Prazo') or ''

        dt_ref_obj = None
        if dt_ref_raw:
            if hasattr(dt_ref_raw, 'date'):
                dt_ref_obj = dt_ref_raw.date()
            elif isinstance(dt_ref_raw, date):
                dt_ref_obj = dt_ref_raw

            if dt_ref_obj and dt_ref_obj.year < 2000:
                try:
                    ano_corrigido = int(str(dt_ref_obj.year).zfill(4)[-2:]) + 2000
                    dt_ref_obj = dt_ref_obj.replace(year=ano_corrigido)
                except Exception:
                    pass

        categoria_prazo = "a_vencer"
        if dt_ref_obj:
            if dt_ref_obj < hoje:
                categoria_prazo = "vencidos"
            elif dt_ref_obj == hoje:
                categoria_prazo = "vencendo"
            else:
                categoria_prazo = "a_vencer"

        counts[categoria_prazo] += 1

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""
        prazo_line = f"<p><strong>Prazo:</strong> {prazo_desc}</p>" if prazo_desc else ""

        prazos_html += (
            f'<div class="card card-prazo item-prazo status-{categoria_prazo}">'
            f'<h3>⏳ Data Cumprimento: {data_cumprimento_fmt}</h3>'
            f'<p><strong>Publicado em:</strong> {data_publicacao_fmt}</p>'
            f'{proc_line}'
            f'<p><strong>Cliente:</strong> {cliente}</p>'
            f'<p><strong>Manifestação:</strong> {manifestacao}</p>'
            '<details class="pub-details">'
            '<summary>▶ Ver publicação</summary>'
            f'<div class="pub-content">{publicacao}</div>'
            '</details>'
            '</div>'
        )

    prazos_html += """
    <div class="empty-msg msg-vencidos" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo vencido.</div>
    <div class="empty-msg msg-vencendo" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo vencendo hoje.</div>
    <div class="empty-msg msg-a_vencer" style="display:none; padding:15px; color:#6c757d;">Nenhum prazo futuro a vencer.</div>
    """

    # Renderiza Processos
    processos_html = """
    <div class="search-box">
        <input type="text" id="search-processos" placeholder="🔍 Buscar processo, cliente, ação..." onkeyup="filtrarProcessos()">
    </div>
    <div id="lista-processos">
    """
    for proc in processos:
        cod_novo = get_val(proc, 'ProcessoNovoCod1') or 'Sem Cód. Novo'
        num_proc = get_val(proc, 'Processo') or ''
        cliente = get_val(proc, 'cliente_nome', 'cliente_empresa') or 'Não informado'
        parte_contraria = get_val(proc, 'parte_contraria') or 'Não informada'
        acao = get_val(proc, 'acao_nome') or 'Não informada'
        vara = get_val(proc, 'Vara') or 'Não informada'
        
        sistema_nome = get_val(proc, 'sistema_nome') or ''
        sistema_link = get_val(proc, 'sistema_link') or ''

        # Botão de Link para o Sistema
        if sistema_link and str(sistema_link).strip():
            url = str(sistema_link).strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            btn_link_html = f'''
            <a href="{url}" target="_blank" style="display:inline-block; margin-top:8px; padding:6px 12px; background-color:#0d6efd; color:white; text-decoration:none; border-radius:6px; font-size:0.85rem; font-weight:bold;">
                &#128279; Acessar {sistema_nome or "Sistema"}
            </a>
            '''
        else:
            btn_link_html = '''
            <button onclick="alert('Nenhum link cadastrado para este sistema.')" style="margin-top:8px; padding:6px 12px; background-color:#6c757d; color:white; border:none; border-radius:6px; font-size:0.85rem; cursor:pointer;">
                &#128279; Sem link cadastrado
            </button>
            '''

        texto_busca = f"{cod_novo} {num_proc} {cliente} {parte_contraria} {acao} {vara} {sistema_nome}".lower()
        proc_num_line = f"<p><strong>Nº Processo:</strong> {num_proc}</p>" if num_proc else ""
        sistema_line = f"<p><strong>Sistema:</strong> {sistema_nome}</p>" if sistema_nome else ""

        processos_html += (
            f'<div class="card card-item-processo" data-search="{texto_busca}">'
            f'<h3>📁 {cod_novo}</h3>'
            f'{proc_num_line}'
            f'<p><strong>Cliente:</strong> {cliente}</p>'
            f'<p><strong>Parte Contrária:</strong> {parte_contraria}</p>'
            f'<p><strong>Ação:</strong> {acao}</p>'
            f'<p><strong>Vara/Juízo:</strong> {vara}</p>'
            f'{sistema_line}'
            f'{btn_link_html}'
            '</div>'
        )
    processos_html += "</div>"
    if not processos:
        processos_html = "<p style='padding:15px;'>Nenhum processo encontrado.</p>"

    # Renderiza Clientes
    clientes_html = """
    <div class="search-box">
        <input type="text" id="search-clientes" placeholder="🔍 Buscar por nome, CPF/CNPJ, cidade..." onkeyup="filtrarClientes()">
    </div>
    <div id="lista-clientes">
    """
    for cli in clientes:
        cod_cli = get_val(cli, 'CodCli')
        nome = get_val(cli, 'Nomecli', 'Empresa') or 'Sem Nome'
        doc = get_val(cli, 'CPF_CNPJ') or 'N/A'
        rg = get_val(cli, 'RG_IE') or 'N/A'
        tel = get_val(cli, 'NúmeroTelefone') or 'N/A'

        endereco_rua = get_val(cli, 'EndCli') or ''
        cidade = get_val(cli, 'CidaCli') or ''
        cep = get_val(cli, 'CEP') or ''

        partes_end = [p for p in [endereco_rua, cidade, cep] if p]
        endereco_completo = ", ".join(partes_end) if partes_end else "Não informado"

        procs_cli = processos_por_cliente.get(cod_cli, [])
        procs_html = ""
        if procs_cli:
            for p_item in procs_cli:
                c_num = get_val(p_item, 'ProcessoNovoCod1') or 'Sem Cód.'
                num_p = get_val(p_item, 'Processo') or ''
                a_nome = get_val(p_item, 'acao_nome') or 'Ação N/I'

                ident = c_num
                if num_p and num_p != c_num:
                    ident += f" ({num_p})"
                procs_html += f"<li><strong>{ident}</strong> - {a_nome}</li>"
            procs_html = f"<ul class='sub-proc-list'>{procs_html}</ul>"
        else:
            procs_html = "<p style='font-size:0.85rem; color:#6c757d; margin-top:4px;'>Nenhum processo vinculado.</p>"

        texto_busca = f"{nome} {doc} {rg} {tel} {endereco_completo}".lower()

        clientes_html += (
            f'<div class="card card-item-cliente" data-search="{texto_busca}">'
            '<details class="pub-details">'
            '<summary style="cursor:pointer; outline:none;">'
            f'<div style="font-size:1.05rem; font-weight:bold; color:var(--blue-dark); margin-bottom:4px;">👤 {nome}</div>'
            f'<div style="font-size:0.88rem; color:#495057; font-weight:normal;"><strong>Documento:</strong> {doc}</div>'
            f'<div style="font-size:0.88rem; color:#495057; font-weight:normal;"><strong>Telefone:</strong> {tel}</div>'
            '</summary>'
            '<div class="pub-content" style="margin-top:10px;">'
            f'<p><strong>RG:</strong> {rg}</p>'
            f'<p><strong>Endereço:</strong> {endereco_completo}</p>'
            '<hr style="border:0; border-top:1px solid #e0e0e0; margin:8px 0;">'
            '<p><strong>Processos Relacionados:</strong></p>'
            f'{procs_html}'
            '</div>'
            '</details>'
            '</div>'
        )
    clientes_html += "</div>"
    if not clientes:
        clientes_html = "<p style='padding:15px;'>Nenhum cliente encontrado.</p>"

    # Substituição final do template
    rendered_html = (
        HTML_TEMPLATE
        .replace("{{CNT_VENCIDOS}}", str(counts['vencidos']))
        .replace("{{CNT_VENCENDO}}", str(counts['vencendo']))
        .replace("{{CNT_A_VENCER}}", str(counts['a_vencer']))
        .replace("{{PRAZOS_HTML}}", prazos_html)
        .replace("{{AGENDA_HTML}}", agenda_html)
        .replace("{{PROCESSOS_HTML}}", processos_html)
        .replace("{{CLIENTES_HTML}}", clientes_html)
    )

    return HTMLResponse(content=rendered_html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
