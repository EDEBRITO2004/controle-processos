import os
import re
import datetime
import imaplib
import email
from email.header import decode_header
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Controle jurídico - Ede Brito")

# ------------------------------------------------------------------
# CONFIGURAÇÕES DO BANCO DE DADOS E E-MAIL
# ------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:senha@localhost:5432/nome_banco")

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_USER = os.getenv("EMAIL_USER", "seu_email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "sua_senha_de_app")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ------------------------------------------------------------------
# ROTINA DE LEITURA DE E-MAILS (PJe Publicações)
# ------------------------------------------------------------------
def ler_emails_e_salvar():
    novos_registros = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Busca e-mails não lidos (UNSEEN) com o assunto "PJe" ou "Publicação"
        status, messages = mail.search(None, '(UNSEEN SUBJECT "PJe")')
        email_ids = messages[0].split()

        if not email_ids:
            mail.logout()
            return 0

        conn = get_db_connection()
        cur = conn.cursor()

        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decodificar Assunto
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")

                    # Extrair corpo da mensagem
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    # Extrair Número do Processo (Exemplo de Regex para padrão CNJ)
                    match_processo = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', body)
                    num_processo = match_processo.group(0) if match_processo else "Desconhecido"

                    # Salvar no banco
                    cur.execute(
                        """
                        INSERT INTO publicacoes (processo, assunto, conteudo, data_recebimento)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (num_processo, subject, body, datetime.datetime.now())
                    )
                    novos_registros += 1

        conn.commit()
        cur.close()
        conn.close()
        mail.logout()
    except Exception as e:
        print(f"Erro ao processar e-mails: {e}")

    return novos_registros


# ------------------------------------------------------------------
# TEMPLATES HTML
# ------------------------------------------------------------------

# 1. TELA INICIAL (SPLASH PAGE COM A BALANÇA DOURADA)
TELA_INICIAL_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PJe Publicações - Ede Brito</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body {
            background: linear-gradient(180deg, #0b488a 0%, #1a73e8 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .scale-container { margin-bottom: 25px; }
        h1 { font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.5px; }
        p.subtitle { font-size: 1.1rem; font-style: italic; color: #ffcc00; opacity: 0.9; margin-bottom: 45px; }
        .btn-consultar {
            background-color: #fbbc04;
            color: #1a1a1a;
            padding: 16px 36px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s, background-color 0.2s;
            display: inline-block;
        }
        .btn-consultar:active { transform: scale(0.97); }
    </style>
</head>
<body>

    <!-- Desenho da Balança em SVG -->
    <div class="scale-container">
        <svg width="140" height="140" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Topo e Haste Central -->
            <circle cx="50" cy="18" r="4" fill="#fbbc04" />
            <line x1="50" y1="22" x2="50" y2="70" stroke="#fbbc04" stroke-width="4" stroke-linecap="round" />
            <path d="M 38 78 L 50 70 L 62 78 Z" fill="#fbbc04" />

            <!-- Travessão Horizontal -->
            <line x1="28" y1="32" x2="72" y2="32" stroke="#fbbc04" stroke-width="4" stroke-linecap="round" />

            <!-- Prato Esquerdo -->
            <line x1="28" y1="32" x2="21" y2="48" stroke="#fbbc04" stroke-width="2" />
            <line x1="28" y1="32" x2="35" y2="48" stroke="#fbbc04" stroke-width="2" />
            <path d="M 19 48 Q 28 58 37 48" stroke="#fbbc04" stroke-width="3" fill="none" stroke-linecap="round" />

            <!-- Prato Direito -->
            <line x1="72" y1="32" x2="65" y2="48" stroke="#fbbc04" stroke-width="2" />
            <line x1="72" y1="32" x2="79" y2="48" stroke="#fbbc04" stroke-width="2" />
            <path d="M 63 48 Q 72 58 81 48" stroke="#fbbc04" stroke-width="3" fill="none" stroke-linecap="round" />
        </svg>
    </div>

    <h1>PJe Publicações</h1>
    <p class="subtitle">por Ede Brito</p>

    <a href="/painel" class="btn-consultar">Consultar Publicações</a>

</body>
</html>"""


# 2. PAINEL GERAL (DASHBOARD)
PAINEL_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚖️ Painel Geral - Ede Brito</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, sans-serif; }
        body { background: #f4f6f9; color: #333; padding: 20px; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        h1 { color: #0b488a; }
        .back-link { text-decoration: none; color: #0b488a; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
        .card h3 { margin-bottom: 10px; font-size: 1.1rem; }
        .card .count { font-size: 2rem; font-weight: bold; color: #1a73e8; }
        .actions { margin-top: 30px; text-align: center; }
        .btn-sync { background-color: #1a73e8; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 1rem; text-decoration: none; display: inline-block; }
    </style>
</head>
<body>
    <header>
        <h1>⚖️ Painel de Controle Jurídico</h1>
        <a href="/" class="back-link">← Voltar à Tela Inicial</a>
    </header>

    <div class="grid">
        <div class="card">
            <h3>⏳ Prazos Pendentes</h3>
            <div class="count">{total_prazos}</div>
        </div>
        <div class="card">
            <h3>📆 Audiências</h3>
            <div class="count">{total_audiencias}</div>
        </div>
        <div class="card">
            <h3>📂 Publicações</h3>
            <div class="count">{total_publicacoes}</div>
        </div>
    </div>

    <div class="actions">
        <a href="/sincronizar-emails" class="btn-sync">🔄 Ler novos e-mails (PJe)</a>
    </div>
</body>
</html>"""


# ------------------------------------------------------------------
# ROTAS FASTAPI
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def tela_inicial():
    """Apresenta a landing page/splash com a balança desenhada."""
    return HTMLResponse(content=TELA_INICIAL_TEMPLATE)


@app.get("/painel", response_class=HTMLResponse)
async def painel():
    """Painel de controle com a contagem de registros do banco."""
    total_prazos = 0
    total_audiencias = 0
    total_publicacoes = 0

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM prazos WHERE status = 'Pendente';")
        total_prazos = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM audiencias;")
        total_audiencias = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM publicacoes;")
        total_publicacoes = cur.fetchone()['count']

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Aviso: Não foi possível obter contadores do banco de dados ({e})")

    html_renderizado = PAINEL_TEMPLATE.format(
        total_prazos=total_prazos,
        total_audiencias=total_audiencias,
        total_publicacoes=total_publicacoes
    )

    return HTMLResponse(content=html_renderizado)


@app.get("/sincronizar-emails")
async def sincronizar_emails():
    """Dispara a leitura dos e-mails e redireciona de volta para o painel."""
    ler_emails_e_salvar()
    return RedirectResponse(url="/painel")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
