import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Pega a URL do banco do Render (ou usa a sua URL direta se configurada)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://controle_processos_lnju_user:J7I5L81oYnOyPcxRIO5FqBkx1RP0HQoX@dpg-dac0l9jtqb8s73dqjh00-a.virginia-postgres.render.com/controle_processos_lnju")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Busca os registros de cada tabela (ajuste os nomes das tabelas se necessário)
    cursor.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 20;")
    clientes = cursor.fetchall()

    cursor.execute("SELECT * FROM processos ORDER BY id DESC LIMIT 20;")
    processos = cursor.fetchall()

    cursor.execute("SELECT * FROM agenda ORDER BY data_hora ASC LIMIT 20;")
    agenda = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "clientes": clientes,
        "processos": processos,
        "agenda": agenda
    })
  
