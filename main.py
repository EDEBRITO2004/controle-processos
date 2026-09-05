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

@app.get("/", response_class=HTMLResponse)
async def home():
    info_html = ""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        # Lista todas as tabelas do banco de dados
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        
        info_html += "<h2>Tabelas encontradas no banco:</h2><ul>"
        for t in tables:
            t_name = t['table_name']
            info_html += f"<li><strong>{t_name}</strong></li>"
        info_html += "</ul>"

        cursor.close()
        conn.close()
    except Exception as err:
        info_html = f"<h2>Erro ao conectar:</h2><p>{err}</p>"

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Inspeção DB</title></head>
    <body style="font-family: sans-serif; padding: 20px;">
        {info_html}
    </body>
    </html>
    """)
