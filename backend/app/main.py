"""API FastAPI do controle de logística (portaria + balança)."""

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .anpr.plate import normalizar_placa
from .anpr.recognizer import get_recognizer
from .balanca.ao_vivo import BalancaAoVivo
from .config import settings
from .db import get_db, init_db
from . import models
from .schemas import (
    BalancaEstado,
    BalancaPesarOut,
    EventoPlacaOut,
    MovimentacaoOut,
    PesagemIn,
    PesagemOut,
    ReconhecerResponse,
    ReconhecimentoOut,
)
from .services.peso_service import registrar_pesagem
from .services.plate_service import registrar_evento


def _loop_balanca(balanca: BalancaAoVivo, stop: threading.Event) -> None:
    while not stop.is_set():
        balanca.tick()
        time.sleep(0.2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.imagens_dir.mkdir(parents=True, exist_ok=True)

    balanca = BalancaAoVivo()
    app.state.balanca = balanca
    stop = threading.Event()
    app.state.balanca_stop = stop
    thread = threading.Thread(target=_loop_balanca, args=(balanca, stop), daemon=True)
    thread.start()

    yield

    stop.set()


app = FastAPI(title="Controle Logística", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _resolver_ponto(db: Session, ponto_codigo: str) -> models.Ponto:
    ponto = db.execute(
        select(models.Ponto).where(models.Ponto.codigo == ponto_codigo)
    ).scalar_one_or_none()
    if ponto is None:
        raise HTTPException(status_code=404, detail=f"Ponto '{ponto_codigo}' não encontrado")
    return ponto


def _salvar_imagem(conteudo: bytes) -> str:
    nome = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.jpg"
    caminho = settings.imagens_dir / nome
    caminho.write_bytes(conteudo)
    return str(caminho)


@app.post("/placas/reconhecer", response_model=ReconhecerResponse)
async def reconhecer_placa(
    arquivo: UploadFile = File(...),
    ponto_codigo: str = Form(...),
    salvar: bool = Form(True),
    db: Session = Depends(get_db),
) -> ReconhecerResponse:
    ponto = _resolver_ponto(db, ponto_codigo)

    conteudo = await arquivo.read()
    arr = np.frombuffer(conteudo, dtype=np.uint8)
    imagem = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if imagem is None:
        raise HTTPException(status_code=400, detail="Imagem inválida")

    melhor = get_recognizer().reconhecer_melhor(imagem)

    imagem_path = _salvar_imagem(conteudo) if salvar else None
    resposta: list[ReconhecimentoOut] = []
    if melhor is not None:
        evento_id = None
        if salvar:
            evento = registrar_evento(
                db,
                placa=melhor["placa"],
                confianca=melhor["confianca"],
                raw=melhor["raw"],
                planta_id=ponto.planta_id,
                ponto_id=ponto.id,
                imagem_path=imagem_path,
            )
            evento_id = evento.id
        resposta.append(
            ReconhecimentoOut(
                placa=melhor["placa"].valor,
                formato=melhor["placa"].formato,
                confianca=melhor["confianca"],
                raw=melhor["raw"],
                evento_id=evento_id,
            )
        )

    return ReconhecerResponse(candidatos=resposta, total=len(resposta))


@app.get("/eventos", response_model=list[EventoPlacaOut])
def listar_eventos(
    placa: str | None = None,
    ponto_codigo: str | None = None,
    limite: int = 50,
    db: Session = Depends(get_db),
) -> list[EventoPlacaOut]:
    stmt = select(models.EventoPlaca).order_by(models.EventoPlaca.capturado_em.desc())
    if placa:
        stmt = stmt.where(models.EventoPlaca.placa == placa.upper())
    if ponto_codigo:
        stmt = stmt.join(models.Ponto).where(models.Ponto.codigo == ponto_codigo)
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))


@app.get("/pesagens", response_model=list[PesagemOut])
def listar_pesagens(
    ponto_codigo: str | None = None,
    limite: int = 50,
    db: Session = Depends(get_db),
) -> list[PesagemOut]:
    stmt = select(models.Pesagem).order_by(models.Pesagem.capturado_em.desc())
    if ponto_codigo:
        stmt = stmt.join(models.Ponto).where(models.Ponto.codigo == ponto_codigo)
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))


@app.post("/pesagens", response_model=PesagemOut)
def criar_pesagem(body: PesagemIn, db: Session = Depends(get_db)) -> PesagemOut:
    placa = normalizar_placa(body.placa)
    if placa is None:
        raise HTTPException(status_code=422, detail="Placa inválida")
    ponto = _resolver_ponto(db, body.ponto_codigo)
    return registrar_pesagem(
        db,
        placa=placa.valor,
        peso=body.peso,
        desvio=None,
        amostras=None,
        planta_id=ponto.planta_id,
        ponto_id=ponto.id,
    )


@app.get("/movimentacoes", response_model=list[MovimentacaoOut])
def listar_movimentacoes(
    status: str | None = None,
    placa: str | None = None,
    limite: int = 50,
    db: Session = Depends(get_db),
) -> list[MovimentacaoOut]:
    stmt = (
        select(models.Movimentacao)
        .options(selectinload(models.Movimentacao.veiculo))
        .order_by(models.Movimentacao.criado_em.desc())
    )
    if status:
        stmt = stmt.where(models.Movimentacao.status == status)
    if placa:
        stmt = stmt.join(models.Veiculo).where(models.Veiculo.placa == placa.upper())
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))


@app.get("/movimentacoes/abertas", response_model=list[MovimentacaoOut])
def listar_movimentacoes_abertas(
    db: Session = Depends(get_db),
) -> list[MovimentacaoOut]:
    stmt = (
        select(models.Movimentacao)
        .options(selectinload(models.Movimentacao.veiculo))
        .where(models.Movimentacao.status == "aberta")
        .order_by(models.Movimentacao.criado_em)
    )
    return list(db.scalars(stmt))


@app.websocket("/ws/peso")
async def ws_peso(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(app.state.balanca.estado())
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass


@app.get("/balanca/estado", response_model=BalancaEstado)
def balanca_estado() -> BalancaEstado:
    return app.state.balanca.estado()


def _decodificar_imagem(conteudo: bytes) -> np.ndarray:
    arr = np.frombuffer(conteudo, dtype=np.uint8)
    imagem = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if imagem is None:
        raise HTTPException(status_code=400, detail="Imagem inválida")
    return imagem


@app.post("/balanca/pesar", response_model=BalancaPesarOut)
async def balanca_pesar(
    arquivo: UploadFile = File(...),
    ponto_codigo: str = Form("BALANCA"),
    db: Session = Depends(get_db),
) -> BalancaPesarOut:
    ponto = _resolver_ponto(db, ponto_codigo)
    conteudo = await arquivo.read()
    imagem = _decodificar_imagem(conteudo)
    melhor = get_recognizer().reconhecer_melhor(imagem)

    estado = app.state.balanca.estado()
    peso = estado["peso_estavel"] if estado["peso_estavel"] is not None else estado["peso_atual"]

    if melhor is None:
        return BalancaPesarOut(
            placa=None, formato=None, confianca=None,
            peso=peso, desvio=estado["desvio"],
            pesagem_id=None, movimentacao_id=None,
            movimentacao_status=None, movimentacao_tipo=None,
        )

    placa = melhor["placa"]
    pesagem = registrar_pesagem(
        db,
        placa=placa.valor,
        peso=peso,
        desvio=estado["desvio"],
        amostras=25,
        planta_id=ponto.planta_id,
        ponto_id=ponto.id,
    )
    mov = db.get(models.Movimentacao, pesagem.movimentacao_id)
    return BalancaPesarOut(
        placa=placa.valor,
        formato=placa.formato,
        confianca=melhor["confianca"],
        peso=peso,
        desvio=estado["desvio"],
        pesagem_id=pesagem.id,
        movimentacao_id=pesagem.movimentacao_id,
        movimentacao_status=mov.status if mov else None,
        movimentacao_tipo=mov.tipo if mov else None,
    )


settings.static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")
