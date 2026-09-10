# -*- coding: utf-8 -*-
import os
import json
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import pg8000.native
from curl_cffi import requests

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

def get_val(row, *keys):
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None

def eh_dia_util(dt):
    if dt.weekday() in (5, 6):
        return False
    feriados_fixos = [(1, 1), (21, 4), (1, 5), (7, 9), (12, 10), (2, 11), (15, 11), (20, 11), (25, 12)]
    if (dt.day, dt.month) in feriados_fixos:
        return False
    return True

def calcular_prazo_5_dias_uteis(data_disp_str):
    try:
        dt_disp = datetime.strptime(data_disp_str, "%Y-%m-%d").date()
    except ValueError:
        dt_disp = datetime.now().date()
        
    dt_pub = dt_disp + timedelta(days=1)
    while not eh_dia_util(dt_pub):
        dt_pub += timedelta(days=1)
        
    dias = 0
    dt_limite = dt_pub
    while dias < 5:
        dt_limite += timedelta(days=1)
        if eh_dia_util(dt_limite):
            dias += 1
            
    return dt_pub, dt_limite

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
        body {
            background: linear-gradient(180deg, #0d47a1 0%, #1976d2 100%);
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 100vh; color: white; text-align: center; padding: 20px;
        }
        .balanca { position: relative; width: 160px; height: 140px; display: flex; flex-direction: column; align-items: center; margin-bottom: 24px; }
        .haste-vertical { width: 6px; height: 100px; background-color: #fbc02d; position: absolute; top: 15px; }
        .topo { width: 14px; height: 14px; background-color: #fbc02d; border-radius: 50%; position: absolute; top: 5px; }
        .haste-horizontal { width: 140px; height: 5px; background-color: #fbc02d; position: absolute; top: 25px; border-radius: 2px; }
        .prato { width: 40px; height: 20px; border: 4px solid #fbc02d; border-top: none; border-bottom-left-radius: 25px; border-bottom-right-radius: 25px; position: absolute; top: 55px; }
        .prato.esquerdo { left: 0px; }
        .prato.direito { right: 0px; }
        .base { width: 0; height: 0; border-left: 25px solid transparent; border-right: 25px solid transparent; border-bottom: 20px solid #fbc02d; position: absolute; bottom: 0; }
        h1 { font-size: 1.8rem; font-weight: bold; margin-bottom: 6px; }
        .subtitulo { font-size: 1rem; color: #ffcc00; font-style: italic; margin-bottom: 40px; }
        .btn-acesso { background-color: #ffcc00; color: #0d233a; font-weight: bold; font-size: 1.05rem; padding: 16px 40px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(0,0,0,0.25); display: inline-block; }
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
# TEMPLATE DO PAINEL DASHBOARD
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
        .stats-grid { display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px; }
        .stat-card { background: white; padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center; border-left: 5px solid #1e4570; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .stat-card.prazo { border-left-color: #dc3545; }
        .stat-card.audiencia { border-left-color: #0d6efd; }
        .stat-val { font-size: 2rem; font-weight: bold; color: #0d233a; display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
        .stat-card p { font-size: 0.9rem; color: #666; font-weight: 600; }
        .modules-title { font-size: 1.1rem; color: #0d233a; margin-bottom: 15px; font-weight: bold; }
        .modules-grid { display: flex; flex-direction: column; gap: 12px; }
        .module-btn { background-color: #1e4570; color: white; padding: 16px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 3px 8px rgba(0,0,0,0.1); }
        .module-btn:hover { background-color: #0d233a; }
    </style>
</head>
<body>
    <header>
        <h1>Painel de Controle<br>Jurídico</h1>
        <nav><a href="/">← Voltar ao Início</a></nav>
    </header>

    <div class="container">
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

        <div class="modules-grid">
            <a href="/prazos" class="module-btn">
                <span>⏳ Gestão de Prazos</span>
                <span>➔</span>
            </a>
            <a href="/agenda" class="module-btn">
                <span>📆 Agenda & Audiências</span>
                <span>➔</span>
            </a>
            <a href="/processos" class="module-btn">
                <span>📂 Gestão de Processos</span>
                <span>➔</span>
            </a>
            <a href="/clientes" class="module-btn">
                <span>👤 Cadastro de Clientes</span>
                <span>➔</span>
            </a>
        </div>
    </div>
</body>
</html>"""

# ------------------------------------------------------------------
# TEMPLATE BASE DAS TELAS DE MÓDULOS
# ------------------------------------------------------------------
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITULO_PAGINA}} - Controle Jurídico</title>
    <style>
        :root {
            --blue-primary: #0d6efd;
            --blue-dark: #0a58ca;
            --red-deadline: #dc3545;
            --bg-body: #f8f9fa;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg-body); margin: 0; padding-bottom: 30px; }
        header { background-color: var(--blue-dark); color: white; padding: 16px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; font-size: 1.1rem; }
        header a { color: #ffcc00; text-decoration: none; font-size: 0.88rem; }
        .container { padding: 12px; max-width: 600px; margin: 0 auto; }
        .search-form { display: flex; gap: 6px; margin-bottom: 12px; }
        .search-form input { flex: 1; padding: 10px 12px; border: 1px solid #ced4da; border-radius: 8px; font-size: 0.9rem; outline: none; }
        .search-form button { padding: 10px 16px; background-color: var(--blue-primary); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .sub-filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
        .btn-sub-filter { flex: 1; padding: 10px 4px; border: 1px solid #ced4da; background-color: #ffffff; color: #495057; border-radius: 6px; font-size: 0.85rem; font-weight: bold; text-decoration: none; text-align: center; display: block; }
        .btn-sub-filter.active { background-color: var(--blue-primary); color: white; border-color: var(--blue-primary); }
        .card { background: white; border-radius: 10px; padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid var(--blue-primary); }
        .card.card-prazo { border-left-color: var(--red-deadline); }
        .card h3 { margin: 0 0 6px 0; color: var(--blue-dark); font-size: 1rem; }
        .card.card-prazo h3 { color: var(--red-deadline); }
        .card p { margin: 3px 0; color: #495057; font-size: 0.9rem; }
        .obs-form { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }
        .obs-form textarea { width: 100%; padding: 8px; border: 1px solid #ced4da; border-radius: 6px; font-size: 0.88rem; box-sizing: border-box; resize: vertical; min-height: 60px; font-family: inherit; }
        .obs-form button { align-self: flex-end; background-color: var(--blue-primary); color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 0.82rem; font-weight: bold; cursor: pointer; }
        .pub-details summary { color: var(--blue-dark); font-weight: bold; font-size: 0.9rem; cursor: pointer; outline: none; }
        .pub-content { margin-top: 8px; padding: 10px; background-color: #f8f9fa; border-radius: 6px; font-size: 0.88rem; color: #333; white-space: pre-wrap; }
        .sub-proc-list { margin: 4px 0 0 0; padding-left: 18px; font-size: 0.85rem; color: #495057; }
        .info-banner { background: #d1e7dd; color: #0f5132; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #badbcc; font-size: 0.9rem; font-weight: 500; }
        .erro-banner { background: #f8d7da; color: #842029; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #f5c2c7; font-size: 0.9rem; }
    </style>
</head>
<body>
    <header>
        <span>{{TITULO_PAGINA}}</span>
        <a href="/painel">📊 Voltar ao Painel</a>
    </header>

    <div class="container">
        {{INFO_BANNER}}
        {{ERRO_BANNER}}
        {{CONTEUDO_PAGINA}}
    </div>
</body>
</html>"""

# ------------------------------------------------------------------
# ROTAS DO SISTEMA
# ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def splash():
    return HTMLResponse(content=SPLASH_TEMPLATE)

@app.get("/painel", response_class=HTMLResponse)
async def painel():
    cnt_prazos, cnt_audiencias, cnt_processos, cnt_clientes = 0, 0, 0, 0
    conn = None
    try:
        conn = get_db_connection()
        try:
            r = conn.run('SELECT COUNT(*) FROM "Publicações" WHERE "Cumprido" IS NULL OR "Cumprido" = FALSE;')
            if r: cnt_prazos = r[0][0]
        except Exception: pass
        try:
            r = conn.run('SELECT COUNT(*) FROM "Agenda" WHERE "Cumprido" IS NULL OR "Cumprido" = FALSE;')
            if r: cnt_audiencias = r[0][0]
        except Exception: pass
        try:
            r = conn.run('SELECT COUNT(*) FROM "Processos";')
            if r: cnt_processos = r[0][0]
        except Exception: pass
        try:
            r = conn.run('SELECT COUNT(*) FROM "Clientes";')
            if r: cnt_clientes = r[0][0]
        except Exception: pass
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    html = PAINEL_TEMPLATE.replace("{{TOTAL_PRAZOS}}", str(cnt_prazos))\
                          .replace("{{TOTAL_AUDIENCIAS}}", str(cnt_audiencias))\
                          .replace("{{TOTAL_PROCESSOS}}", str(cnt_processos))\
                          .replace("{{TOTAL_CLIENTES}}", str(cnt_clientes))
    return HTMLResponse(content=html)

# MÓDULO 1: PRAZOS (Com filtro nativo via Query String)
@app.get("/prazos", response_class=HTMLResponse)
async def pagina_prazos(aba: str = "a_vencer", msg: str = None, erro: str = None):
    hoje = date.today()
    prazos = []
    erro_db = erro or ""
    conn = None
    try:
        conn = get_db_connection()
        q_pub = """
            SELECT
                pub.*,
                p."ProcessoNovoCod1" AS proc_cod_vinculado,
                p."Processo" AS numero_processo,
                c."Nomecli" AS cliente_nome,
                c."Empresa" AS cliente_empresa
            FROM "Publicações" pub
            LEFT JOIN "Processos" p ON TRIM(UPPER(pub."ProcessoNovoCod1")) = TRIM(UPPER(p."ProcessoNovoCod1"))
            LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
            ORDER BY "DataCumprimento" ASC;
        """
        prazos = fetch_all_dict(conn, q_pub)
    except Exception as e:
        erro_db = str(e)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    counts = {"vencidos": 0, "vencendo": 0, "a_vencer": 0}
    cards_html = ""

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

        dt_ref_obj = None
        if dt_ref_raw:
            if hasattr(dt_ref_raw, 'date'): dt_ref_obj = dt_ref_raw.date()
            elif isinstance(dt_ref_raw, date): dt_ref_obj = dt_ref_raw

        categoria_prazo = "a_vencer"
        if dt_ref_obj:
            if dt_ref_obj < hoje: categoria_prazo = "vencidos"
            elif dt_ref_obj == hoje: categoria_prazo = "vencendo"
            else: categoria_prazo = "a_vencer"

        counts[categoria_prazo] += 1

        if categoria_prazo != aba:
            continue

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""

        cards_html += f"""
        <div class="card card-prazo">
            <h3>⏳ Data Cumprimento: {data_cumprimento_fmt}</h3>
            <p><strong>Publicado em:</strong> {data_publicacao_fmt}</p>
            {proc_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Manifestação:</strong> {manifestacao}</p>
            <details class="pub-details">
                <summary>▶ Ver publicação</summary>
                <div class="pub-content">{publicacao}</div>
            </details>
        </div>
        """

    if not cards_html:
        cards_html = f"<div style='padding:15px; color:#6c757d; background:white; border-radius:8px;'>Nenhum prazo nesta categoria ({aba.replace('_', ' ')}).</div>"

    active_v = "active" if aba == "vencidos" else ""
    active_vc = "active" if aba == "vencendo" else ""
    active_av = "active" if aba == "a_vencer" else ""

    conteudo = f"""
    <div style="margin-bottom: 12px;">
        <form action="/prazos/sincronizar-djen" method="post">
            <button type="submit" style="width: 100%; padding: 12px; background-color: #198754; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 0.9rem; cursor: pointer;">
                🔄 Sincronizar Publicações DJEN (OAB 182981/SP)
            </button>
        </form>
    </div>
    <div class="sub-filter-bar">
        <a href="/prazos?aba=vencidos" class="btn-sub-filter {active_v}">Vencidos ({counts['vencidos']})</a>
        <a href="/prazos?aba=vencendo" class="btn-sub-filter {active_vc}">Vencendo ({counts['vencendo']})</a>
        <a href="/prazos?aba=a_vencer" class="btn-sub-filter {active_av}">A vencer ({counts['a_vencer']})</a>
    </div>
    <div>
        {cards_html}
    </div>
    """

    info_banner = f'<div class="info-banner">{msg}</div>' if msg else ""
    erro_banner = f'<div class="erro-banner">⚠️ Erro: {erro_db}</div>' if erro_db else ""
    html = PAGE_TEMPLATE.replace("{{TITULO_PAGINA}}", "Gestão de Prazos")\
                        .replace("{{INFO_BANNER}}", info_banner)\
                        .replace("{{ERRO_BANNER}}", erro_banner)\
                        .replace("{{CONTEUDO_PAGINA}}", conteudo)
    return HTMLResponse(content=html)

# MÓDULO 2: AGENDA
@app.get("/agenda", response_class=HTMLResponse)
async def pagina_agenda(msg: str = None):
    agenda = []
    erro_db = ""
    conn = None
    try:
        conn = get_db_connection()
        q_ag = """
            SELECT
                a.*,
                a."Código" AS codigo_agenda,
                a."Horário" AS horario_compromisso,
                a."Observações" AS observacoes_agenda,
                p."Processo" AS numero_processo,
                c."Nomecli" AS cliente_nome,
                c."Empresa" AS cliente_empresa
            FROM "Agenda" a
            LEFT JOIN "Processos" p ON a."ProcessoNovoCod1" = p."ProcessoNovoCod1"
            LEFT JOIN "Clientes" c ON p."CodCli" = c."CodCli"
            WHERE a."Cumprido" IS NULL OR a."Cumprido" = FALSE
            ORDER BY a."Data" ASC, a."Horário" ASC;
        """
        agenda = fetch_all_dict(conn, q_ag)
    except Exception as e:
        erro_db = str(e)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    cards_html = ""
    for item in agenda:
        item_id = get_val(item, 'codigo_agenda', 'Código', 'id')
        tipo = get_val(item, 'Tipo') or 'Compromisso'
        desc = get_val(item, 'Tarefa') or 'Sem descrição'
        obs = get_val(item, 'observacoes_agenda', 'Observações') or ''
        cod_novo = get_val(item, 'ProcessoNovoCod1') or ''
        num_proc = get_val(item, 'numero_processo', 'Processo') or ''
        cliente = get_val(item, 'cliente_nome', 'cliente_empresa') or 'Não informado'

        raw_hora = get_val(item, 'horario_compromisso', 'Horário')
        hora_fmt = ""
        if raw_hora is not None:
            if hasattr(raw_hora, 'strftime'):
                hora_fmt = raw_hora.strftime('%H:%M')
            else:
                txt = str(raw_hora).strip()
                if ' ' in txt: txt = txt.split()[-1]
                if ':' in txt:
                    partes = txt.split(':')
                    hora_fmt = f"{partes[0].zfill(2)}:{partes[1].zfill(2)}"

        data_fmt = formatar_data(get_val(item, 'Data'))
        data_hora_exibicao = f"{data_fmt} - {hora_fmt}" if hora_fmt else data_fmt

        identificacao_proc = cod_novo
        if num_proc and num_proc != cod_novo:
            identificacao_proc += f" ({num_proc})" if cod_novo else num_proc

        proc_line = f"<p><strong>Processo:</strong> {identificacao_proc}</p>" if identificacao_proc else ""
        titulo_obs = "▶ Ver/Editar observação" if obs and obs.strip() else "▶ Adicionar observação"

        cards_html += f"""
        <div class="card">
            <h3>📆 {tipo}</h3>
            <p><strong>Data:</strong> {data_hora_exibicao}</p>
            {proc_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Descrição:</strong> {desc}</p>
            <details class="pub-details">
                <summary>{titulo_obs}</summary>
                <div class="pub-content">
                    <form class="obs-form" action="/agenda/atualizar/{item_id}" method="post">
                        <textarea name="observacoes" placeholder="Digite aqui as observações...">{obs}</textarea>
                        <button type="submit">💾 Salvar Observação</button>
                    </form>
                </div>
            </details>
        </div>
        """

    if not agenda:
        cards_html = "<p style='padding:15px; background:white; border-radius:8px;'>Nenhum registro pendente na Agenda.</p>"

    info_banner = f'<div class="info-banner">{msg}</div>' if msg else ""
    erro_banner = f'<div class="erro-banner">⚠️ Erro no Banco: {erro_db}</div>' if erro_db else ""
    html = PAGE_TEMPLATE.replace("{{TITULO_PAGINA}}", "Agenda & Audiências")\
                        .replace("{{INFO_BANNER}}", info_banner)\
                        .replace("{{ERRO_BANNER}}", erro_banner)\
                        .replace("{{CONTEUDO_PAGINA}}", cards_html)
    return HTMLResponse(content=html)

# MÓDULO 3: PROCESSOS (Busca Nativa do Servidor)
@app.get("/processos", response_class=HTMLResponse)
async def pagina_processos(q: str = ""):
    processos = []
    erro_db = ""
    conn = None
    termo_busca = q.strip().lower()
    try:
        conn = get_db_connection()
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
        processos = fetch_all_dict(conn, q_proc)
    except Exception as e:
        erro_db = str(e)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    cards_html = ""
    encontrados = 0
    for proc in processos:
        cod_novo = get_val(proc, 'ProcessoNovoCod1') or 'Sem Cód. Novo'
        num_proc = get_val(proc, 'Processo') or ''
        cliente = get_val(proc, 'cliente_nome', 'cliente_empresa') or 'Não informado'
        parte_contraria = get_val(proc, 'parte_contraria') or 'Não informada'
        acao = get_val(proc, 'acao_nome') or 'Não informada'
        vara = get_val(proc, 'Vara') or 'Não informada'
        sistema_nome = get_val(proc, 'sistema_nome') or ''
        sistema_link = get_val(proc, 'sistema_link') or ''

        texto_busca = f"{cod_novo} {num_proc} {cliente} {parte_contraria} {acao} {vara} {sistema_nome}".lower()
        if termo_busca and termo_busca not in texto_busca:
            continue

        encontrados += 1

        if sistema_link and str(sistema_link).strip():
            url = str(sistema_link).strip()
            if not url.startswith(('http://', 'https://')): url = 'https://' + url
            btn_link_html = f'''<a href="{url}" target="_blank" style="display:inline-block; margin-top:8px; padding:8px 12px; background-color:#0d6efd; color:white; border-radius:6px; font-size:0.85rem; font-weight:bold; text-decoration:none;">🔗 Acessar {sistema_nome or "Sistema"}</a>'''
        else:
            btn_link_html = ''

        proc_num_line = f"<p><strong>Nº Processo:</strong> {num_proc}</p>" if num_proc else ""
        sistema_line = f"<p><strong>Sistema:</strong> {sistema_nome}</p>" if sistema_nome else ""

        cards_html += f"""
        <div class="card">
            <h3>📁 {cod_novo}</h3>
            {proc_num_line}
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Parte Contrária:</strong> {parte_contraria}</p>
            <p><strong>Ação:</strong> {acao}</p>
            <p><strong>Vara/Juízo:</strong> {vara}</p>
            {sistema_line}
            {btn_link_html}
        </div>
        """

    if encontrados == 0:
        cards_html = "<p style='padding:15px; background:white; border-radius:8px;'>Nenhum processo encontrado.</p>"

    conteudo = f"""
    <form class="search-form" action="/processos" method="get">
        <input type="text" name="q" value="{q}" placeholder="🔍 Buscar por código, processo, cliente, vara...">
        <button type="submit">Buscar</button>
    </form>
    <div>
        {cards_html}
    </div>
    """

    erro_banner = f'<div class="erro-banner">⚠️ Erro no Banco: {erro_db}</div>' if erro_db else ""
    html = PAGE_TEMPLATE.replace("{{TITULO_PAGINA}}", "Gestão de Processos")\
                        .replace("{{INFO_BANNER}}", "")\
                        .replace("{{ERRO_BANNER}}", erro_banner)\
                        .replace("{{CONTEUDO_PAGINA}}", conteudo)
    return HTMLResponse(content=html)

# MÓDULO 4: CLIENTES (Busca Nativa do Servidor)
@app.get("/clientes", response_class=HTMLResponse)
async def pagina_clientes(q: str = ""):
    clientes = []
    processos = []
    erro_db = ""
    conn = None
    termo_busca = q.strip().lower()
    try:
        conn = get_db_connection()
        clientes = fetch_all_dict(conn, 'SELECT * FROM "Clientes" ORDER BY "Nomecli" ASC;')
        processos = fetch_all_dict(conn, 'SELECT "ProcessoNovoCod1", "Processo", "CodCli" FROM "Processos";')
    except Exception as e:
        erro_db = str(e)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

    processos_por_cliente = {}
    for proc in processos:
        cod_cli = proc.get('CodCli')
        if cod_cli:
            if cod_cli not in processos_por_cliente:
                processos_por_cliente[cod_cli] = []
            processos_por_cliente[cod_cli].append(proc)

    cards_html = ""
    encontrados = 0
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

        texto_busca = f"{nome} {doc} {rg} {tel} {endereco_completo}".lower()
        if termo_busca and termo_busca not in texto_busca:
            continue

        encontrados += 1

        procs_cli = processos_por_cliente.get(cod_cli, [])
        procs_html = ""
        if procs_cli:
            for p_item in procs_cli:
                c_num = get_val(p_item, 'ProcessoNovoCod1') or 'Sem Cód.'
                num_p = get_val(p_item, 'Processo') or ''
                ident = c_num
                if num_p and num_p != c_num: ident += f" ({num_p})"
                procs_html += f"<li><strong>{ident}</strong></li>"
            procs_html = f"<ul class='sub-proc-list'>{procs_html}</ul>"
        else:
            procs_html = "<p style='font-size:0.85rem; color:#6c757d; margin-top:4px;'>Nenhum processo vinculado.</p>"

        cards_html += f"""
        <div class="card">
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

    if encontrados == 0:
        cards_html = "<p style='padding:15px; background:white; border-radius:8px;'>Nenhum cliente encontrado.</p>"

    conteudo = f"""
    <form class="search-form" action="/clientes" method="get">
        <input type="text" name="q" value="{q}" placeholder="🔍 Buscar por nome, CPF/CNPJ, cidade...">
        <button type="submit">Buscar</button>
    </form>
    <div>
        {cards_html}
    </div>
    """

    erro_banner = f'<div class="erro-banner">⚠️ Erro no Banco: {erro_db}</div>' if erro_db else ""
    html = PAGE_TEMPLATE.replace("{{TITULO_PAGINA}}", "Cadastro de Clientes")\
                        .replace("{{INFO_BANNER}}", "")\
                        .replace("{{ERRO_BANNER}}", erro_banner)\
                        .replace("{{CONTEUDO_PAGINA}}", conteudo)
    return HTMLResponse(content=html)

# ------------------------------------------------------------------
# AÇÕES
# ------------------------------------------------------------------
@app.post("/agenda/atualizar/{item_id}")
async def atualizar_observacao_agenda(item_id: int, observacoes: str = Form(None)):
    conn = None
    try:
        conn = get_db_connection()
        texto_obs = observacoes.strip() if observacoes and observacoes.strip() else None
        query = 'UPDATE "Agenda" SET "Observações" = :obs WHERE "Código" = :id'
        conn.run(query, obs=texto_obs, id=item_id)
        return RedirectResponse(url="/agenda?msg=Observação+salva+com+sucesso!", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/agenda?msg=Erro+ao+salvar:+{str(e)}", status_code=303)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass

@app.post("/prazos/sincronizar-djen")
def sincronizar_djen():
    oab = "182981"
    uf = "SP"
    
    # Define o intervalo de datas (Data de hoje para a busca)[span_2](start_span)[span_2](end_span)
    hoje = date.today().strftime("%Y-%m-%d")
    data_inicio = hoje
    data_fim = hoje

    # URL ajustada com os parâmetros obrigatórios descobertos no aplicativo móvel do PJe[span_3](start_span)[span_3](end_span)
    url = (
        f"https://comunicaapi.pje.jus.br/api/v1/comunicacao"
        f"?numeroOab={oab}"
        f"&ufOab={uf}"
        f"&dataDisponibilizacaoInicio={data_inicio}"
        f"&dataDisponibilizacaoFim={data_fim}"
        f"&pagina=1"
        f"&itensPorPagina=100"
    )
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://comunica.pje.jus.br',
        'Referer': 'https://comunica.pje.jus.br/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    
    try:
        # Usa curl_cffi simulando Chrome para evitar bloqueio TLS / HTTP 403
        response = requests.get(
            url, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15
        )
        
        if response.status_code == 403:
            msg_erro = "Erro+403:+Acesso+negado+pelo+PJe.+A+API+bloqueou+a+requisição."
            return RedirectResponse(url=f"/prazos?erro={msg_erro}", status_code=303)
            
        response.raise_for_status()
        payload = response.json()
        items = payload.get('items', [])
        
    except Exception as e:
        msg_erro = f"Erro+ao+consultar+DJEN:+{str(e)}"
        return RedirectResponse(url=f"/prazos?erro={msg_erro}", status_code=303)
        
    novos_registros = 0
    duplicados = 0

    conn = get_db_connection()
    try:
        for item in items:
            num_processo = item.get('numero_processo', '')
            data_disp = item.get('data_disponibilizacao', '')
            texto_pub = item.get('texto', '')
            tipo_comunicacao = item.get('nomeClasse', 'Intimação')

            if not num_processo or not data_disp:
                continue

            dt_pub, dt_cumprimento = calcular_prazo_5_dias_uteis(data_disp)

            res = conn.run(
                'SELECT 1 FROM "Publicações" WHERE "ProcessoNovoCod1" = :proc AND "Data" = :data_pub',
                proc=num_processo,
                data_pub=dt_pub
            )
            if res:
                duplicados += 1
                continue

            conn.run(
                '''
                INSERT INTO "Publicações" 
                ("ProcessoNovoCod1", "Data", "DataCumprimento", "Publicação", "Manifestação", "Cumprido")
                VALUES (:proc, :data_pub, :data_cump, :texto, :tipo, :cumprido)
                ''',
                proc=num_processo,
                data_pub=dt_pub,
                data_cump=dt_cumprimento,
                texto=texto_pub,
                tipo=tipo_comunicacao,
                cumprido=False
            )
            novos_registros += 1

    except Exception as e:
        msg_erro = f"Erro+ao+salvar+publicações:+{str(e)}"
        return RedirectResponse(url=f"/prazos?erro={msg_erro}", status_code=303)
    finally:
        try: conn.close()
        except Exception: pass

    msg_sucesso = f"Sincronização+concluída!+{novos_registros}+novas+publicações+inseridas.+({duplicados}+já+existiam+no+banco)."
    return RedirectResponse(url=f"/prazos?msg={msg_sucesso}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
