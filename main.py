"""
API Secundária - "Estante de Livros"
Responsável por persistir os livros que o usuário adicionou à sua estante
(status de leitura e nota), usando SQLite.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "estante.db")

app = FastAPI(
    title="API Secundária - Estante de Livros",
    description="Gerencia a estante pessoal de livros do usuário (CRUD + SQLite).",
    version="1.0.0",
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    diretorio = os.path.dirname(DB_PATH)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS estante (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_books_id TEXT,
            titulo TEXT NOT NULL,
            autores TEXT,
            capa_url TEXT,
            status TEXT NOT NULL DEFAULT 'quero_ler',
            nota INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class StatusLeitura(str, Enum):
    quero_ler = "quero_ler"
    lendo = "lendo"
    lido = "lido"


class LivroCreate(BaseModel):
    google_books_id: Optional[str] = None
    titulo: str
    autores: Optional[str] = None
    capa_url: Optional[str] = None
    status: StatusLeitura = StatusLeitura.quero_ler
    nota: Optional[int] = Field(default=None, ge=0, le=5)


class LivroUpdate(BaseModel):
    status: Optional[StatusLeitura] = None
    nota: Optional[int] = Field(default=None, ge=0, le=5)


class Livro(LivroCreate):
    id: int


@app.get("/", tags=["Status"])
def raiz():
    return {"servico": "API Secundária - Estante de Livros", "status": "online"}


@app.get("/estante", response_model=List[Livro], tags=["Estante"])
def listar_estante(status: Optional[StatusLeitura] = None):
    """Lista todos os livros da estante. Filtro opcional por status."""
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM estante WHERE status = ?", (status.value,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM estante").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/estante/{livro_id}", response_model=Livro, tags=["Estante"])
def obter_livro(livro_id: int):
    """Retorna um livro específico da estante."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM estante WHERE id = ?", (livro_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado na estante")
    return dict(row)


@app.post("/estante", response_model=Livro, status_code=201, tags=["Estante"])
def adicionar_livro(livro: LivroCreate):
    """Adiciona um novo livro à estante."""
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO estante (google_books_id, titulo, autores, capa_url, status, nota)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            livro.google_books_id,
            livro.titulo,
            livro.autores,
            livro.capa_url,
            livro.status.value,
            livro.nota,
        ),
    )
    conn.commit()
    novo_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM estante WHERE id = ?", (novo_id,)).fetchone()
    conn.close()
    return dict(row)


@app.put("/estante/{livro_id}", response_model=Livro, tags=["Estante"])
def atualizar_livro(livro_id: int, dados: LivroUpdate):
    """Atualiza o status de leitura e/ou a nota de um livro da estante."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM estante WHERE id = ?", (livro_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Livro não encontrado na estante")

    novo_status = dados.status.value if dados.status else row["status"]
    nova_nota = dados.nota if dados.nota is not None else row["nota"]

    conn.execute(
        "UPDATE estante SET status = ?, nota = ? WHERE id = ?",
        (novo_status, nova_nota, livro_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM estante WHERE id = ?", (livro_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/estante/{livro_id}", status_code=204, tags=["Estante"])
def remover_livro(livro_id: int):
    """Remove um livro da estante."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM estante WHERE id = ?", (livro_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Livro não encontrado na estante")
    conn.execute("DELETE FROM estante WHERE id = ?", (livro_id,))
    conn.commit()
    conn.close()
    return None
