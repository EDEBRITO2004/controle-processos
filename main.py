# -*- coding: utf-8 -*-
import os
from datetime import date
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pg8000.native

app = FastAPI()

# Configuração de templates (Jinja2)
templates = Jinja2Templates(directory="templates")

# Conexão com o banco de dados PostgreSQL via pg8000
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    # Ajuste os parâmetros caso utilize variáveis de ambiente individuais
    if DATABASE_URL:
        return pg8000.native.Connection(dsn=DATABASE_URL)
    return pg8000.native.Connection(
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        database=os.environ.get("DB_NAME", "controle_processos")
    )

# ---------------------------------------------------------
# ROTA PRINCIPAL: Lista os compromissos da agenda
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    conn = get_db_connection()
    try:
        # Busca os eventos garantindo que a coluna observacoes seja retornada
        query = """
            SELECT id, data_evento, descricao, tipo, observacoes 
            FROM agenda 
            ORDER BY data_evento ASC
        """
        rows = conn.run(query)
        
        # Mapeia os resultados garantindo string vazia caso observacoes seja NULL
        eventos = []
        for r in rows:
            eventos.append({
                "id": r[0],
                "data_evento": r[1],
                "descricao": r[2],
                "tipo": r[3],
                "observacoes": r[4] if r[4] is not None else ""
            })
            
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "eventos": eventos}
        )
    finally:
        conn.close()

# ---------------------------------------------------------
# ROTA DE ATUALIZAÇÃO: Grava/Edita as observações no banco
# ---------------------------------------------------------
@app.post("/agenda/atualizar/{evento_id}")
def atualizar_observacao(evento_id: int, observacoes: str = Form(None)):
    conn = get_db_connection()
    try:
        # Trata o texto digitado (se for apenas espaços vazios, salva como NULL)
        texto_obs = observacoes.strip() if observacoes and observacoes.strip() else None

        # Executa a atualização na tabela agenda
        conn.run(
            "UPDATE agenda SET observacoes = :obs WHERE id = :id",
            obs=texto_obs,
            id=evento_id
        )
        return RedirectResponse(url="/", status_code=303)
    finally:
        conn.close()

# ---------------------------------------------------------
# EXECUÇÃO LOCAL (Apenas para rodar no PyDroid/PC)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
