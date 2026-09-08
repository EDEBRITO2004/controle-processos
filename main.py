# -*- coding: utf-8 -*-
import os
from datetime import date
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import pg8000.native

app = FastAPI(title="Controle de Processos")

# Configurações do Banco de Dados
DB_USER = "controle_processos_lnju_user"
DB_PASS = "J7I5L81oYnOyPcxRIO5FqBkx1RP0HQoX"
DB_HOST = "dpg-dac0l9jtqb8s73dqjh00-a.virginia-postgres.render.com"
DB_NAME = "controle_processos_lnju"

def get_db_connection():
    return pg8000.native.Connection(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        database=DB_NAME,
        ssl_context=True
    )

def fetch_all_dict(conn, query):
    try:
        res = conn.run(query)
        if not res:
            return []
        cols = [col['name'] for col in conn.columns]
        return [dict(zip(cols, row)) for row in res]
    except Exception as e:
        print(f"Erro na query: {query[:60]}... Erro: {e}")
        return []

def formatar_data(raw_data):
    if not raw_data:
    try:
        parts = str(raw_data).split()[0].split('-')
        ano = int(parts[0])
        if ano < 2000:
            ano = int(str(ano).zfill(4)[-2:]) + 2000
        return f"{parts[2]}/{parts[1]}/{ano}"
    except Exception:
        return str(raw_data)

def get_val(row, *keys):
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None

# ------------------------------------------------------------------
# TEMPLATE DA TELA DE ABERTURA (SPLASH)
# ------------------------------------------------------------------
SPLASH_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Controle Jurídico</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        html, body { height: 100%; }
        body {
            background: linear-gradient(180deg, #0d47a1 0%, #1976d2 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: white;
            text-align: center;
            padding: 20px;
        }

        }

        /* Travessão Horizontal */
        .haste-horizontal {
            width: 140px;
            height: 5px;
            background-color: #fbc02d;
            position: absolute;
            top: 25px;
            border-radius: 2px;
        }

        /* Pratos da Balança (Semicírculos) */
        .prato {
            width: 40px;
            height: 20px;
            border: 4px solid #fbc02d;
            border-top: none;
            border-bottom-left-radius: 25px;
            border-bottom-right-radius: 25px;
            position: absolute;
            top: 55px;
        }

        .prato.esquerdo { left: 0px; }
        .prato.direito { right: 0px; }

        /* Base Trapezoidal */
        .base {
            width: 0;
            height: 0;
            border-left: 25px solid transparent;
            border-right: 25px solid transparent;
            border-bottom: 20px solid #fbc02d;
            position: absolute;
            bottom: 0;
        }

        h1 { font-size: 1.8rem; font-weight: bold; margin-bottom: 6px; }
        .subtitulo { font-size: 1rem; color: #ffcc00; font-style: italic; margin-bottom: 40px; }
        .btn-acesso {
            background-color: #ffcc00;
            color: #0d233a;
            font-weight: bold;
            font-size: 1.05rem;
            padding: 16px 40px;
            border-radius: 30px;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            display: inline-block;
        }
        .btn-acesso:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="balanca">
        <div class="topo"></div>
        <div class="haste-horizontal"></div>
        <div class="haste-vertical"></div>
        <div class="prato esquerdo"></div>
        <div class="prato direito"></div>
        <div class="base"></div>
    </div>
    <h1>Controle Jurídico</h1>
    <div class="subtitulo">por Ede Brito</div>
    <a href="/painel" class="btn-acesso">Acesso ao sistema</a>
</body>
</html>"""

# ------------------------------------------------------------------
# TEMPLATE DA TELA DO PAINEL DASHBOARD
# ------------------------------------------------------------------
PAINEL_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Geral - Controle Jurídico</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f4f6f9; color: #333; padding-bottom: 30px; }
        header { background-color: #0d233a; color: white; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        header h1 { font-size: 1.2rem; font-weight: bold; line-height: 1.2; }
        nav a { color: #ffcc00; text-decoration: none; font-weight: bold; font-size: 0.9rem; }
        
        .container { max-width: 500px; margin: 20px auto; padding: 0 15px; }
        
        /* Cards dos Contadores */
        .stats-grid { display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px; }
        .stat-card { background: white; padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center; border-left: 5px solid #1e4570; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .stat-card.prazo { border-left-color: #dc3545; }
        .stat-card.audiencia { border-left-color: #0d6efd; }
        .stat-val { font-size: 2rem; font-weight: bold; color: #0d233a; display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
        .stat-card p { font-size: 0.9rem; color: #666; font-weight: 600; }

        /* Módulos de Gestão */
        .modules-title { font-size: 1.1rem; color: #0d233a; margin-bottom: 15px; font-weight: bold; }
        .modules-grid { display: flex; flex-direction: column; gap: 12px; }
        .module-btn { background-color: #1e4570; color: white; padding: 16px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 3px 8px rgba(0,0,0,0.1); transition: background 0.2s; }
        .module-btn:hover { background-color: #0d233a; }
        .module-btn span { font-size: 1rem; display: flex; align-items: center; gap: 8px; }
        .badge-icon { font-size: 1.2rem; }
    </style>
</head>
<body>
    <header>
        <h1>Painel de Controle<br>Jurídico</h1>
        <nav>
            <a href="/">← Voltar ao Início</a>
        </nav>
    </header>

    <div class="container">
        <!-- Indicadores -->
        <div class="stats-grid">
            <div class="stat-card prazo">
                <div class="stat-val">⏳ {{TOTAL_PRAZOS}}</div>
                <p>Prazos Pendentes</p>
            </div>
            <div class="stat-card audiencia">
                <div class="stat-val">📆 {{TOTAL_AUDIENCIAS}}</div>
                <p>Audiências</p>
            </div>
            <div class="stat-card">
                <div class="stat-val">📂 {{TOTAL_PROCESSOS}}</div>
                <p>Processos Ativos</p>
            </div>
            <div class="stat-card">
                <div class="stat-val">👤 {{TOTAL_CLIENTES}}</div>
                <p>Clientes Cadastrados</p>
            </div>
        </div>

        <h2 class="modules-title">Módulos de Gestão</h2>

        <!-- Botões vinculados individualmente às suas listas -->
        <div class="modules-grid">
            <a href="/sistema?tab=prazos" class="module-btn">
                <span>⏳ Gestão de Prazos</span>
                <span class="badge-icon">➔</span>
            </a>
            <a href="/sistema?tab=agenda" class="module-btn">
                <span>📆 Agenda & Audiências</span>
                <span class="badge-icon">➔</span>
            </a>
            <a href="/sistema?tab=processos" class="module-btn">
                <span>📂 Gestão de Processos</span>
                <span class="badge-icon">➔</span>
            </a>
            <a href="/sistema?tab=clientes" class="module-btn">
                <span>👤 Cadastro de Clientes</span>
                <span class="badge-icon">➔</span>
            </a>
        </div>
    </div>
</body>
</html>"""

# ------------------------------------------------------------------
# TEMPLATE DAS LISTAS (SEM O RODAPÉ DE ATALHOS)
# ------------------------------------------------------------------
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
            padding-bottom: 30px;
        }
        header {
            background-color: var(--blue-dark);
            color: white;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
            font-size: 1.1rem;
        }
        header a { color: #ffcc00; text-decoration: none; font-size: 0.88rem; }
       .container {
            padding: 12px;
            max-width: 600px;
            margin: 0 auto;
        }
       .section { display: none; }
       .section.active { display: block; }

       .search-box { margin-bottom: 12px; }
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
            resize: none;
            overflow-y: hidden;
            min-height: 50px;
            font-family: inherit;
            line-height: 1.4;
        }
       .obs-form button {
            align-self: flex-end;
            background-color: var(--blue-primary);
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: bold;
            cursor: pointer;
        }

       .pub-details { margin-top: 6px; }
       .pub-details summary {
            color: var(--blue-dark);
            font-weight: bold;
            font-size: 0.9rem;
            cursor: pointer;
            outline: none;
            list-style: none;
        }
       .pub-details summary::-webkit-details-marker { display: none; }
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
       .sub-proc-list li { margin-bottom: 4px; }

       .erro-banner {
            background: #fff3cd;
            color: #664d03;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
            border: 1px solid #ffecb5;
        }

        #toast {
            visibility: hidden;
            min-width: 250px;
            background-color: #198754;
            color: #fff;
            text-align: center;
            border-radius: 8px;
            z-index: 1000;
            left: 50%;
            top: 20px;
            transform: translateX(-50%);
            font-size: 0.9rem;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            opacity: 0;
            transition: opacity 0.3s, top 0.3s;
        }
        #toast.show {
            visibility: visible;
            opacity: 1;
            top: 30px;
        }
    </style>
</head>
<body>
    <header>
        <span>Controle de Processos</span>
        <a href="/painel">📊 Voltar ao Painel</a>
    </header>
    <div id="toast">✅ Observação salva com sucesso!</div>

    <div class="container">
        {{ERRO_BANNER}}
        <div id="prazos" class="section">
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
            textarea.style.height = textarea.scrollHeight + 'px';
        }

        function initAutoResize() {
            document.querySelectorAll('.auto-resize').forEach(function (textarea) {
                autoAjustarTextarea(textarea);
                textarea.addEventListener('input', function () {
                    autoAjustarTextarea(this);
                });
            });
        }

        function showToast(mensagem) {
            var toast = document.getElementById("toast");
            if (mensagem) toast.innerText = mensagem;
            toast.className = "show";
            setTimeout(function(){ toast.className = toast.className.replace("show", ""); }, 3000);
        }

        async function salvarObservacao(event, form, itemId) {
            event.preventDefault();
            var formData = new FormData(form);
            try {
                var response = await fetch('/agenda/atualizar/' + itemId, {
                    method: 'POST',
                    body: formData
                });
                var res = await response.json();
                if (res.status === 'ok') {
                    showToast("✅ Observação salva com sucesso!");
                    var details = form.closest('details');
                    if (details) {
                        var summary = details.querySelector('summary');
                        var val = formData.get('observacoes') || '';
                        if (summary) {
                            summary.innerText = val.trim() ? "▶ Ver/Editar observação" : "▶ Adicionar observação";
                        }
                    }
                } else {
                    alert("Erro ao salvar: " + (res.message || "Erro desconhecido"));
                }
            } catch (err) {
                alert("Erro na requisição: " + err);
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
            const urlParams = new URLSearchParams(window.location.search);
            const initialTab = urlParams.get('tab') || 'prazos';
            showTab(initialTab);

            filtrarPrazos('a_vencer', document.querySelector('#prazos .btn-sub-filter.active'));
            initAutoResize();
        });
    </script>
</body>
</html>"""

# ------------------------------------------------------------------
# ROTA 0: TELA DE ABERTURA (SPLASH)
# ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def splash():
    return HTMLResponse(content=SPLASH_TEMPLATE)

# ------------------------------------------------------------------
# ROTA 1: DASHBOARD
# ------------------------------------------------------------------
@app.get("/painel", response_class=HTMLResponse)
async def painel():
    cnt_prazos, cnt_audiencias, cnt_processos, cnt_clientes = 0, 0, 0, 0
    conn = None

    try:
        conn = get_db_connection()
        
        # Total Prazos Pendentes
        try:
            r = conn.run('SELECT COUNT(*) FROM "Publicações" WHERE "Cumprido" IS NULL OR "Cumprido" = FALSE;')
            if r: cnt_prazos = r[0][0]
        except Exception: pass

        # Total Audiências Pendentes
        try:
            r = conn.run('SELECT COUNT(*) FROM "Agenda" WHERE "Cumprido" IS NULL OR "Cumprido" = FALSE;')
            if r: cnt_audiencias = r[0][0]
        except Exception: pass

        # Total Processos
        try:
            r = conn.run('SELECT COUNT(*) FROM "Processos";')
            if r: cnt_processos = r[0][0]
        except Exception: pass

        # Total Clientes
        try:
            r = conn.run('SELECT COUNT(*) FROM "Clientes";')
            if r: cnt_clientes = r[0][0]
        except Exception: pass

    except Exception as e:
        print(f"Erro ao carregar totais do painel: {e}")
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    html = PAINEL_TEMPLATE.replace("{{TOTAL_PRAZOS}}", str(cnt_prazos))\
                          .replace("{{TOTAL_AUDIENCIAS}}", str(cnt_audiencias))\
                          .replace("{{TOTAL_PROCESSOS}}", str(cnt_processos))\
                          .replace("{{TOTAL_CLIENTES}}", str(cnt_clientes))
    return HTMLResponse(content=html)

# ------------------------------------------------------------------
# ROTA 2: EXIBIÇÃO DA LISTA SELECIONADA
# ------------------------------------------------------------------
@app.get("/sistema", response_class=HTMLResponse)
async def sistema():
    clientes, processos, agenda, prazos = [], [], [], []
    hoje = date.today()
    conn = None
    erro_db = ""

    try:
        conn = get_db_connection()

        try:
            clientes = fetch_all_dict(conn, 'SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC;')
        except Exception as e:
            erro_db += f"Clientes: {e}; "

        try:
            q_proc = """
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
            """
    if not clientes: clientes_html = "<p style='padding:15px;'>Nenhum cliente encontrado.</p>"

    erro_banner = f'<div class="erro-banner">⚠️ Erro ao conectar no banco: {erro_db}</div>' if erro_db else ""

    rendered_html = (
        HTML_TEMPLATE
       .replace("{{ERRO_BANNER}}", erro_banner)
       .replace("{{CNT_VENCIDOS}}", str(counts['vencidos']))
       .replace("{{CNT_VENCENDO}}", str(counts['vencendo']))
       .replace("{{CNT_A_VENCER}}", str(counts['a_vencer']))
       .replace("{{PRAZOS_HTML}}", prazos_html)
       .replace("{{AGENDA_HTML}}", agenda_html)
       .replace("{{PROCESSOS_HTML}}", processos_html)
       .replace("{{CLIENTES_HTML}}", clientes_html)
    )

    return HTMLResponse(content=rendered_html)

@app.post("/agenda/atualizar/{item_id}")
async def atualizar_observacao_agenda(item_id: int, observacoes: str = Form(None)):
    conn = None
    try:
        conn = get_db_connection()
        texto_obs = observacoes.strip() if observacoes and observacoes.strip() else None
        query = 'UPDATE "Agenda" SET "Observações" = :obs WHERE "Código" = :id'
        conn.run(query, obs=texto_obs, id=item_id)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
