from flask import Flask, render_template_string, request
import re
import html
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus
import webbrowser
from threading import Timer

app = Flask(__name__)

def buscar_dados_mock(oab="182981", uf="SP", dias_atras=5):
    hoje = date.today()
    inicio = hoje - timedelta(days=dias_atras)
    
    mock_response = {
        "total": 2,
        "pagina": 1,
        "itensPorPagina": 50,
        "totalPaginas": 1,
        "items": [
            {
                "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
                "tipo_comunicacao": "intimacao",
                "nome_classe": "Procedimento Comum Cível",
                "numero_processo": "1001234-56.2026.8.26.0236",
                "data_disponibilizacao": "2026-09-09",
                "meio": "D",
                "link": "https://pje.tjsp.jus.br/pje/Processo/ConsultaDocumento/listView.seam",
                "texto": "Processo 1001234-56.2026.8.26.0236. Fica a parte autora intimada para, no prazo de 15 dias, manifestar-se sobre a contestacao apresentada.",
                "siglaTribunal": "TJSP",
                "destinatario": {
                    "nome": "EDE BRITO",
                    "numeroOab": "182981",
                    "ufOab": "SP",
                    "tipo": "ADVOGADO"
                },
                "orgao_julgador": {
                    "nome": "1ª Vara Cível da Comarca de Ibitinga",
                    "codigo": "0236",
                    "siglaTribunal": "TJSP"
                }
            },
            {
                "id": "b2c3d4e5-f6a7-48b9-c0d1-e2f3a4b5c6d7",
                "tipo_comunicacao": "intimacao",
                "nome_classe": "Ação Penal - Procedimento Ordinário",
                "numero_processo": "1500987-65.2026.8.26.0236",
                "data_disponibilizacao": "2026-09-08",
                "meio": "D",
                "link": None,
                "texto": "Processo CRIMINAL 1500987-65.2026.8.26.0236. Designo AUDIENCIA de instrucao e julgamento para o dia 25/10/2026 as 14:00 horas.",
                "siglaTribunal": "TJSP",
                "destinatario": {
                    "nome": "EDE BRITO",
                    "numeroOab": "182981",
                    "ufOab": "SP",
                    "tipo": "ADVOGADO"
                },
                "orgao_julgador": {
                    "nome": "Vara Criminal da Comarca de Ibitinga",
                    "codigo": "0237",
                    "siglaTribunal": "TJSP"
                }
            }
        ]
    }
    return mock_response.get("items", []), inicio.strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def destacar_termos(texto):
    padrao = r'\b(audiencia|sentenca|recurso|pericia|prazo|despacho|acordao|liminar)\b'
    texto_destacado = re.sub(
        padrao, 
        r'<mark style="background-color: #fef08a; padding: 2px 4px; border-radius: 4px; font-weight: bold; color: #854d0e;">\1</mark>', 
        texto, 
        flags=re.IGNORECASE
    )
    return texto_destacado

@app.route("/")
def home():
    oab = request.args.get("oab", "182981")
    uf = request.args.get("uf", "SP")
    
    items, dt_inicio, dt_fim = buscar_dados_mock(oab=oab, uf=uf, dias_atras=5)
    
    nome_advogado = "Ede Brito" if oab == "182981" and uf == "SP" else f"Consulta OAB {oab}/{uf}"
    
    cards_html = ""
    if not items:
        cards_html = f'<div class="card empty-card"><p>ℹ️ Nenhuma publicação localizada para OAB {oab}/{uf} no período ({dt_inicio} a {dt_fim}).</p></div>'
    else:
        for i, item in enumerate(items, 1):
            texto_raw = item.get("texto", "")
            data_disp_str = item.get("data_disponibilizacao")
            
            texto_decod = html.unescape(texto_raw)
            texto_sem_tags = re.sub(r'<[^>]+>', ' ', texto_decod)
            texto_limpo = '\n'.join([l.strip() for l in texto_sem_tags.splitlines() if l.strip()])
            
            match_cnj = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto_limpo)
            cnj = match_cnj.group(0) if match_cnj else "Não localizado"
            
            match_prazo = re.search(r'prazo\s+(?:de\s+)?(\d+)\s*dias?', texto_limpo, re.IGNORECASE)
            dias = int(match_prazo.group(1)) if match_prazo else 5
            
            e_criminal = "CRIMINAL" in texto_limpo.upper()
            e_audiencia = "AUDIENCIA" in texto_limpo.upper()
            rito = "Criminal (Dias Corridos)" if e_criminal else "Cível / Trabalhista (Dias Úteis)"
            
            tipo_evento = "Audiência" if e_audiencia else "Prazo"
            icone_agenda = "📆" if e_audiencia else "⏳"
            
            dt_disp = datetime.strptime(data_disp_str, "%Y-%m-%d") if data_disp_str else datetime.now()
            dt_pub = dt_disp + timedelta(days=1)
            
            texto_formatado_html = destacar_termos(html.escape(texto_limpo))
            texto_url = quote_plus(texto_limpo[:300])
            
            cards_html += f'''
            <div class="card">
                <div class="card-header">
                    <span class="badge">#{i}</span>
                    <span class="cnj">{cnj}</span>
                </div>
                <div class="info-group">
                    <div class="info-item"><b>Rito:</b> {rito}</div>
                    <div class="info-item"><b>Prazo:</b> <span class="highlight">{dias} dias</span></div>
                    <div class="info-item"><b>Disponibilização:</b> {dt_disp.strftime("%d/%m/%Y")} &nbsp;|&nbsp; <b>Publicação:</b> {dt_pub.strftime("%d/%m/%Y")}</div>
                </div>
                <details>
                    <summary>📄 Ver Teor Completo da Intimação</summary>
                    <pre id="texto-{i}">{texto_formatado_html}</pre>
                    <div class="action-buttons">
                        <button class="btn-action" onclick="copiarTexto('{i}')">📋 Copiar Texto</button>
                        <a class="btn-action btn-calendar" href="https://calendar.google.com/calendar/render?action=TEMPLATE&text={icone_agenda}+{tipo_evento}+-+Proc.+{cnj}&details={texto_url}..." target="_blank">
                            {icone_agenda} Add à Agenda ({tipo_evento})
                        </a>
                    </div>
                </details>
            </div>
            '''

    html_template = f'''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Publicações PJe</title>
        <style>
            :root {{
                --blue-primary: #1e3a8a;
                --blue-secondary: #2563eb;
                --blue-light: #eff6ff;
                --blue-accent: #0284c7;
                --text-dark: #1e293b;
                --text-muted: #64748b;
                --bg-main: #f8fafc;
                --white: #ffffff;
                --border-color: #e2e8f0;
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg-main); color: var(--text-dark); margin: 0; padding: 12px; }}
            .header {{ background-color: var(--white); padding: 16px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid var(--border-color); }}
            .header-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
            .adv-profile {{ font-size: 16px; font-weight: 800; color: var(--blue-primary); }}
            .oab-badge {{ background-color: var(--blue-light); color: var(--blue-secondary); font-size: 12px; padding: 3px 8px; border-radius: 6px; font-weight: 700; margin-left: 6px; }}
            .sub {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}
            .search-box {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color); display: flex; gap: 8px; flex-wrap: wrap; }}
            input, select {{ padding: 8px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 13px; }}
            input[type="text"] {{ width: 100px; flex-grow: 1; }}
            .btn {{ background-color: var(--blue-secondary); color: var(--white); padding: 8px 14px; border: none; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 13px; cursor: pointer; }}
            .card {{ background-color: var(--white); border-radius: 12px; padding: 16px; margin-bottom: 14px; border: 1px solid var(--border-color); border-left: 5px solid var(--blue-secondary); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }}
            .empty-card {{ text-align: center; color: var(--text-muted); border-left: 5px solid var(--blue-accent); }}
            .card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }}
            .badge {{ background-color: var(--blue-light); color: var(--blue-secondary); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px; }}
            .cnj {{ font-weight: 700; font-size: 15px; color: var(--blue-primary); }}
            .info-group {{ font-size: 13px; color: var(--text-dark); line-height: 1.5; }}
            .info-item {{ margin-bottom: 4px; }}
            .highlight {{ color: var(--blue-secondary); font-weight: 700; }}
            details {{ margin-top: 12px; background-color: var(--blue-light); border: 1px solid #dbeafe; padding: 10px; border-radius: 8px; }}
            summary {{ font-weight: 600; cursor: pointer; color: var(--blue-secondary); font-size: 13px; }}
            pre {{ font-family: "Courier New", Courier, monospace; font-size: 11px; white-space: pre-wrap; word-wrap: break-word; color: #334155; margin-top: 10px; background-color: var(--white); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); }}
            .action-buttons {{ display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }}
            .btn-action {{ background-color: var(--white); border: 1px solid var(--blue-secondary); color: var(--blue-secondary); padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: none; }}
            .btn-calendar {{ background-color: var(--blue-light); }}
        </style>
        <script>
            function copiarTexto(id) {{
                var element = document.getElementById('texto-' + id);
                var text = element.innerText || element.textContent;
                navigator.clipboard.writeText(text).then(function() {{
                    alert('Teor da intimação copiado!');
                }}).catch(function(err) {{
                    alert('Erro ao copiar: ' + err);
                }});
            }}
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-top">
                <div>
                    <div class="adv-profile">👨‍⚖️ {nome_advogado} <span class="oab-badge">OAB-{uf} {oab}</span></div>
                    <div class="sub">Período: {dt_inicio} a {dt_fim} | MOCK - Dados de teste</div>
                </div>
                <a href="/?oab={oab}&uf={uf}" class="btn">🔄 Atualizar</a>
            </div>
            <form class="search-box" action="/" method="GET">
                <input type="text" name="oab" value="{oab}" placeholder="Nº OAB" required>
                <select name="uf">
                    <option value="SP" {"selected" if uf == "SP" else ""}>SP</option>
                    <option value="PR" {"selected" if uf == "PR" else ""}>PR</option>
                    <option value="RJ" {"selected" if uf == "RJ" else ""}>RJ</option>
                    <option value="MG" {"selected" if uf == "MG" else ""}>MG</option>
                    <option value="RS" {"selected" if uf == "RS" else ""}>RS</option>
                    <option value="SC" {"selected" if uf == "SC" else ""}>SC</option>
                </select>
                <button type="submit" class="btn">Buscar</button>
            </form>
        </div>
        {cards_html}
    </body>
    </html>
    '''
    return render_template_string(html_template)

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1.5, abrir_navegador).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
