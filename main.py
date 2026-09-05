import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Obtém a URL do banco de dados das variáveis de ambiente do Render
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://controle_processos_lnju_user:J7I5L81oYnOyPcxRIO5FqBkx1RP0HQoX@dpg-dac0l9jtqb8s73dqjh00-a.virginia-postgres.render.com/controle_processos_lnju"
)

def get_db_connection():
    # Adiciona sslmode='require' para garantir a conexão com o Render
    return psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=RealDictCursor)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    clientes, processos, agenda = [], [], []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Busca Clientes
        try:
            cursor.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 20;")
            clientes = cursor.fetchall()
        except Exception as e:
            conn.rollback()

        # Busca Processos
        try:
            cursor.execute("SELECT * FROM processos ORDER BY id DESC LIMIT 20;")
            processos = cursor.fetchall()
        except Exception as e:
            conn.rollback()

        # Busca Agenda
        try:
            cursor.execute("SELECT * FROM agenda ORDER BY data_hora ASC LIMIT 20;")
            agenda = cursor.fetchall()
        except Exception as e:
            conn.rollback()

        cursor.close()
        conn.close()
    except Exception as err:
        print(f"Erro na conexão com a base de dados: {err}")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "clientes": clientes,
        "processos": processos,
        "agenda": agenda
    })
