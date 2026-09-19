from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Lock
from time import monotonic, perf_counter

import structlog
import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agenda.application.calcular_comissao_agendamento import CalcularComissaoAgendamento
from agenda.application.relatorio_comissao import gerar_relatorio_comissao
from agenda.application.criar_agendamento import CriarAgendamento
from agenda.application.criar_disponibilidade import CriarDisponibilidade
from agenda.application.descobrir_ofertas import DescobrirOfertas
from agenda.application.criar_lembrete_notificacao import CriarLembreteNotificacao
from agenda.application.criar_membership import CriarMembership
from agenda.application.criar_notificacao_agendamento import CriarNotificacaoAgendamento
from agenda.application.criar_organizacao import CriarOrganizacao
from agenda.application.criar_profissional_independente import (
    CriarProfissionalIndependente,
)
from agenda.application.criar_pacote import CriarPacote
from agenda.application.criar_programa_fidelidade import CriarProgramaFidelidade
from agenda.application.criar_servico import CriarServico
from agenda.application.consultar_operacao import (
    construir_estatisticas,
    construir_ficha,
)
from agenda.application.consultar_horarios_livres import ConsultarHorariosLivres
from agenda.application.registrar_atendimento_fidelidade import RegistrarAtendimentoFidelidade
from agenda.application.registrar_fidelidade_agendamento import RegistrarFidelidadeAgendamento
from agenda.application.resgatar_fidelidade import ResgatarFidelidade
from agenda.application.registrar_progresso_fidelidade import RegistrarProgressoFidelidade
from agenda.application.registrar_usuario import RegistrarUsuario
from agenda.application.sincronizar_usuario_identidade import SincronizarUsuarioIdentidade
from agenda.application.criar_organizacao_com_equipe import CriarOrganizacaoComEquipe
from agenda.application.enviar_media import EnviarMedia
from agenda.application.anexar_media import AnexarMedia
from agenda.adapters.keycloak_identity_adapter import (
    IdentidadeNaoAutenticadaError,
    KeycloakIdentityAdapter,
    ProvedorIdentidadeIndisponivelError,
)
from agenda.adapters.nominatim_geocodificacao_adapter import NominatimGeocodificacaoAdapter
from agenda.adapters.osrm_distancia_adapter import OSRMDistanciaAdapter
from agenda.adapters.webhook_notificacao_adapter import WebhookNotificacaoAdapter
from agenda.adapters.filesystem_storage_adapter import FilesystemStorageAdapter
from agenda.application.processar_notificacoes import ProcessarNotificacoesVencidas
from agenda.config import settings
from agenda.domain.agendamento import (
    Agendamento,
    CatalogoStatus,
    ItemAgendamento,
    StatusAgendamento,
    TransicaoStatus,
)
from agenda.domain.comissao import RegraComissao
from agenda.domain.disponibilidade import Disponibilidade, ExcecaoAgenda, IntervaloHorario, JanelaSemanal
from agenda.domain.endereco import Endereco
from agenda.domain.endereco import Cliente
from agenda.domain.exceptions import (
    AgendamentoInvalidoError,
    FidelidadeInvalidaError,
    TransicaoAgendamentoNaoPermitidaError,
)
from agenda.domain.fidelidade import (
    AplicacaoRecompensa,
    ProgramaFidelidade,
    ProgressoFidelidade,
    RecompensaFidelidade,
    aplicar_recompensa,
)
from agenda.domain.lembrete import ConfiguracaoLembrete, LembreteInvalidoError
from agenda.domain.membership import Membership
from agenda.domain.organizacao import Organizacao
from agenda.domain.pacote import Pacote
from agenda.domain.papel import Papel
from agenda.domain.catalogo_servico import NomeServico
from agenda.domain.servico import ModalidadeAtendimento, Servico
from agenda.domain.tipo_procedimento import TipoProcedimento
from agenda.domain.media import AnexoMedia, Media
from agenda.domain.usuario import Usuario
from agenda.infrastructure.agendamento_repository import AgendamentoRepository
from agenda.infrastructure.cliente_repository import ClienteRepository
from agenda.infrastructure.comissao_repository import RegraComissaoRepository
from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.disponibilidade_repository import DisponibilidadeRepository
from agenda.infrastructure.fidelidade_repository import (
    ProgramaFidelidadeRepository,
    ProgressoFidelidadeRepository,
    ResgateFidelidadeRepository,
)
from agenda.infrastructure.membership_repository import MembershipRepository, PapelRepository
from agenda.infrastructure.notificacao_repository import NotificacaoAgendamentoRepository
from agenda.infrastructure.organizacao_repository import OrganizacaoRepository
from agenda.infrastructure.pacote_repository import PacoteRepository
from agenda.infrastructure.servico_repository import NomeServicoRepository, ServicoRepository
from agenda.infrastructure.status_agendamento_repository import CatalogoStatusRepository
from agenda.infrastructure.tipo_procedimento_repository import TipoProcedimentoRepository
from agenda.infrastructure.media_repository import AnexoMediaRepository, MediaRepository
from agenda.infrastructure.usuario_repository import UsuarioRepository
from agenda.logging import configure_logging
from agenda.ports import DestinatarioNotificacao


configure_logging(settings.log_level, settings.log_format)
logger = structlog.get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Agenda API",
    version="0.1.0",
    description=(
        "API para gestão de organizações, usuários, serviços, agendamentos, "
        "disponibilidades, memberships, fidelidade e notificações do sistema de agenda. "
        "A documentação cobre o fluxo principal do MVP, incluindo criação, consulta, "
        "atualização, remoção e regras de negócio de agendamento e comissão.\n\n"
        "Endpoints públicos: GET /health, GET /organizacoes, GET /servicos e "
        "GET /disponibilidades, incluindo suas consultas por ID. Esses endpoints "
        "são protegidos por rate limit por endereço IP. Os demais endpoints exigem "
        "autenticação Keycloak e, quando aplicável, permissão RBAC."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Health", "description": "Endpoints de saúde e verificação do serviço."},
        {"name": "Usuários", "description": "Cadastro e consulta de usuários do sistema."},
        {"name": "Organizações", "description": "Gestão de organizações e endereços vinculados."},
        {"name": "Serviços", "description": "Serviços ofertados por profissionais e organizações."},
        {"name": "Memberships", "description": "Relacionamentos entre usuário, organização e papéis."},
        {"name": "Pacotes", "description": "Pacotes de serviços com duração e preço agregados."},
        {"name": "Disponibilidade", "description": "Definição de janelas de disponibilidade para agenda."},
        {"name": "Agendamentos", "description": "Fluxo principal de marcação e controle de agendamentos."},
        {"name": "Fidelidade", "description": "Programas de fidelidade e acompanhamento de progresso."},
        {"name": "Notificações", "description": "Geração de lembretes e notificações de agendamento."},
        {"name": "Comissão", "description": "Cálculo de comissão com base em regras e status do agendamento."},
        {"name": "Catálogos", "description": "Catálogos administráveis: papéis, status de agendamento e tipos de procedimento."},
        {"name": "Mídia", "description": "Upload e associação de arquivos binários (fotos, vídeos, documentos) a qualquer entidade."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_debug_request(request: Request, call_next):
    if settings.log_level.upper() != "DEBUG":
        return await call_next(request)

    started_at = perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (perf_counter() - started_at) * 1000
        safe_headers = {
            name: ("[REDACTED]" if name.lower() in {
                "authorization", "cookie", "set-cookie", "x-api-key",
            } else value)
            for name, value in request.headers.items()
        }
        logger.debug(
            "http_request_debug",
            method=request.method,
            path=str(request.url.path),
            query=dict(request.query_params),
            headers=safe_headers,
            status_code=response.status_code if response is not None else 500,
            duration_ms=round(elapsed_ms, 2),
        )

if not hasattr(app.state, "engine"):
    app.state.engine = criar_engine(
        settings.database_url,
        echo=settings.sql_echo or settings.log_level.upper() == "DEBUG",
    )
if not hasattr(app.state, "identity_adapter"):
    app.state.identity_adapter = KeycloakIdentityAdapter(
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
    )
if not hasattr(app.state, "armazenamento"):
    app.state.armazenamento = FilesystemStorageAdapter(
        raiz=settings.media_storage_path,
        base_url=settings.media_base_url,
    )
app.mount(
    "/media/arquivos",
    StaticFiles(directory=settings.media_storage_path),
    name="media_arquivos",
)


class PublicRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = Lock()

    def allow(self, client_key: str) -> bool:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = [
                timestamp
                for timestamp in self._requests.get(client_key, [])
                if timestamp > cutoff
            ]
            if len(timestamps) >= self.limit:
                self._requests[client_key] = timestamps
                return False
            timestamps.append(now)
            self._requests[client_key] = timestamps
            return True


if not hasattr(app.state, "public_rate_limiter"):
    app.state.public_rate_limiter = PublicRateLimiter(
        settings.public_rate_limit_per_minute
    )


def limitar_endpoint_publico(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    if not app.state.public_rate_limiter.allow(client_host):
        raise HTTPException(
            status_code=429,
            detail="limite de requisicoes publicas excedido",
            headers={"Retry-After": "60"},
        )


class UsuarioInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "keycloak",
                "subject": "cliente-123",
                "nome": "Maria Silva",
                "cpf": "12345678909",
                "email": "maria@example.com",
                "telefone": "+5511999999999",
            }
        }
    )
    provider: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    cpf: str | None = Field(default=None, pattern=r"^\d{11}$")
    email: str | None = None
    telefone: str | None = None


class UsuarioOutput(BaseModel):
    id: str
    provider: str
    subject: str
    nome: str
    cpf: str | None = None
    email: str | None = None
    telefone: str | None = None


class IdentidadeOutput(BaseModel):
    provider: str
    subject: str
    nome: str


class AcessoOrganizacaoOutput(BaseModel):
    membership_id: str
    organizacao_id: str | None = None
    ativo: bool
    papeis: list[str] = Field(default_factory=list)
    permissoes: list[str] = Field(default_factory=list)


class EnderecoInput(BaseModel):
    logradouro: str = Field(..., min_length=1)
    numero: str = Field(..., min_length=1)
    cidade: str = Field(..., min_length=1)
    estado: str = Field(..., min_length=1)
    cep: str = Field(..., min_length=1)


class EnderecoOutput(BaseModel):
    logradouro: str
    numero: str
    cidade: str
    estado: str
    cep: str


class ClienteInput(BaseModel):
    nome: str = Field(..., min_length=1)
    telefone: str | None = None
    email: str | None = None
    cpf: str | None = Field(default=None, pattern=r"^\d{11}$")
    segmento: str | None = None
    endereco: EnderecoInput | None = None


class ClienteOutput(BaseModel):
    id: str
    nome: str
    telefone: str | None = None
    email: str | None = None
    cpf: str | None = None
    segmento: str | None = None
    endereco: EnderecoOutput | None = None


class OrganizacaoInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Studio Bem Estar",
                "unipessoal": False,
                "endereco": {
                    "logradouro": "Rua das Flores",
                    "numero": "100",
                    "cidade": "Sao Paulo",
                    "estado": "SP",
                    "cep": "01000-000",
                },
            }
        }
    )
    nome: str = Field(..., min_length=1)
    unipessoal: bool = False
    endereco: EnderecoInput | None = None


class OrganizacaoOutput(BaseModel):
    id: str
    nome: str
    unipessoal: bool
    endereco: EnderecoOutput | None = None


class ProfissionalIndependenteInput(BaseModel):
    nome: str = Field(..., min_length=1)
    endereco: EnderecoInput | None = None


class ModalidadeInput(BaseModel):
    chave: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    ajuste_preco_fixo: Decimal | None = None
    ajuste_preco_percentual: Decimal | None = None
    ajuste_duracao_minutos: int = 0


class ModalidadeOutput(BaseModel):
    chave: str
    nome: str
    ajuste_preco_fixo: Decimal | None = None
    ajuste_preco_percentual: Decimal | None = None
    ajuste_duracao_minutos: int = 0


class ServicoInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Massagem relaxante",
                "categoria": "Bem-estar",
                "duracao_base_minutos": 60,
                "preco_base": "150.00",
                "profissional_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
                "modalidades": [
                    {
                        "chave": "presencial",
                        "nome": "Atendimento presencial",
                        "ajuste_preco_fixo": "0.00",
                        "ajuste_duracao_minutos": 0,
                    }
                ],
            }
        }
    )
    nome: str = Field(..., min_length=1)
    categoria: str = Field(..., min_length=1)
    categorias: list[str] = Field(default_factory=list)
    nome_servico_id: str | None = None
    duracao_base_minutos: int = Field(..., gt=0)
    preco_base: Decimal = Field(..., ge=0)
    profissional_id: str | None = None
    organizacao_id: str | None = None
    tipo_procedimento_id: str | None = None
    modalidades: list[ModalidadeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_ofertante(self) -> "ServicoInput":
        if self.profissional_id is None and self.organizacao_id is None:
            raise ValueError(
                "servico precisa pertencer a um profissional ou organizacao"
            )
        return self


class ServicoOutput(BaseModel):
    id: str
    nome: str
    categoria: str
    categorias: list[str] = Field(default_factory=list)
    nome_servico_id: str | None = None
    duracao_base_minutos: int
    preco_base: Decimal
    profissional_id: str | None = None
    organizacao_id: str | None = None
    tipo_procedimento_id: str | None = None
    modalidades: list[ModalidadeOutput] = Field(default_factory=list)


class OfertaDescobertaOutput(BaseModel):
    servico: ServicoOutput
    organizacao: OrganizacaoOutput | None = None
    distancia_km: Decimal | None = None


class PapelInput(BaseModel):
    chave: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    permissoes: list[str] = Field(default_factory=list)


class PapelOutput(BaseModel):
    id: str
    chave: str
    nome: str
    permissoes: list[str] = Field(default_factory=list)


class NomeServicoInput(BaseModel):
    nome: str = Field(..., min_length=1)


class NomeServicoOutput(BaseModel):
    id: str
    nome: str


class MembershipInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "usuario_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
                "papeis": ["funcionario"],
            }
        }
    )
    usuario_id: str
    organizacao_id: str | None = None
    papeis: list[str] = Field(default_factory=list, min_length=1)


class AtualizarMembershipInput(BaseModel):
    papeis: list[str] = Field(default_factory=list, min_length=1)
    ativo: bool = True


class MembershipOutput(BaseModel):
    id: str
    usuario_id: str
    organizacao_id: str | None = None
    ativo: bool
    papeis: list[PapelOutput] = Field(default_factory=list)


class ProfissionalIndependenteOutput(BaseModel):
    organizacao: OrganizacaoOutput
    membership: MembershipOutput


class PacoteInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Pacote relaxamento mensal",
                "servico_ids": ["0190a7b0-7f4d-7000-8000-000000000003"],
                "duracao_total_minutos": 240,
                "preco": "540.00",
                "profissional_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
            }
        }
    )
    nome: str = Field(..., min_length=1)
    servico_ids: list[str] = Field(default_factory=list)
    duracao_total_minutos: int = Field(..., gt=0)
    preco: Decimal = Field(..., ge=0)
    profissional_id: str | None = None
    organizacao_id: str | None = None


class PacoteOutput(BaseModel):
    id: str
    nome: str
    servico_ids: list[str] = Field(default_factory=list)
    duracao_total_minutos: int
    preco: Decimal
    profissional_id: str | None = None
    organizacao_id: str | None = None


class IntervaloInput(BaseModel):
    inicio: time
    fim: time


class JanelaSemanalInput(BaseModel):
    dia_semana: int = Field(..., ge=0, le=6)
    intervalo: IntervaloInput


class ExcecaoAgendaInput(BaseModel):
    data: date
    intervalos: list[IntervaloInput] = Field(default_factory=list)


class DisponibilidadeInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "semanal": [
                    {
                        "dia_semana": 1,
                        "intervalo": {"inicio": "09:00:00", "fim": "18:00:00"},
                    }
                ],
                "excecoes": [],
                "profissional_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
            }
        }
    )
    semanal: list[JanelaSemanalInput] = Field(default_factory=list)
    excecoes: list[ExcecaoAgendaInput] = Field(default_factory=list)
    profissional_id: str | None = None
    organizacao_id: str | None = None

    @model_validator(mode="after")
    def validar_ofertante(self) -> "DisponibilidadeInput":
        if self.profissional_id is None and self.organizacao_id is None:
            raise ValueError(
                "disponibilidade precisa pertencer a um profissional ou organizacao"
            )
        return self


class DisponibilidadeOutput(BaseModel):
    id: str
    semanal: list[dict[str, object]] = Field(default_factory=list)
    excecoes: list[dict[str, object]] = Field(default_factory=list)
    profissional_id: str | None = None
    organizacao_id: str | None = None


class HorarioLivreOutput(BaseModel):
    inicio: datetime
    fim: datetime


class ItemAgendamentoInput(BaseModel):
    servico_id: str | None = None
    pacote_id: str | None = None
    duracao_minutos: int = Field(..., gt=0)
    preco: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def validar_referencia(self) -> "ItemAgendamentoInput":
        if (self.servico_id is None) == (self.pacote_id is None):
            raise ValueError(
                "item deve referenciar exatamente um servico ou pacote"
            )
        return self


class AgendamentoInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cliente_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "profissional_id": "0190a7b0-7f4d-7000-8000-000000000002",
                "inicio": "2026-09-20T14:00:00-03:00",
                "itens": [
                    {
                        "servico_id": "0190a7b0-7f4d-7000-8000-000000000003",
                        "duracao_minutos": 60,
                        "preco": "150.00",
                    }
                ],
                "status_atual": "reservado",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
            }
        }
    )
    cliente_id: str
    profissional_id: str
    inicio: datetime
    itens: list[ItemAgendamentoInput] = Field(default_factory=list)
    status_atual: str = Field(..., min_length=1)
    organizacao_id: str | None = None

    @model_validator(mode="after")
    def validar_itens(self) -> "AgendamentoInput":
        if not self.itens:
            raise ValueError("agendamento precisa ter ao menos um item")
        return self


class AgendamentoOutput(BaseModel):
    id: str
    cliente_id: str
    profissional_id: str
    inicio: datetime
    itens: list[dict[str, object]] = Field(default_factory=list)
    status_atual: str
    organizacao_id: str | None = None


class TransicionarAgendamentoInput(BaseModel):
    novo_status: str = Field(..., min_length=1)
    ator: str = Field(..., min_length=1)


class RecompensaFidelidadeInput(BaseModel):
    tipo: str = Field(..., min_length=1)
    valor: Decimal | None = None
    alvo_id: str | None = None


class ProgramaFidelidadeInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "A cada 10 atendimentos",
                "alvo_servico_id": "0190a7b0-7f4d-7000-8000-000000000003",
                "atendimentos_necessarios": 10,
                "recompensa": {"tipo": "desconto_percentual", "valor": "20.00"},
                "segmento_cliente": "recorrente",
                "profissional_id": "0190a7b0-7f4d-7000-8000-000000000002",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
            }
        }
    )
    nome: str = Field(..., min_length=1)
    alvo_servico_id: str | None = None
    alvo_pacote_id: str | None = None
    atendimentos_necessarios: int = Field(..., gt=0)
    recompensa: RecompensaFidelidadeInput
    segmento_cliente: str | None = None
    profissional_id: str | None = None
    organizacao_id: str | None = None


class ProgramaFidelidadeOutput(BaseModel):
    id: str
    nome: str
    alvo_servico_id: str | None = None
    alvo_pacote_id: str | None = None
    atendimentos_necessarios: int
    recompensa: dict[str, object]
    segmento_cliente: str | None = None
    profissional_id: str | None = None
    organizacao_id: str | None = None


class ProgressoFidelidadeInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "programa_id": "0190a7b0-7f4d-7000-8000-000000000004",
                "cliente_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "atendimentos_concluidos": 3,
            }
        }
    )
    programa_id: str
    cliente_id: str
    atendimentos_concluidos: int = 0


class ProgressoFidelidadeOutput(BaseModel):
    programa_id: str
    cliente_id: str
    atendimentos_concluidos: int


class ResgateFidelidadeInput(BaseModel):
    programa_id: str
    cliente_id: str
    preco: Decimal = Field(..., ge=0)
    agendamento_id: str | None = None


class ResgateFidelidadeOutput(BaseModel):
    resgate_id: str
    programa_id: str
    cliente_id: str
    preco_original: Decimal
    desconto: Decimal
    preco_final: Decimal
    gratuito: bool
    atendimentos_restantes: int


class ResgateFidelidadeRegistroOutput(BaseModel):
    resgate_id: str
    programa_id: str
    cliente_id: str
    agendamento_id: str | None = None
    preco_original: Decimal
    desconto: Decimal
    preco_final: Decimal
    gratuito: bool


class DestinatarioNotificacaoInput(BaseModel):
    id: str = Field(..., min_length=1)
    canal: str = Field(..., min_length=1)
    destino: str = Field(..., min_length=1)


class LembreteInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agendamento": {
                    "cliente_id": "0190a7b0-7f4d-7000-8000-000000000001",
                    "profissional_id": "0190a7b0-7f4d-7000-8000-000000000002",
                    "inicio": "2026-09-20T14:00:00-03:00",
                    "itens": [],
                    "status_atual": "reservado",
                },
                "configuracao": {"antecedencia_horas": 2, "canal": "email"},
                "destinatario": {
                    "id": "cliente-123",
                    "canal": "email",
                    "destino": "maria@example.com",
                },
                "mensagem": "Lembrete: seu atendimento acontece amanha.",
            }
        }
    )
    agendamento: AgendamentoInput
    configuracao: dict[str, object]
    destinatario: DestinatarioNotificacaoInput
    mensagem: str = Field(..., min_length=1)


class LembretePersistidoInput(BaseModel):
    configuracao: dict[str, object]
    destinatario: DestinatarioNotificacaoInput
    mensagem: str = Field(..., min_length=1)


class LembreteOutput(BaseModel):
    agendamento_id: str
    destinatario: DestinatarioNotificacaoInput
    mensagem: str
    enviar_em: datetime


class NotificacaoOutput(BaseModel):
    agendamento_id: str
    destinatario: DestinatarioNotificacaoInput
    mensagem: str
    enviar_em: datetime
    status: str
    tentativas: int
    erro: str | None = None
    enviado_em: datetime | None = None


class RegraComissaoInput(BaseModel):
    id: str
    tipo: str
    valor: Decimal
    membership_id: str | None = None
    servico_id: str | None = None


class RegraComissaoOutput(BaseModel):
    id: str
    tipo: str
    valor: Decimal
    membership_id: str | None = None
    servico_id: str | None = None


class StatusAgendamentoInput(BaseModel):
    chave: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)


class TransicaoStatusInput(BaseModel):
    de: str = Field(..., min_length=1)
    para: str = Field(..., min_length=1)
    atores: list[str] = Field(default_factory=list)


class CatalogoStatusInput(BaseModel):
    status: list[StatusAgendamentoInput] = Field(default_factory=list)
    transicoes: list[TransicaoStatusInput] = Field(default_factory=list)


class CatalogoStatusOutput(BaseModel):
    status: list[StatusAgendamentoInput]
    transicoes: list[TransicaoStatusInput]


class TipoProcedimentoInput(BaseModel):
    chave: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)


class TipoProcedimentoOutput(BaseModel):
    id: str
    chave: str
    nome: str


class MediaOutput(BaseModel):
    id: str
    sha256: str
    mime_type: str
    tamanho_bytes: int
    nome_original: str | None = None
    url: str
    reaproveitada: bool = False


class AnexoMediaInput(BaseModel):
    media_id: str
    entidade_tipo: str = Field(..., min_length=1)
    entidade_id: str
    papel: str = Field(..., min_length=1)
    ordem: int = 0


class AnexoMediaOutput(BaseModel):
    id: str
    entidade_tipo: str
    entidade_id: str
    papel: str
    ordem: int
    media: MediaOutput


class ComissaoInput(BaseModel):
    agendamento: AgendamentoInput
    membership_id: str
    regras: list[RegraComissaoInput] = Field(default_factory=list)
    status_concluido: str = Field(..., min_length=1)


class ComissaoRelatorioInput(BaseModel):
    membership_id: str
    regras: list[RegraComissaoInput] = Field(default_factory=list)
    status_concluido: str = Field(default="concluido", min_length=1)


class LinhaComissaoOutput(BaseModel):
    agendamento_id: str
    profissional_id: str
    valor: Decimal


class ComissaoRelatorioOutput(BaseModel):
    membership_id: str
    linhas: list[LinhaComissaoOutput]
    total: Decimal


class FichaConfiabilidadeOutput(BaseModel):
    cliente_id: str
    total_agendamentos: int
    cancelamentos: int
    nao_comparecimentos: int
    concluidos: int


class EstatisticasOperacaoOutput(BaseModel):
    total_agendamentos: int
    concluidos: int
    cancelados: int
    nao_comparecimentos: int
    ocupacao_minutos: int
    receita_registrada: Decimal


@app.get(
    "/health",
    tags=["Health"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Verifica saúde da API",
    description="[Público, com rate limit] Endpoint de monitoramento usado para confirmar que a aplicação está em execução.",
)
async def health() -> dict[str, str]:
    logger.info("health_check_completed")
    return {"status": "ok", "service": "agenda"}


def identidade_autenticada(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> IdentidadeExterna:
    if credentials is None:
        logger.warning("authentication_header_missing")
        raise HTTPException(
            status_code=401,
            detail="Bearer token obrigatorio",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    try:
        identidade = app.state.identity_adapter.obter_identidade(token)
        SincronizarUsuarioIdentidade(
            UsuarioRepository(app.state.engine)
        ).executar(identidade)
        logger.info(
            "identity_synchronized",
            provider=identidade.provider,
            subject=identidade.subject,
        )
        return identidade
    except IdentidadeNaoAutenticadaError as exc:
        logger.warning("authentication_rejected", reason=str(exc))
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ProvedorIdentidadeIndisponivelError as exc:
        logger.error("authentication_provider_unavailable", reason=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        logger.error("identity_synchronization_failed", reason=str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def exigir_permissao(permissao: str):
    def verificar(
        identidade: IdentidadeExterna = Depends(identidade_autenticada),
    ) -> IdentidadeExterna:
        usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
            identidade.provider,
            identidade.subject,
        )
        if usuario is None:
            raise HTTPException(
                status_code=403,
                detail="identidade externa sem usuario interno",
            )

        memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(
            usuario.id
        )
        if not any(membership.tem_permissao(permissao) for membership in memberships):
            raise HTTPException(
                status_code=403,
                detail=f"permissao obrigatoria: {permissao}",
            )
        return identidade

    return verificar


def exigir_acesso_organizacao(
    identidade: IdentidadeExterna | None,
    organizacao_id: uuid.UUID,
    permissao: str,
) -> None:
    if identidade is None:
        return
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(
            status_code=403,
            detail="identidade externa sem usuario interno",
        )
    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(
        usuario.id
    )
    if not any(
        membership.organizacao_id == organizacao_id
        and membership.tem_permissao(permissao)
        for membership in memberships
    ):
        raise HTTPException(
            status_code=403,
            detail=f"permissao obrigatoria na organizacao: {permissao}",
        )


def exigir_acesso_oferta(
    identidade: IdentidadeExterna | None,
    *,
    organizacao_id: uuid.UUID | None,
    profissional_id: uuid.UUID | None,
    permissao: str,
) -> None:
    if identidade is None:
        return
    if organizacao_id is not None:
        exigir_acesso_organizacao(identidade, organizacao_id, permissao)
        if profissional_id is not None:
            memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(
                profissional_id
            )
            if not any(
                membership.organizacao_id == organizacao_id and membership.ativo
                for membership in memberships
            ):
                raise HTTPException(
                    status_code=422,
                    detail="profissional nao possui membership ativo na organizacao",
                )
        return
    if profissional_id is None:
        raise HTTPException(status_code=422, detail="ofertante obrigatorio")
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None or usuario.id != profissional_id:
        raise HTTPException(
            status_code=403,
            detail="profissional independente so pode ser gerenciado pelo proprio usuario",
        )


exigir_gerenciar_servico = exigir_permissao("servico.gerenciar")
exigir_configurar_estabelecimento = exigir_permissao(
    "estabelecimento.configurar_dados"
)
exigir_gerenciar_equipe = exigir_permissao("estabelecimento.gerenciar_equipe")
exigir_gerenciar_pacote = exigir_permissao("pacote.gerenciar")
exigir_configurar_agenda = exigir_permissao("agenda.configurar")
exigir_solicitar_agendamento = exigir_permissao("agendamento.solicitar")
exigir_configurar_fidelidade = exigir_permissao("fidelidade.configurar_programa")
exigir_configurar_comissao = exigir_permissao("comissao.configurar_regra")
exigir_gerenciar_catalogos = exigir_permissao("plataforma.gerenciar_catalogos")


@app.get(
    "/auth/me",
    response_model=IdentidadeOutput,
    tags=["Health"],
    summary="Consulta a identidade autenticada",
    description="Valida o Bearer token no Keycloak e retorna a identidade externa reconhecida.",
)
def consultar_identidade_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> IdentidadeOutput:
    return IdentidadeOutput(
        provider=identidade.provider,
        subject=identidade.subject,
        nome=identidade.nome,
    )


@app.get(
    "/auth/me/acessos",
    response_model=list[AcessoOrganizacaoOutput],
    tags=["Health"],
    summary="Lista acessos da identidade autenticada",
    description=(
        "Resolve o usuário interno pelo par provider/subject e retorna os memberships "
        "ativos e as permissões concedidas pelos papéis associados."
    ),
)
def listar_acessos_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[AcessoOrganizacaoOutput]:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(
            status_code=403,
            detail="identidade externa sem usuario interno",
        )

    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(
        usuario.id
    )
    return [
        AcessoOrganizacaoOutput(
            membership_id=str(membership.id),
            organizacao_id=(
                str(membership.organizacao_id)
                if membership.organizacao_id
                else None
            ),
            ativo=membership.ativo,
            papeis=sorted(membership.chaves_papeis()),
            permissoes=sorted(
                {
                    permissao
                    for papel in membership.papeis
                    for permissao in papel.permissoes
                }
            ),
        )
        for membership in memberships
    ]


def usuario_para_output(usuario: Usuario) -> UsuarioOutput:
    return UsuarioOutput(
        id=str(usuario.id),
        provider=usuario.provider,
        subject=usuario.subject,
        nome=usuario.nome,
        cpf=usuario.cpf,
        email=usuario.email,
        telefone=usuario.telefone,
    )


def organizacao_para_output(organizacao: Organizacao) -> OrganizacaoOutput:
    return OrganizacaoOutput(
        id=str(organizacao.id),
        nome=organizacao.nome,
        unipessoal=organizacao.unipessoal,
        endereco=(
            EnderecoOutput(
                logradouro=organizacao.endereco.logradouro,
                numero=organizacao.endereco.numero,
                cidade=organizacao.endereco.cidade,
                estado=organizacao.endereco.estado,
                cep=organizacao.endereco.cep,
            )
            if organizacao.endereco is not None
            else None
        ),
    )


def cliente_para_output(cliente: Cliente) -> ClienteOutput:
    return ClienteOutput(
        id=str(cliente.id),
        nome=cliente.nome,
        telefone=cliente.telefone,
        email=cliente.email,
        cpf=cliente.cpf,
        segmento=cliente.segmento,
        endereco=(
            EnderecoOutput(
                logradouro=cliente.endereco.logradouro,
                numero=cliente.endereco.numero,
                cidade=cliente.endereco.cidade,
                estado=cliente.endereco.estado,
                cep=cliente.endereco.cep,
            )
            if cliente.endereco is not None
            else None
        ),
    )


def servico_para_output(servico: Servico) -> ServicoOutput:
    return ServicoOutput(
        id=str(servico.id),
        nome=servico.nome,
        categoria=servico.categoria,
        categorias=list(servico.categorias),
        nome_servico_id=(
            str(servico.nome_servico_id) if servico.nome_servico_id else None
        ),
        duracao_base_minutos=servico.duracao_base_minutos,
        preco_base=servico.preco_base,
        profissional_id=str(servico.profissional_id) if servico.profissional_id else None,
        organizacao_id=str(servico.organizacao_id) if servico.organizacao_id else None,
        tipo_procedimento_id=(
            str(servico.tipo_procedimento_id) if servico.tipo_procedimento_id else None
        ),
        modalidades=[
            ModalidadeOutput(
                chave=item.chave,
                nome=item.nome,
                ajuste_preco_fixo=item.ajuste_preco_fixo,
                ajuste_preco_percentual=item.ajuste_preco_percentual,
                ajuste_duracao_minutos=item.ajuste_duracao_minutos,
            )
            for item in servico.modalidades
        ],
    )


def membership_para_output(membership: Membership) -> MembershipOutput:
    return MembershipOutput(
        id=str(membership.id),
        usuario_id=str(membership.usuario_id),
        organizacao_id=str(membership.organizacao_id) if membership.organizacao_id else None,
        ativo=membership.ativo,
        papeis=[
            PapelOutput(
                id=str(papel.id),
                chave=papel.chave,
                nome=papel.nome,
                permissoes=list(papel.permissoes),
            )
            for papel in membership.papeis
        ],
    )


def pacote_para_output(pacote: Pacote) -> PacoteOutput:
    return PacoteOutput(
        id=str(pacote.id),
        nome=pacote.nome,
        servico_ids=[str(item) for item in pacote.servico_ids],
        duracao_total_minutos=pacote.duracao_total_minutos,
        preco=pacote.preco,
        profissional_id=str(pacote.profissional_id) if pacote.profissional_id else None,
        organizacao_id=str(pacote.organizacao_id) if pacote.organizacao_id else None,
    )


def disponibilidade_para_output(disponibilidade: Disponibilidade) -> DisponibilidadeOutput:
    return DisponibilidadeOutput(
        id=str(disponibilidade.id),
        semanal=[
            {"dia_semana": item.dia_semana, "intervalo": {"inicio": item.intervalo.inicio.isoformat(), "fim": item.intervalo.fim.isoformat()}}
            for item in disponibilidade.semanal
        ],
        excecoes=[
            {"data": item.data.isoformat(), "intervalos": [{"inicio": i.inicio.isoformat(), "fim": i.fim.isoformat()} for i in item.intervalos]}
            for item in disponibilidade.excecoes
        ],
        profissional_id=str(disponibilidade.profissional_id) if disponibilidade.profissional_id else None,
        organizacao_id=str(disponibilidade.organizacao_id) if disponibilidade.organizacao_id else None,
    )


def agendamento_para_output(agendamento: Agendamento) -> AgendamentoOutput:
    return AgendamentoOutput(
        id=str(agendamento.id),
        cliente_id=str(agendamento.cliente_id),
        profissional_id=str(agendamento.profissional_id),
        inicio=agendamento.inicio,
        itens=[
            {
                "servico_id": str(item.servico_id) if item.servico_id else None,
                "pacote_id": str(item.pacote_id) if item.pacote_id else None,
                "duracao_minutos": item.duracao_minutos,
                "preco": str(item.preco),
            }
            for item in agendamento.itens
        ],
        status_atual=agendamento.status_atual,
        organizacao_id=str(agendamento.organizacao_id) if agendamento.organizacao_id else None,
    )


def programa_fidelidade_para_output(programa: ProgramaFidelidade) -> ProgramaFidelidadeOutput:
    return ProgramaFidelidadeOutput(
        id=str(programa.id),
        nome=programa.nome,
        alvo_servico_id=str(programa.alvo_servico_id) if programa.alvo_servico_id else None,
        alvo_pacote_id=str(programa.alvo_pacote_id) if programa.alvo_pacote_id else None,
        atendimentos_necessarios=programa.atendimentos_necessarios,
        recompensa={
            "tipo": programa.recompensa.tipo,
            "valor": str(programa.recompensa.valor) if programa.recompensa.valor is not None else None,
            "alvo_id": str(programa.recompensa.alvo_id) if programa.recompensa.alvo_id else None,
        },
        segmento_cliente=programa.segmento_cliente,
        profissional_id=str(programa.profissional_id) if programa.profissional_id else None,
        organizacao_id=str(programa.organizacao_id) if programa.organizacao_id else None,
    )


def progresso_fidelidade_para_output(progresso: ProgressoFidelidade) -> ProgressoFidelidadeOutput:
    return ProgressoFidelidadeOutput(
        programa_id=str(progresso.programa_id),
        cliente_id=str(progresso.cliente_id),
        atendimentos_concluidos=progresso.atendimentos_concluidos,
    )


@app.get(
    "/usuarios",
    response_model=list[UsuarioOutput],
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista usuários",
    description="Retorna todos os usuários cadastrados no sistema.",
)
def listar_usuarios_endpoint() -> list[UsuarioOutput]:
    repo = UsuarioRepository(app.state.engine)
    return [usuario_para_output(item) for item in repo.listar()]


@app.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca usuário por ID",
    description="Consulta um usuário específico pelo identificador único.",
)
def buscar_usuario_endpoint(usuario_id: str) -> UsuarioOutput:
    repo = UsuarioRepository(app.state.engine)
    usuario = repo.buscar_por_id(uuid.UUID(usuario_id))
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    return usuario_para_output(usuario)


@app.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Atualiza usuário",
    description="Atualiza os dados básicos de um usuário já cadastrado.",
)
def atualizar_usuario_endpoint(usuario_id: str, payload: UsuarioInput) -> UsuarioOutput:
    repo = UsuarioRepository(app.state.engine)
    usuario = repo.buscar_por_id(uuid.UUID(usuario_id))
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")

    atualizado = Usuario(
        id=usuario.id,
        provider=payload.provider,
        subject=payload.subject,
        nome=payload.nome,
        cpf=payload.cpf,
        email=payload.email,
        telefone=payload.telefone,
    )
    salvo = repo.atualizar(atualizado)
    return usuario_para_output(salvo)


@app.delete(
    "/usuarios/{usuario_id}",
    status_code=200,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Remove usuário",
    description="Exclui um usuário do cadastro quando ele não for mais necessário.",
)
def remover_usuario_endpoint(usuario_id: str) -> dict[str, str]:
    repo = UsuarioRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(usuario_id)) is None:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    repo.remover(uuid.UUID(usuario_id))
    return {"status": "deleted"}


@app.get(
    "/organizacoes",
    response_model=list[OrganizacaoOutput],
    tags=["Organizações"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista organizações",
    description="[Público, com rate limit] Retorna todas as organizações do sistema.",
)
def listar_organizacoes_endpoint() -> list[OrganizacaoOutput]:
    repo = OrganizacaoRepository(app.state.engine)
    return [organizacao_para_output(item) for item in repo.listar()]


@app.get(
    "/organizacoes/{organizacao_id}",
    response_model=OrganizacaoOutput,
    tags=["Organizações"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Busca organização por ID",
    description="[Público, com rate limit] Recupera uma organização específica com endereço quando disponível.",
)
def buscar_organizacao_endpoint(organizacao_id: str) -> OrganizacaoOutput:
    repo = OrganizacaoRepository(app.state.engine)
    organizacao = repo.buscar_por_id(uuid.UUID(organizacao_id))
    if organizacao is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return organizacao_para_output(organizacao)


@app.put(
    "/organizacoes/{organizacao_id}",
    response_model=OrganizacaoOutput,
    tags=["Organizações"],
    dependencies=[Depends(exigir_configurar_estabelecimento)],
    summary="Atualiza organização",
    description="Atualiza os dados cadastrais e o endereço de uma organização.",
)
def atualizar_organizacao_endpoint(
    organizacao_id: str,
    payload: OrganizacaoInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_estabelecimento),
) -> OrganizacaoOutput:
    repo = OrganizacaoRepository(app.state.engine)
    organizacao_uuid = uuid.UUID(organizacao_id)
    exigir_acesso_organizacao(
        identidade,
        organizacao_uuid,
        "estabelecimento.configurar_dados",
    )
    organizacao = repo.buscar_por_id(organizacao_uuid)
    if organizacao is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")

    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            logradouro=payload.endereco.logradouro,
            numero=payload.endereco.numero,
            cidade=payload.endereco.cidade,
            estado=payload.endereco.estado,
            cep=payload.endereco.cep,
        )

    atualizado = Organizacao(
        id=organizacao.id,
        nome=payload.nome,
        unipessoal=payload.unipessoal,
        endereco=endereco,
    )
    salvo = repo.atualizar(atualizado)
    return organizacao_para_output(salvo)


@app.delete(
    "/organizacoes/{organizacao_id}",
    status_code=200,
    tags=["Organizações"],
    dependencies=[Depends(exigir_configurar_estabelecimento)],
    summary="Remove organização",
    description="Remove uma organização do cadastro após validação do identificador.",
)
def remover_organizacao_endpoint(
    organizacao_id: str,
    identidade: IdentidadeExterna = Depends(exigir_configurar_estabelecimento),
) -> dict[str, str]:
    repo = OrganizacaoRepository(app.state.engine)
    organizacao_uuid = uuid.UUID(organizacao_id)
    if repo.buscar_por_id(organizacao_uuid) is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    exigir_acesso_organizacao(
        identidade,
        organizacao_uuid,
        "estabelecimento.configurar_dados",
    )
    repo.remover(organizacao_uuid)
    return {"status": "deleted"}


@app.get(
    "/servicos",
    response_model=list[ServicoOutput],
    tags=["Serviços"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista serviços",
    description="[Público, com rate limit] Retorna todos os serviços disponíveis para profissionais e organizações.",
)
def listar_servicos_endpoint() -> list[ServicoOutput]:
    repo = ServicoRepository(app.state.engine)
    return [servico_para_output(item) for item in repo.listar()]


@app.get(
    "/servicos/{servico_id}",
    response_model=ServicoOutput,
    tags=["Serviços"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Busca serviço por ID",
    description="[Público, com rate limit] Detalha um serviço, incluindo modalidades, preço base e duração.",
)
def buscar_servico_endpoint(servico_id: str) -> ServicoOutput:
    repo = ServicoRepository(app.state.engine)
    servico = repo.buscar_por_id(uuid.UUID(servico_id))
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico_para_output(servico)


@app.get(
    "/descoberta",
    response_model=list[OfertaDescobertaOutput],
    tags=["Serviços"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Descobre ofertas",
    description="Busca serviços por categoria e, opcionalmente, por proximidade de um endereço.",
)
def descobrir_ofertas_endpoint(
    termo: str | None = None,
    categoria: str | None = None,
    endereco: str | None = None,
    raio_km: Decimal | None = None,
) -> list[OfertaDescobertaOutput]:
    geocodificacao = None
    distancia = None
    if endereco:
        geocodificacao = NominatimGeocodificacaoAdapter(
            base_url=settings.nominatim_base_url
        )
        distancia = OSRMDistanciaAdapter(base_url=settings.osrm_base_url)
    try:
        ofertas = DescobrirOfertas(
            ServicoRepository(app.state.engine),
            OrganizacaoRepository(app.state.engine),
            geocodificacao,
            distancia,
        ).executar(
            termo=termo,
            categoria=categoria,
            endereco=endereco,
            raio_km=raio_km,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [
        OfertaDescobertaOutput(
            servico=servico_para_output(oferta.servico),
            organizacao=(
                organizacao_para_output(oferta.organizacao)
                if oferta.organizacao is not None
                else None
            ),
            distancia_km=oferta.distancia_km,
        )
        for oferta in ofertas
    ]


@app.put(
    "/servicos/{servico_id}",
    response_model=ServicoOutput,
    tags=["Serviços"],
    summary="Atualiza serviço",
    description="Altera dados base de um serviço, incluindo modalidades e associações.",
)
def atualizar_servico_endpoint(
    servico_id: str,
    payload: ServicoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> ServicoOutput:
    repo = ServicoRepository(app.state.engine)
    servico = repo.buscar_por_id(uuid.UUID(servico_id))
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    exigir_acesso_oferta(
        identidade,
        organizacao_id=servico.organizacao_id,
        profissional_id=servico.profissional_id,
        permissao="servico.gerenciar",
    )
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="servico.gerenciar",
    )

    atualizado = Servico(
        id=servico.id,
        nome=payload.nome,
        categoria=payload.categoria,
        categorias=tuple(payload.categorias),
        nome_servico_id=(
            uuid.UUID(payload.nome_servico_id) if payload.nome_servico_id else None
        ),
        duracao_base_minutos=payload.duracao_base_minutos,
        preco_base=payload.preco_base,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
        tipo_procedimento_id=(
            uuid.UUID(payload.tipo_procedimento_id) if payload.tipo_procedimento_id else None
        ),
        modalidades=tuple(
            ModalidadeAtendimento(
                chave=item.chave,
                nome=item.nome,
                ajuste_preco_fixo=item.ajuste_preco_fixo,
                ajuste_preco_percentual=item.ajuste_preco_percentual,
                ajuste_duracao_minutos=item.ajuste_duracao_minutos,
            )
            for item in payload.modalidades
        ),
    )
    salvo = repo.atualizar(atualizado)
    return servico_para_output(salvo)


@app.delete(
    "/servicos/{servico_id}",
    status_code=200,
    tags=["Serviços"],
    summary="Remove serviço",
    description="Exclui um serviço do catálogo quando não estiver mais em uso.",
)
def remover_servico_endpoint(
    servico_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> dict[str, str]:
    repo = ServicoRepository(app.state.engine)
    servico = repo.buscar_por_id(uuid.UUID(servico_id))
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=servico.organizacao_id,
        profissional_id=servico.profissional_id,
        permissao="servico.gerenciar",
    )
    repo.remover(uuid.UUID(servico_id))
    return {"status": "deleted"}


@app.post(
    "/clientes",
    response_model=ClienteOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Cria ficha de cliente",
    description="Cria o perfil comercial do cliente, separado da identidade autenticada.",
)
def criar_cliente_endpoint(
    payload: ClienteInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ClienteOutput:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            payload.endereco.logradouro,
            payload.endereco.numero,
            payload.endereco.cidade,
            payload.endereco.estado,
            payload.endereco.cep,
        )
    cliente = Cliente(
        id=uuid.uuid7(),
        nome=payload.nome,
        usuario_id=usuario.id,
        segmento=payload.segmento,
        telefone=payload.telefone,
        email=payload.email,
        cpf=payload.cpf,
        endereco=endereco,
    )
    return cliente_para_output(ClienteRepository(app.state.engine).salvar(cliente))


@app.get(
    "/clientes",
    response_model=list[ClienteOutput],
    tags=["Usuários"],
    summary="Lista fichas de cliente",
    description=(
        "Retorna todas as fichas de cliente para quem tem a permissão 'cliente.ver_ficha' "
        "em algum membership ativo; caso contrário, retorna apenas a própria ficha."
    ),
)
def listar_clientes_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[ClienteOutput]:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(usuario.id)
    pode_ver_todos = any(
        membership.tem_permissao("cliente.ver_ficha") for membership in memberships
    )
    clientes = ClienteRepository(app.state.engine).listar()
    if not pode_ver_todos:
        clientes = [cliente for cliente in clientes if cliente.usuario_id == usuario.id]
    return [cliente_para_output(cliente) for cliente in clientes]


@app.get(
    "/clientes/{cliente_id}",
    response_model=ClienteOutput,
    tags=["Usuários"],
    summary="Busca ficha de cliente",
)
def buscar_cliente_endpoint(
    cliente_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ClienteOutput:
    cliente = ClienteRepository(app.state.engine).buscar_por_id(uuid.UUID(cliente_id))
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None or cliente.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="cliente fora do escopo do usuario")
    return cliente_para_output(cliente)


@app.put(
    "/clientes/{cliente_id}",
    response_model=ClienteOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Atualiza ficha de cliente",
)
def atualizar_cliente_endpoint(
    cliente_id: str,
    payload: ClienteInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ClienteOutput:
    repo = ClienteRepository(app.state.engine)
    existente = repo.buscar_por_id(uuid.UUID(cliente_id))
    if existente is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None or existente.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="cliente fora do escopo do usuario")
    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            payload.endereco.logradouro,
            payload.endereco.numero,
            payload.endereco.cidade,
            payload.endereco.estado,
            payload.endereco.cep,
        )
    atualizado = Cliente(
        id=existente.id,
        nome=payload.nome,
        usuario_id=existente.usuario_id,
        segmento=payload.segmento,
        telefone=payload.telefone,
        email=payload.email,
        cpf=payload.cpf,
        endereco=endereco,
    )
    return cliente_para_output(repo.atualizar(atualizado))


@app.delete(
    "/clientes/{cliente_id}",
    response_model=ClienteOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Anonimiza ficha de cliente",
    description="Remove dados pessoais da ficha sem apagar referências históricas de agendamento.",
)
def anonimizar_cliente_endpoint(
    cliente_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ClienteOutput:
    repo = ClienteRepository(app.state.engine)
    existente = repo.buscar_por_id(uuid.UUID(cliente_id))
    if existente is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None or existente.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="cliente fora do escopo do usuario")
    cliente = repo.anonimizar(existente.id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente_para_output(cliente)


@app.get(
    "/memberships",
    response_model=list[MembershipOutput],
    tags=["Memberships"],
    summary="Lista memberships",
    description=(
        "Recupera os vínculos entre usuários, organizações e papéis. Para quem tem a "
        "permissão 'plataforma.visualizar_metricas_globais' (admin da plataforma), "
        "retorna todos os memberships do sistema; caso contrário, apenas os próprios."
    ),
)
def listar_memberships_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[MembershipOutput]:
    repo = MembershipRepository(app.state.engine)
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    proprios = repo.listar_por_usuario_id(usuario.id)
    pode_ver_todos = any(
        membership.tem_permissao("plataforma.visualizar_metricas_globais")
        for membership in proprios
    )
    itens = repo.listar() if pode_ver_todos else proprios
    return [membership_para_output(item) for item in itens]


@app.get(
    "/memberships/{membership_id}",
    response_model=MembershipOutput,
    tags=["Memberships"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca membership por ID",
    description="Consulta o vínculo específico de usuário e organização em um perfil funcional.",
)
def buscar_membership_endpoint(
    membership_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> MembershipOutput:
    repo = MembershipRepository(app.state.engine)
    membership = repo.buscar_por_id(uuid.UUID(membership_id))
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership não encontrado")
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None or membership.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Membership não encontrado")
    return membership_para_output(membership)


@app.put(
    "/memberships/{membership_id}",
    response_model=MembershipOutput,
    tags=["Memberships"],
    summary="Atualiza membership",
    description="Atualiza os papéis catalogados e o estado ativo do vínculo.",
)
def atualizar_membership_endpoint(
    membership_id: str,
    payload: AtualizarMembershipInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_equipe),
) -> MembershipOutput:
    repo = MembershipRepository(app.state.engine)
    membership = repo.buscar_por_id(uuid.UUID(membership_id))
    if membership is None or membership.organizacao_id is None:
        raise HTTPException(status_code=404, detail="Membership nao encontrado")
    exigir_acesso_organizacao(
        identidade,
        membership.organizacao_id,
        "estabelecimento.gerenciar_equipe",
    )
    papeis_repo = PapelRepository(app.state.engine)
    papeis = []
    for chave in payload.papeis:
        papel = papeis_repo.buscar_por_chave(chave)
        if papel is None:
            raise HTTPException(status_code=422, detail=f"papel nao encontrado no catalogo: {chave}")
        papeis.append(papel)
    membership.papeis = papeis
    membership.ativo = payload.ativo
    atualizado = repo.atualizar(membership)
    return membership_para_output(atualizado)


@app.delete(
    "/memberships/{membership_id}",
    status_code=200,
    tags=["Memberships"],
    summary="Remove membership",
    description="Remove um vínculo de equipe dentro da organização autorizada.",
)
def remover_membership_endpoint(
    membership_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_equipe),
) -> dict[str, str]:
    repo = MembershipRepository(app.state.engine)
    membership = repo.buscar_por_id(uuid.UUID(membership_id))
    if membership is None or membership.organizacao_id is None:
        raise HTTPException(status_code=404, detail="Membership nao encontrado")
    exigir_acesso_organizacao(
        identidade,
        membership.organizacao_id,
        "estabelecimento.gerenciar_equipe",
    )
    repo.remover(membership.id)
    return {"status": "deleted"}


@app.get(
    "/pacotes",
    response_model=list[PacoteOutput],
    tags=["Pacotes"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista pacotes",
    description="Retorna os pacotes de serviço cadastrados na plataforma.",
)
def listar_pacotes_endpoint() -> list[PacoteOutput]:
    repo = PacoteRepository(app.state.engine)
    return [pacote_para_output(item) for item in repo.listar()]


@app.get(
    "/pacotes/{pacote_id}",
    response_model=PacoteOutput,
    tags=["Pacotes"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca pacote por ID",
    description="Consulta um pacote de serviços pelo identificador único.",
)
def buscar_pacote_endpoint(pacote_id: str) -> PacoteOutput:
    repo = PacoteRepository(app.state.engine)
    pacote = repo.buscar_por_id(uuid.UUID(pacote_id))
    if pacote is None:
        raise HTTPException(status_code=404, detail="Pacote não encontrado")
    return pacote_para_output(pacote)


@app.get(
    "/disponibilidades",
    response_model=list[DisponibilidadeOutput],
    tags=["Disponibilidade"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista disponibilidades",
    description="[Público, com rate limit] Retorna as disponibilidades cadastradas por profissional ou organização.",
)
def listar_disponibilidades_endpoint() -> list[DisponibilidadeOutput]:
    repo = DisponibilidadeRepository(app.state.engine)
    return [disponibilidade_para_output(item) for item in repo.listar()]


@app.get(
    "/disponibilidades/{disponibilidade_id}",
    response_model=DisponibilidadeOutput,
    tags=["Disponibilidade"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Busca disponibilidade por ID",
    description="[Público, com rate limit] Detalha a disponibilidade específica de agenda e suas exceções.",
)
def buscar_disponibilidade_endpoint(disponibilidade_id: str) -> DisponibilidadeOutput:
    repo = DisponibilidadeRepository(app.state.engine)
    disponibilidade = repo.buscar_por_id(uuid.UUID(disponibilidade_id))
    if disponibilidade is None:
        raise HTTPException(status_code=404, detail="Disponibilidade não encontrada")
    return disponibilidade_para_output(disponibilidade)


@app.get(
    "/agendamentos",
    response_model=list[AgendamentoOutput],
    tags=["Agendamentos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista agendamentos",
    description="Consulta todos os agendamentos registrados no sistema.",
)
def listar_agendamentos_endpoint() -> list[AgendamentoOutput]:
    repo = AgendamentoRepository(app.state.engine)
    return [agendamento_para_output(item) for item in repo.listar()]


@app.get(
    "/agendamentos/{agendamento_id}",
    response_model=AgendamentoOutput,
    tags=["Agendamentos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca agendamento por ID",
    description="Recupera um agendamento específico com itens, cliente e status atual.",
)
def buscar_agendamento_endpoint(agendamento_id: str) -> AgendamentoOutput:
    repo = AgendamentoRepository(app.state.engine)
    agendamento = repo.buscar_por_id(uuid.UUID(agendamento_id))
    if agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return agendamento_para_output(agendamento)


@app.get(
    "/programas-fidelidade",
    response_model=list[ProgramaFidelidadeOutput],
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista programas de fidelidade",
    description="Retorna os programas de fidelidade disponíveis para clientes, serviços ou pacotes.",
)
def listar_programas_fidelidade_endpoint() -> list[ProgramaFidelidadeOutput]:
    repo = ProgramaFidelidadeRepository(app.state.engine)
    return [programa_fidelidade_para_output(item) for item in repo.listar()]


@app.get(
    "/programas-fidelidade/{programa_id}",
    response_model=ProgramaFidelidadeOutput,
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca programa de fidelidade por ID",
    description="Consulta detalhes do programa de fidelidade e da recompensa definida.",
)
def buscar_programa_fidelidade_endpoint(programa_id: str) -> ProgramaFidelidadeOutput:
    repo = ProgramaFidelidadeRepository(app.state.engine)
    programa = repo.buscar_por_id(uuid.UUID(programa_id))
    if programa is None:
        raise HTTPException(status_code=404, detail="Programa de fidelidade não encontrado")
    return programa_fidelidade_para_output(programa)


@app.get(
    "/progresso-fidelidade",
    response_model=list[ProgressoFidelidadeOutput],
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista progresso de fidelidade",
    description="Expõe o avanço acumulado dos clientes em programas de fidelidade.",
)
def listar_progresso_fidelidade_endpoint() -> list[ProgressoFidelidadeOutput]:
    repo = ProgressoFidelidadeRepository(app.state.engine)
    return [progresso_fidelidade_para_output(item) for item in repo.listar()]


@app.get(
    "/progresso-fidelidade/{programa_id}/{cliente_id}",
    response_model=ProgressoFidelidadeOutput,
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca progresso por programa e cliente",
    description="Consulta o progresso de um cliente específico em um programa de fidelidade.",
)
def buscar_progresso_fidelidade_endpoint(programa_id: str, cliente_id: str) -> ProgressoFidelidadeOutput:
    repo = ProgressoFidelidadeRepository(app.state.engine)
    progresso = repo.buscar_por_id(uuid.UUID(programa_id), uuid.UUID(cliente_id))
    if progresso is None:
        raise HTTPException(status_code=404, detail="Progresso de fidelidade não encontrado")
    return progresso_fidelidade_para_output(progresso)


@app.get(
    "/clientes/{cliente_id}/programas-fidelidade",
    response_model=list[ProgramaFidelidadeOutput],
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista programas aplicáveis ao cliente",
    description="Programas segmentados do cliente substituem os programas padrão do mesmo alvo.",
)
def listar_programas_cliente_endpoint(cliente_id: str) -> list[ProgramaFidelidadeOutput]:
    cliente = ClienteRepository(app.state.engine).buscar_por_id(uuid.UUID(cliente_id))
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    programas = ProgramaFidelidadeRepository(app.state.engine).listar()
    aplicaveis: list = []
    por_alvo: dict[tuple[uuid.UUID | None, uuid.UUID | None], list] = {}
    for programa in programas:
        if programa.segmento_cliente not in (None, cliente.segmento):
            continue
        por_alvo.setdefault(
            (programa.alvo_servico_id, programa.alvo_pacote_id), []
        ).append(programa)
    for candidatos in por_alvo.values():
        segmentados = [item for item in candidatos if item.segmento_cliente is not None]
        aplicaveis.extend(segmentados or candidatos)
    return [programa_fidelidade_para_output(item) for item in aplicaveis]


@app.post(
    "/usuarios",
    response_model=UsuarioOutput,
    tags=["Usuários"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Cria usuário",
    description="Registra um novo usuário no sistema com identificador de provedor e subject.",
)
def criar_usuario_endpoint(payload: UsuarioInput) -> UsuarioOutput:
    repo = UsuarioRepository(app.state.engine)
    use_case = RegistrarUsuario(repo)
    usuario = Usuario(
        id=uuid.uuid7(),
        provider=payload.provider,
        subject=payload.subject,
        nome=payload.nome,
        cpf=payload.cpf,
        email=payload.email,
        telefone=payload.telefone,
    )
    try:
        salvo = use_case.executar(usuario)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return usuario_para_output(salvo)


@app.post(
    "/organizacoes",
    response_model=OrganizacaoOutput,
    tags=["Organizações"],
    dependencies=[Depends(exigir_configurar_estabelecimento)],
    summary="Cria organização",
    description="Cria uma nova organização com nome, tipo e endereço opcional.",
)
def criar_organizacao_endpoint(payload: OrganizacaoInput) -> OrganizacaoOutput:
    repo = OrganizacaoRepository(app.state.engine)
    use_case = CriarOrganizacao(repo)
    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            logradouro=payload.endereco.logradouro,
            numero=payload.endereco.numero,
            cidade=payload.endereco.cidade,
            estado=payload.endereco.estado,
            cep=payload.endereco.cep,
        )
    organizacao = Organizacao(id=uuid.uuid7(), nome=payload.nome, unipessoal=payload.unipessoal, endereco=endereco)
    salvo = use_case.executar(organizacao)
    return OrganizacaoOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        unipessoal=salvo.unipessoal,
        endereco=(
            EnderecoOutput(
                logradouro=salvo.endereco.logradouro,
                numero=salvo.endereco.numero,
                cidade=salvo.endereco.cidade,
                estado=salvo.endereco.estado,
                cep=salvo.endereco.cep,
            )
            if salvo.endereco is not None
            else None
        ),
    )


@app.post(
    "/profissionais/independente",
    response_model=ProfissionalIndependenteOutput,
    tags=["Organizações"],
    summary="Cria perfil de profissional independente",
    description=(
        "Cria uma organização unipessoal e vincula o usuário autenticado como dono. "
        "O papel dono é obtido do catálogo persistido de papéis."
    ),
)
def criar_profissional_independente_endpoint(
    payload: ProfissionalIndependenteInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ProfissionalIndependenteOutput:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(
            status_code=403,
            detail="identidade externa sem usuario interno",
        )

    papel_dono = PapelRepository(app.state.engine).buscar_por_chave("dono")
    if papel_dono is None:
        raise HTTPException(
            status_code=503,
            detail="catalogo de papeis nao inicializado",
        )

    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            logradouro=payload.endereco.logradouro,
            numero=payload.endereco.numero,
            cidade=payload.endereco.cidade,
            estado=payload.endereco.estado,
            cep=payload.endereco.cep,
        )

    perfil = CriarProfissionalIndependente(
        OrganizacaoRepository(app.state.engine),
        MembershipRepository(app.state.engine),
    ).executar(
        usuario_id=usuario.id,
        nome=payload.nome,
        papel_dono=papel_dono,
        endereco=endereco,
    )
    return ProfissionalIndependenteOutput(
        organizacao=organizacao_para_output(perfil.organizacao),
        membership=membership_para_output(perfil.membership),
    )


@app.post(
    "/organizacoes/com-equipe",
    response_model=ProfissionalIndependenteOutput,
    tags=["Organizações"],
    summary="Cria organização com equipe e vincula o usuário autenticado como dono",
    description=(
        "Cria uma organização não unipessoal e vincula o usuário autenticado como "
        "dono, permitindo montar equipe em seguida via POST /memberships. "
        "Complementa /profissionais/independente, que cobre o caso autônomo puro: "
        "sem este endpoint, uma organização criada via POST /organizacoes ficava "
        "sem ninguém com permissão para gerenciar sua equipe."
    ),
)
def criar_organizacao_com_equipe_endpoint(
    payload: ProfissionalIndependenteInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ProfissionalIndependenteOutput:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(
            status_code=403,
            detail="identidade externa sem usuario interno",
        )

    papel_dono = PapelRepository(app.state.engine).buscar_por_chave("dono")
    if papel_dono is None:
        raise HTTPException(
            status_code=503,
            detail="catalogo de papeis nao inicializado",
        )

    endereco = None
    if payload.endereco is not None:
        endereco = Endereco(
            logradouro=payload.endereco.logradouro,
            numero=payload.endereco.numero,
            cidade=payload.endereco.cidade,
            estado=payload.endereco.estado,
            cep=payload.endereco.cep,
        )

    perfil = CriarOrganizacaoComEquipe(
        OrganizacaoRepository(app.state.engine),
        MembershipRepository(app.state.engine),
    ).executar(
        usuario_id=usuario.id,
        nome=payload.nome,
        papel_dono=papel_dono,
        endereco=endereco,
    )
    return ProfissionalIndependenteOutput(
        organizacao=organizacao_para_output(perfil.organizacao),
        membership=membership_para_output(perfil.membership),
    )


@app.post(
    "/servicos",
    response_model=ServicoOutput,
    tags=["Serviços"],
    summary="Cria serviço",
    description="Cadastra um novo serviço com duração, preço e modalidades de atendimento.",
)
def criar_servico_endpoint(
    payload: ServicoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> ServicoOutput:
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="servico.gerenciar",
    )
    repo = ServicoRepository(app.state.engine)
    use_case = CriarServico(repo)
    servico = Servico(
        id=uuid.uuid7(),
        nome=payload.nome,
        categoria=payload.categoria,
        categorias=tuple(payload.categorias),
        nome_servico_id=(
            uuid.UUID(payload.nome_servico_id) if payload.nome_servico_id else None
        ),
        duracao_base_minutos=payload.duracao_base_minutos,
        preco_base=payload.preco_base,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
        tipo_procedimento_id=(
            uuid.UUID(payload.tipo_procedimento_id) if payload.tipo_procedimento_id else None
        ),
        modalidades=tuple(
            ModalidadeAtendimento(
                chave=item.chave,
                nome=item.nome,
                ajuste_preco_fixo=item.ajuste_preco_fixo,
                ajuste_preco_percentual=item.ajuste_preco_percentual,
                ajuste_duracao_minutos=item.ajuste_duracao_minutos,
            )
            for item in payload.modalidades
        ),
    )
    salvo = use_case.executar(servico)
    return servico_para_output(salvo)


@app.post(
    "/memberships",
    response_model=MembershipOutput,
    tags=["Memberships"],
    summary="Cria membership",
    description="Vincula usuário, organização e papéis para compor o perfil funcional da operação.",
)
def criar_membership_endpoint(
    payload: MembershipInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_equipe),
) -> MembershipOutput:
    if payload.organizacao_id is None:
        raise HTTPException(
            status_code=422,
            detail="organizacao_id e obrigatorio para membership de equipe",
        )
    exigir_acesso_organizacao(
        identidade,
        uuid.UUID(payload.organizacao_id),
        "estabelecimento.gerenciar_equipe",
    )
    repo = MembershipRepository(app.state.engine)
    papeis_repo = PapelRepository(app.state.engine)
    papeis: list[Papel] = []
    for chave in payload.papeis:
        papel = papeis_repo.buscar_por_chave(chave)
        if papel is None:
            raise HTTPException(
                status_code=422,
                detail=f"papel nao encontrado no catalogo: {chave}",
            )
        papeis.append(papel)

    use_case = CriarMembership(repo)
    membership = use_case.executar(
        usuario_id=uuid.UUID(str(payload.usuario_id)),
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
        papeis=papeis,
    )
    return MembershipOutput(
        id=str(membership.id),
        usuario_id=str(membership.usuario_id),
        organizacao_id=str(membership.organizacao_id) if membership.organizacao_id else None,
        ativo=membership.ativo,
        papeis=[
            PapelOutput(
                id=str(papel.id),
                chave=papel.chave,
                nome=papel.nome,
                permissoes=list(papel.permissoes),
            )
            for papel in membership.papeis
        ],
    )


@app.post(
    "/pacotes",
    response_model=PacoteOutput,
    tags=["Pacotes"],
    summary="Cria pacote",
    description="Agrupa serviços em um pacote com preço e duração totais.",
)
def criar_pacote_endpoint(
    payload: PacoteInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_pacote),
) -> PacoteOutput:
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="pacote.gerenciar",
    )
    servico_repo = ServicoRepository(app.state.engine)
    servicos = [
        servico_repo.buscar_por_id(uuid.UUID(str(servico_id)))
        for servico_id in payload.servico_ids
    ]
    if any(servico is None for servico in servicos):
        raise HTTPException(
            status_code=422,
            detail="pacote referencia servico inexistente",
        )
    repo = PacoteRepository(app.state.engine)
    use_case = CriarPacote(repo)
    pacote = Pacote(
        id=uuid.uuid7(),
        nome=payload.nome,
        servico_ids=tuple(uuid.UUID(str(item)) for item in payload.servico_ids),
        duracao_total_minutos=payload.duracao_total_minutos,
        preco=payload.preco,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = use_case.executar(pacote)
    return PacoteOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        servico_ids=[str(item) for item in salvo.servico_ids],
        duracao_total_minutos=salvo.duracao_total_minutos,
        preco=salvo.preco,
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.put(
    "/pacotes/{pacote_id}",
    response_model=PacoteOutput,
    tags=["Pacotes"],
    summary="Atualiza pacote",
    description="Altera nome, serviços, duração ou preço de um pacote existente.",
)
def atualizar_pacote_endpoint(
    pacote_id: str,
    payload: PacoteInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_pacote),
) -> PacoteOutput:
    repo = PacoteRepository(app.state.engine)
    pacote = repo.buscar_por_id(uuid.UUID(pacote_id))
    if pacote is None:
        raise HTTPException(status_code=404, detail="Pacote não encontrado")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=pacote.organizacao_id,
        profissional_id=pacote.profissional_id,
        permissao="pacote.gerenciar",
    )
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="pacote.gerenciar",
    )
    servico_repo = ServicoRepository(app.state.engine)
    servicos = [
        servico_repo.buscar_por_id(uuid.UUID(str(servico_id)))
        for servico_id in payload.servico_ids
    ]
    if any(servico is None for servico in servicos):
        raise HTTPException(status_code=422, detail="pacote referencia servico inexistente")
    atualizado = Pacote(
        id=pacote.id,
        nome=payload.nome,
        servico_ids=tuple(uuid.UUID(str(item)) for item in payload.servico_ids),
        duracao_total_minutos=payload.duracao_total_minutos,
        preco=payload.preco,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = repo.atualizar(atualizado)
    return PacoteOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        servico_ids=[str(item) for item in salvo.servico_ids],
        duracao_total_minutos=salvo.duracao_total_minutos,
        preco=salvo.preco,
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.delete(
    "/pacotes/{pacote_id}",
    status_code=200,
    tags=["Pacotes"],
    summary="Remove pacote",
    description="Exclui um pacote de serviços do catálogo.",
)
def remover_pacote_endpoint(
    pacote_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_pacote),
) -> dict[str, str]:
    repo = PacoteRepository(app.state.engine)
    pacote = repo.buscar_por_id(uuid.UUID(pacote_id))
    if pacote is None:
        raise HTTPException(status_code=404, detail="Pacote não encontrado")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=pacote.organizacao_id,
        profissional_id=pacote.profissional_id,
        permissao="pacote.gerenciar",
    )
    repo.remover(uuid.UUID(pacote_id))
    return {"status": "deleted"}


@app.post(
    "/disponibilidades",
    response_model=DisponibilidadeOutput,
    tags=["Disponibilidade"],
    summary="Cria disponibilidade",
    description="Define janelas de agenda recorrentes e exceções para profissionais ou organizações.",
)
def criar_disponibilidade_endpoint(
    payload: DisponibilidadeInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_agenda),
) -> DisponibilidadeOutput:
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="agenda.configurar",
    )
    repo = DisponibilidadeRepository(app.state.engine)
    use_case = CriarDisponibilidade(repo)
    disponibilidade = Disponibilidade(
        id=uuid.uuid7(),
        semanal=tuple(
            JanelaSemanal(
                dia_semana=item.dia_semana,
                intervalo=IntervaloHorario(inicio=item.intervalo.inicio, fim=item.intervalo.fim),
            )
            for item in payload.semanal
        ),
        excecoes=tuple(
            ExcecaoAgenda(
                data=item.data,
                intervalos=tuple(
                    IntervaloHorario(inicio=i.inicio, fim=i.fim)
                    for i in item.intervalos
                ),
            )
            for item in payload.excecoes
        ),
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = use_case.executar(disponibilidade)
    return DisponibilidadeOutput(
        id=str(salvo.id),
        semanal=[
            {"dia_semana": item.dia_semana, "intervalo": {"inicio": item.intervalo.inicio.isoformat(), "fim": item.intervalo.fim.isoformat()}}
            for item in salvo.semanal
        ],
        excecoes=[
            {"data": item.data.isoformat(), "intervalos": [{"inicio": i.inicio.isoformat(), "fim": i.fim.isoformat()} for i in item.intervalos]}
            for item in salvo.excecoes
        ],
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.put(
    "/disponibilidades/{disponibilidade_id}",
    response_model=DisponibilidadeOutput,
    tags=["Disponibilidade"],
    summary="Atualiza disponibilidade",
    description="Substitui janelas semanais e exceções de uma disponibilidade existente.",
)
def atualizar_disponibilidade_endpoint(
    disponibilidade_id: str,
    payload: DisponibilidadeInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_agenda),
) -> DisponibilidadeOutput:
    repo = DisponibilidadeRepository(app.state.engine)
    disponibilidade = repo.buscar_por_id(uuid.UUID(disponibilidade_id))
    if disponibilidade is None:
        raise HTTPException(status_code=404, detail="Disponibilidade não encontrada")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=disponibilidade.organizacao_id,
        profissional_id=disponibilidade.profissional_id,
        permissao="agenda.configurar",
    )
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="agenda.configurar",
    )
    atualizada = Disponibilidade(
        id=disponibilidade.id,
        semanal=tuple(
            JanelaSemanal(
                dia_semana=item.dia_semana,
                intervalo=IntervaloHorario(inicio=item.intervalo.inicio, fim=item.intervalo.fim),
            )
            for item in payload.semanal
        ),
        excecoes=tuple(
            ExcecaoAgenda(
                data=item.data,
                intervalos=tuple(
                    IntervaloHorario(inicio=i.inicio, fim=i.fim)
                    for i in item.intervalos
                ),
            )
            for item in payload.excecoes
        ),
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = repo.atualizar(atualizada)
    return DisponibilidadeOutput(
        id=str(salvo.id),
        semanal=[
            {"dia_semana": item.dia_semana, "intervalo": {"inicio": item.intervalo.inicio.isoformat(), "fim": item.intervalo.fim.isoformat()}}
            for item in salvo.semanal
        ],
        excecoes=[
            {"data": item.data.isoformat(), "intervalos": [{"inicio": i.inicio.isoformat(), "fim": i.fim.isoformat()} for i in item.intervalos]}
            for item in salvo.excecoes
        ],
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.delete(
    "/disponibilidades/{disponibilidade_id}",
    status_code=200,
    tags=["Disponibilidade"],
    summary="Remove disponibilidade",
    description="Exclui uma disponibilidade cadastrada.",
)
def remover_disponibilidade_endpoint(
    disponibilidade_id: str,
    identidade: IdentidadeExterna = Depends(exigir_configurar_agenda),
) -> dict[str, str]:
    repo = DisponibilidadeRepository(app.state.engine)
    disponibilidade = repo.buscar_por_id(uuid.UUID(disponibilidade_id))
    if disponibilidade is None:
        raise HTTPException(status_code=404, detail="Disponibilidade não encontrada")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=disponibilidade.organizacao_id,
        profissional_id=disponibilidade.profissional_id,
        permissao="agenda.configurar",
    )
    repo.remover(uuid.UUID(disponibilidade_id))
    return {"status": "deleted"}


@app.get(
    "/horarios-livres",
    response_model=list[HorarioLivreOutput],
    tags=["Disponibilidade"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Consulta horários livres",
    description=(
        "Retorna horários que cabem na disponibilidade do profissional ou organização "
        "e não conflitam com agendamentos existentes."
    ),
)
def consultar_horarios_livres_endpoint(
    profissional_id: str,
    data: date,
    duracao_minutos: int,
    passo_minutos: int = 15,
    organizacao_id: str | None = None,
) -> list[HorarioLivreOutput]:
    try:
        slots = ConsultarHorariosLivres(
            DisponibilidadeRepository(app.state.engine),
            AgendamentoRepository(app.state.engine),
        ).executar(
            profissional_id=uuid.UUID(profissional_id),
            data=data,
            duracao_minutos=duracao_minutos,
            passo_minutos=passo_minutos,
            organizacao_id=uuid.UUID(organizacao_id) if organizacao_id else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return [HorarioLivreOutput(inicio=slot.inicio, fim=slot.fim) for slot in slots]


@app.post(
    "/agendamentos",
    response_model=AgendamentoOutput,
    tags=["Agendamentos"],
    dependencies=[Depends(exigir_solicitar_agendamento)],
    summary="Cria agendamento",
    description="Registra um novo agendamento com cliente, profissional, itens e status inicial.",
)
def criar_agendamento_endpoint(payload: AgendamentoInput) -> AgendamentoOutput:
    repo = AgendamentoRepository(app.state.engine)
    use_case = CriarAgendamento(repo)
    servico_repo = ServicoRepository(app.state.engine)
    pacote_repo = PacoteRepository(app.state.engine)
    for item in payload.itens:
        if item.servico_id is not None:
            if servico_repo.buscar_por_id(uuid.UUID(str(item.servico_id))) is None:
                raise HTTPException(status_code=422, detail="servico do agendamento nao encontrado")
        elif item.pacote_id is not None:
            if pacote_repo.buscar_por_id(uuid.UUID(str(item.pacote_id))) is None:
                raise HTTPException(status_code=422, detail="pacote do agendamento nao encontrado")
    agendamento = Agendamento(
        id=uuid.uuid7(),
        cliente_id=uuid.UUID(str(payload.cliente_id)),
        profissional_id=uuid.UUID(str(payload.profissional_id)),
        inicio=payload.inicio,
        itens=tuple(
            ItemAgendamento(
                servico_id=uuid.UUID(str(item.servico_id)) if item.servico_id else None,
                pacote_id=uuid.UUID(str(item.pacote_id)) if item.pacote_id else None,
                duracao_minutos=item.duracao_minutos,
                preco=item.preco,
            )
            for item in payload.itens
        ),
        status_atual=payload.status_atual,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
    )
    disponibilidades = DisponibilidadeRepository(app.state.engine).listar()
    aplicaveis = [
        disponibilidade
        for disponibilidade in disponibilidades
        if disponibilidade.profissional_id == agendamento.profissional_id
        or (
            agendamento.organizacao_id is not None
            and disponibilidade.organizacao_id == agendamento.organizacao_id
        )
    ]
    if aplicaveis and not any(
        disponibilidade.esta_disponivel(
            agendamento.inicio.date(),
            agendamento.inicio.time(),
            (agendamento.inicio + timedelta(minutes=agendamento.duracao_total_minutos)).time(),
        )
        for disponibilidade in aplicaveis
    ):
        raise HTTPException(
            status_code=409,
            detail="horario solicitado nao esta disponivel para o profissional",
        )
    try:
        salvo = use_case.executar(agendamento)
    except AgendamentoInvalidoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AgendamentoOutput(
        id=str(salvo.id),
        cliente_id=str(salvo.cliente_id),
        profissional_id=str(salvo.profissional_id),
        inicio=salvo.inicio,
        itens=[
            {
                "servico_id": str(item.servico_id) if item.servico_id else None,
                "pacote_id": str(item.pacote_id) if item.pacote_id else None,
                "duracao_minutos": item.duracao_minutos,
                "preco": str(item.preco),
            }
            for item in salvo.itens
        ],
        status_atual=salvo.status_atual,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.post(
    "/agendamentos/{agendamento_id}/transicoes",
    response_model=AgendamentoOutput,
    tags=["Agendamentos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Transiciona agendamento",
    description="Aplica uma transição permitida pelo catálogo persistido de status.",
)
def transicionar_agendamento_endpoint(
    agendamento_id: str,
    payload: TransicionarAgendamentoInput,
    identidade: IdentidadeExterna | None = Depends(identidade_autenticada),
) -> AgendamentoOutput:
    agendamento_repo = AgendamentoRepository(app.state.engine)
    agendamento = agendamento_repo.buscar_por_id(uuid.UUID(agendamento_id))
    if agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
    if identidade is not None:
        usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
            identidade.provider,
            identidade.subject,
        )
        if usuario is None:
            raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
        ator_permitido = False
        if payload.ator == "cliente":
            ator_permitido = usuario.id == agendamento.cliente_id
        elif payload.ator == "profissional":
            ator_permitido = usuario.id == agendamento.profissional_id
            if not ator_permitido and agendamento.organizacao_id is not None:
                ator_permitido = any(
                    membership.organizacao_id == agendamento.organizacao_id
                    and membership.tem_permissao("agendamento.transicionar_status")
                    for membership in MembershipRepository(app.state.engine).listar_por_usuario_id(usuario.id)
                )
        if not ator_permitido:
            raise HTTPException(status_code=403, detail="ator nao autorizado para este agendamento")
    ja_concluido = any(
        registro.status == "concluido" for registro in agendamento.historico
    )
    try:
        agendamento.transicionar_para(
            payload.novo_status,
            payload.ator,
            CatalogoStatusRepository(app.state.engine).obter(),
            datetime.now(tz=agendamento.inicio.tzinfo),
        )
    except (AgendamentoInvalidoError, TransicaoAgendamentoNaoPermitidaError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    salvo = agendamento_repo.atualizar(agendamento)
    if agendamento.status_atual == "concluido" and not ja_concluido:
        RegistrarFidelidadeAgendamento(
            ProgramaFidelidadeRepository(app.state.engine),
            ProgressoFidelidadeRepository(app.state.engine),
        ).executar(agendamento)
    return agendamento_para_output(salvo)


@app.post(
    "/programas-fidelidade",
    response_model=ProgramaFidelidadeOutput,
    tags=["Fidelidade"],
    summary="Cria programa de fidelidade",
    description="Define um programa de fidelidade com regra de atendimento e recompensa.",
)
def criar_programa_fidelidade_endpoint(
    payload: ProgramaFidelidadeInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_fidelidade),
) -> ProgramaFidelidadeOutput:
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="fidelidade.configurar_programa",
    )
    repo = ProgramaFidelidadeRepository(app.state.engine)
    use_case = CriarProgramaFidelidade(repo)
    programa = ProgramaFidelidade(
        id=uuid.uuid7(),
        nome=payload.nome,
        alvo_servico_id=uuid.UUID(str(payload.alvo_servico_id)) if payload.alvo_servico_id else None,
        alvo_pacote_id=uuid.UUID(str(payload.alvo_pacote_id)) if payload.alvo_pacote_id else None,
        atendimentos_necessarios=payload.atendimentos_necessarios,
        recompensa=RecompensaFidelidade(
            tipo=payload.recompensa.tipo,
            valor=payload.recompensa.valor,
            alvo_id=uuid.UUID(str(payload.recompensa.alvo_id)) if payload.recompensa.alvo_id else None,
        ),
        segmento_cliente=payload.segmento_cliente,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = use_case.executar(programa)
    return ProgramaFidelidadeOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        alvo_servico_id=str(salvo.alvo_servico_id) if salvo.alvo_servico_id else None,
        alvo_pacote_id=str(salvo.alvo_pacote_id) if salvo.alvo_pacote_id else None,
        atendimentos_necessarios=salvo.atendimentos_necessarios,
        recompensa={
            "tipo": salvo.recompensa.tipo,
            "valor": str(salvo.recompensa.valor) if salvo.recompensa.valor is not None else None,
            "alvo_id": str(salvo.recompensa.alvo_id) if salvo.recompensa.alvo_id else None,
        },
        segmento_cliente=salvo.segmento_cliente,
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.put(
    "/programas-fidelidade/{programa_id}",
    response_model=ProgramaFidelidadeOutput,
    tags=["Fidelidade"],
    summary="Atualiza programa de fidelidade",
    description="Altera critério de contagem, recompensa ou segmento de um programa existente.",
)
def atualizar_programa_fidelidade_endpoint(
    programa_id: str,
    payload: ProgramaFidelidadeInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_fidelidade),
) -> ProgramaFidelidadeOutput:
    repo = ProgramaFidelidadeRepository(app.state.engine)
    programa = repo.buscar_por_id(uuid.UUID(programa_id))
    if programa is None:
        raise HTTPException(status_code=404, detail="Programa de fidelidade não encontrado")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=programa.organizacao_id,
        profissional_id=programa.profissional_id,
        permissao="fidelidade.configurar_programa",
    )
    profissional_id = uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None
    organizacao_id = uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None
    exigir_acesso_oferta(
        identidade,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
        permissao="fidelidade.configurar_programa",
    )
    atualizado = ProgramaFidelidade(
        id=programa.id,
        nome=payload.nome,
        alvo_servico_id=uuid.UUID(str(payload.alvo_servico_id)) if payload.alvo_servico_id else None,
        alvo_pacote_id=uuid.UUID(str(payload.alvo_pacote_id)) if payload.alvo_pacote_id else None,
        atendimentos_necessarios=payload.atendimentos_necessarios,
        recompensa=RecompensaFidelidade(
            tipo=payload.recompensa.tipo,
            valor=payload.recompensa.valor,
            alvo_id=uuid.UUID(str(payload.recompensa.alvo_id)) if payload.recompensa.alvo_id else None,
        ),
        segmento_cliente=payload.segmento_cliente,
        profissional_id=profissional_id,
        organizacao_id=organizacao_id,
    )
    salvo = repo.atualizar(atualizado)
    return ProgramaFidelidadeOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        alvo_servico_id=str(salvo.alvo_servico_id) if salvo.alvo_servico_id else None,
        alvo_pacote_id=str(salvo.alvo_pacote_id) if salvo.alvo_pacote_id else None,
        atendimentos_necessarios=salvo.atendimentos_necessarios,
        recompensa={
            "tipo": salvo.recompensa.tipo,
            "valor": str(salvo.recompensa.valor) if salvo.recompensa.valor is not None else None,
            "alvo_id": str(salvo.recompensa.alvo_id) if salvo.recompensa.alvo_id else None,
        },
        segmento_cliente=salvo.segmento_cliente,
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
    )


@app.delete(
    "/programas-fidelidade/{programa_id}",
    status_code=200,
    tags=["Fidelidade"],
    summary="Remove programa de fidelidade",
    description="Exclui um programa de fidelidade do catálogo.",
)
def remover_programa_fidelidade_endpoint(
    programa_id: str,
    identidade: IdentidadeExterna = Depends(exigir_configurar_fidelidade),
) -> dict[str, str]:
    repo = ProgramaFidelidadeRepository(app.state.engine)
    programa = repo.buscar_por_id(uuid.UUID(programa_id))
    if programa is None:
        raise HTTPException(status_code=404, detail="Programa de fidelidade não encontrado")
    exigir_acesso_oferta(
        identidade,
        organizacao_id=programa.organizacao_id,
        profissional_id=programa.profissional_id,
        permissao="fidelidade.configurar_programa",
    )
    repo.remover(uuid.UUID(programa_id))
    return {"status": "deleted"}


@app.post(
    "/progresso-fidelidade",
    response_model=ProgressoFidelidadeOutput,
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Registra progresso de fidelidade",
    description="Atualiza o avanço do cliente em um programa de fidelidade.",
)
def registrar_progresso_fidelidade_endpoint(payload: ProgressoFidelidadeInput) -> ProgressoFidelidadeOutput:
    repo = ProgressoFidelidadeRepository(app.state.engine)
    use_case = RegistrarProgressoFidelidade(repo)
    progresso = ProgressoFidelidade(
        programa_id=uuid.UUID(str(payload.programa_id)),
        cliente_id=uuid.UUID(str(payload.cliente_id)),
        atendimentos_concluidos=payload.atendimentos_concluidos,
    )
    salvo = use_case.executar(progresso)
    return ProgressoFidelidadeOutput(
        programa_id=str(salvo.programa_id),
        cliente_id=str(salvo.cliente_id),
        atendimentos_concluidos=salvo.atendimentos_concluidos,
    )


@app.post(
    "/fidelidade/resgates",
    response_model=ResgateFidelidadeOutput,
    tags=["Fidelidade"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Resgata recompensa de fidelidade",
    description="Aplica desconto ou gratuidade, consome o progresso e registra o resgate.",
)
def resgatar_fidelidade_endpoint(payload: ResgateFidelidadeInput) -> ResgateFidelidadeOutput:
    try:
        resultado = ResgatarFidelidade(
            ProgramaFidelidadeRepository(app.state.engine),
            ProgressoFidelidadeRepository(app.state.engine),
            ResgateFidelidadeRepository(app.state.engine),
        ).executar(
            programa_id=uuid.UUID(payload.programa_id),
            cliente_id=uuid.UUID(payload.cliente_id),
            preco=payload.preco,
            agendamento_id=uuid.UUID(payload.agendamento_id) if payload.agendamento_id else None,
        )
    except (ValueError, FidelidadeInvalidaError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ResgateFidelidadeOutput(
        resgate_id=str(resultado.resgate_id),
        programa_id=str(resultado.aplicacao.programa_id),
        cliente_id=str(resultado.aplicacao.cliente_id),
        preco_original=resultado.aplicacao.preco_original,
        desconto=resultado.aplicacao.desconto,
        preco_final=resultado.aplicacao.preco_final,
        gratuito=resultado.aplicacao.gratuito,
        atendimentos_restantes=resultado.progresso.atendimentos_concluidos,
    )


def _registro_resgate_para_output(registro: object) -> ResgateFidelidadeRegistroOutput:
    return ResgateFidelidadeRegistroOutput(
        resgate_id=registro.id,
        programa_id=registro.programa_id,
        cliente_id=registro.cliente_id,
        agendamento_id=registro.agendamento_id,
        preco_original=Decimal(registro.preco_original),
        desconto=Decimal(registro.desconto),
        preco_final=Decimal(registro.preco_final),
        gratuito=registro.gratuito,
    )


def _acesso_permitido_ao_programa(
    identidade: IdentidadeExterna, usuario_id: uuid.UUID, programa_id: str
) -> bool:
    programa = ProgramaFidelidadeRepository(app.state.engine).buscar_por_id(uuid.UUID(programa_id))
    if programa is None:
        return False
    if programa.profissional_id == usuario_id:
        return True
    if programa.organizacao_id is None:
        return False
    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(usuario_id)
    return any(
        membership.organizacao_id == programa.organizacao_id and membership.ativo
        for membership in memberships
    )


@app.get(
    "/fidelidade/resgates",
    response_model=list[ResgateFidelidadeRegistroOutput],
    tags=["Fidelidade"],
    summary="Lista resgates de fidelidade",
    description="Retorna os resgates dos programas de fidelidade que o usuário autenticado pode gerenciar.",
)
def listar_resgates_fidelidade_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[ResgateFidelidadeRegistroOutput]:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    repo = ResgateFidelidadeRepository(app.state.engine)
    return [
        _registro_resgate_para_output(registro)
        for registro in repo.listar()
        if _acesso_permitido_ao_programa(identidade, usuario.id, registro.programa_id)
    ]


@app.get(
    "/fidelidade/resgates/{resgate_id}",
    response_model=ResgateFidelidadeRegistroOutput,
    tags=["Fidelidade"],
    summary="Busca resgate de fidelidade por ID",
)
def buscar_resgate_fidelidade_endpoint(
    resgate_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ResgateFidelidadeRegistroOutput:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    registro = ResgateFidelidadeRepository(app.state.engine).buscar_por_id(uuid.UUID(resgate_id))
    if registro is None:
        raise HTTPException(status_code=404, detail="Resgate de fidelidade não encontrado")
    if not _acesso_permitido_ao_programa(identidade, usuario.id, registro.programa_id):
        raise HTTPException(status_code=403, detail="sem acesso ao programa deste resgate")
    return _registro_resgate_para_output(registro)


@app.post(
    "/lembretes",
    tags=["Notificações"],
    dependencies=[Depends(identidade_autenticada)],
    response_model=LembreteOutput,
    summary="Cria lembrete",
    description="Gera uma notificação de lembrete com base no agendamento, canal e configuração informados.",
)
def criar_lembrete_endpoint(payload: LembreteInput) -> LembreteOutput:
    repo = NotificacaoAgendamentoRepository(app.state.engine)
    use_case = CriarNotificacaoAgendamento(repo)
    agendamento = Agendamento(
        id=uuid.uuid7(),
        cliente_id=uuid.UUID(str(payload.agendamento.cliente_id)),
        profissional_id=uuid.UUID(str(payload.agendamento.profissional_id)),
        inicio=payload.agendamento.inicio,
        itens=tuple(
            ItemAgendamento(
                servico_id=uuid.UUID(str(item.servico_id)) if item.servico_id else None,
                pacote_id=uuid.UUID(str(item.pacote_id)) if item.pacote_id else None,
                duracao_minutos=item.duracao_minutos,
                preco=item.preco,
            )
            for item in payload.agendamento.itens
        ),
        status_atual=payload.agendamento.status_atual,
        organizacao_id=uuid.UUID(str(payload.agendamento.organizacao_id)) if payload.agendamento.organizacao_id else None,
    )
    configuracao = ConfiguracaoLembrete(
        antecedencia=timedelta(hours=int(payload.configuracao.get("antecedencia_horas", 2))),
        canal=str(payload.configuracao.get("canal", "email")),
    )
    destinatario = DestinatarioNotificacao(
        id=payload.destinatario.id,
        canal=payload.destinatario.canal,
        destino=payload.destinatario.destino,
    )
    notificacao = use_case.executar(
        agendamento=agendamento,
        configuracao=configuracao,
        destinatario=destinatario,
        mensagem=payload.mensagem,
    )
    return LembreteOutput(
        agendamento_id=notificacao.agendamento_id,
        destinatario=DestinatarioNotificacaoInput(
            id=notificacao.destinatario.id,
            canal=notificacao.destinatario.canal,
            destino=notificacao.destinatario.destino,
        ),
        mensagem=notificacao.mensagem,
        enviar_em=notificacao.enviar_em,
    )


@app.post(
    "/agendamentos/{agendamento_id}/lembretes",
    tags=["Notificações"],
    dependencies=[Depends(identidade_autenticada)],
    response_model=LembreteOutput,
    summary="Cria lembrete de agendamento persistido",
    description="Gera lembrete usando o agendamento já armazenado, sem aceitar dados comerciais duplicados.",
)
def criar_lembrete_agendamento_endpoint(
    agendamento_id: str,
    payload: LembretePersistidoInput,
) -> LembreteOutput:
    agendamento = AgendamentoRepository(app.state.engine).buscar_por_id(
        uuid.UUID(agendamento_id)
    )
    if agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

    try:
        configuracao = ConfiguracaoLembrete(
            antecedencia=timedelta(
                hours=int(payload.configuracao.get("antecedencia_horas", 2))
            ),
            canal=str(payload.configuracao.get("canal", "email")),
        )
        notificacao = CriarNotificacaoAgendamento(
            NotificacaoAgendamentoRepository(app.state.engine)
        ).executar(
            agendamento=agendamento,
            configuracao=configuracao,
            destinatario=DestinatarioNotificacao(
                id=payload.destinatario.id,
                canal=payload.destinatario.canal,
                destino=payload.destinatario.destino,
            ),
            mensagem=payload.mensagem,
        )
    except (ValueError, LembreteInvalidoError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LembreteOutput(
        agendamento_id=notificacao.agendamento_id,
        destinatario=DestinatarioNotificacaoInput(
            id=notificacao.destinatario.id,
            canal=notificacao.destinatario.canal,
            destino=notificacao.destinatario.destino,
        ),
        mensagem=notificacao.mensagem,
        enviar_em=notificacao.enviar_em,
    )


def _notificacao_para_output(notificacao: object) -> NotificacaoOutput:
    return NotificacaoOutput(
        agendamento_id=notificacao.agendamento_id,
        destinatario=DestinatarioNotificacaoInput(
            id=notificacao.destinatario.id,
            canal=notificacao.destinatario.canal,
            destino=notificacao.destinatario.destino,
        ),
        mensagem=notificacao.mensagem,
        enviar_em=notificacao.enviar_em,
        status=notificacao.status,
        tentativas=notificacao.tentativas,
        erro=notificacao.erro,
        enviado_em=notificacao.enviado_em,
    )


def _acesso_permitido_ao_agendamento(
    identidade: IdentidadeExterna, usuario_id: uuid.UUID, agendamento_id: str
) -> bool:
    agendamento = AgendamentoRepository(app.state.engine).buscar_por_id(uuid.UUID(agendamento_id))
    if agendamento is None:
        return False
    if agendamento.profissional_id == usuario_id:
        return True
    if agendamento.organizacao_id is None:
        return False
    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(usuario_id)
    return any(
        membership.organizacao_id == agendamento.organizacao_id and membership.ativo
        for membership in memberships
    )


@app.get(
    "/lembretes",
    response_model=list[NotificacaoOutput],
    tags=["Notificações"],
    summary="Lista lembretes/notificações",
    description="Retorna os lembretes de agendamentos que o usuário autenticado pode gerenciar.",
)
def listar_lembretes_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[NotificacaoOutput]:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    repo = NotificacaoAgendamentoRepository(app.state.engine)
    return [
        _notificacao_para_output(notificacao)
        for notificacao in repo.listar()
        if _acesso_permitido_ao_agendamento(identidade, usuario.id, notificacao.agendamento_id)
    ]


@app.get(
    "/agendamentos/{agendamento_id}/lembretes",
    response_model=NotificacaoOutput,
    tags=["Notificações"],
    summary="Busca lembrete por agendamento",
)
def buscar_lembrete_agendamento_endpoint(
    agendamento_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> NotificacaoOutput:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider, identidade.subject
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    if not _acesso_permitido_ao_agendamento(identidade, usuario.id, agendamento_id):
        raise HTTPException(status_code=403, detail="sem acesso ao agendamento deste lembrete")
    notificacao = NotificacaoAgendamentoRepository(app.state.engine).buscar_por_agendamento_id(
        agendamento_id
    )
    if notificacao is None:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    return _notificacao_para_output(notificacao)


@app.post(
    "/notificacoes/processar-vencidas",
    tags=["Notificações"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Processa notificações vencidas",
    description="Entrega notificações pendentes cujo horário chegou e registra sucesso ou falha.",
)
def processar_notificacoes_vencidas_endpoint() -> dict[str, int]:
    if not settings.notificacao_webhook_url:
        raise HTTPException(status_code=503, detail="entregador de notificacao nao configurado")
    return ProcessarNotificacoesVencidas(
        NotificacaoAgendamentoRepository(app.state.engine),
        WebhookNotificacaoAdapter(base_url=settings.notificacao_webhook_url),
        max_tentativas=settings.notificacao_max_tentativas,
    ).executar(datetime.now())


@app.post(
    "/comissoes/calcular",
    tags=["Comissão"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Calcula comissão",
    description="Calcula o valor de comissão para um agendamento usando as regras e o status informados.",
)
def calcular_comissao_endpoint(payload: ComissaoInput) -> dict[str, str]:
    agendamento = Agendamento(
        id=uuid.uuid7(),
        cliente_id=uuid.UUID(str(payload.agendamento.cliente_id)),
        profissional_id=uuid.UUID(str(payload.agendamento.profissional_id)),
        inicio=payload.agendamento.inicio,
        itens=tuple(
            ItemAgendamento(
                servico_id=uuid.UUID(str(item.servico_id)) if item.servico_id else None,
                pacote_id=uuid.UUID(str(item.pacote_id)) if item.pacote_id else None,
                duracao_minutos=item.duracao_minutos,
                preco=item.preco,
            )
            for item in payload.agendamento.itens
        ),
        status_atual=payload.agendamento.status_atual,
        organizacao_id=uuid.UUID(str(payload.agendamento.organizacao_id)) if payload.agendamento.organizacao_id else None,
    )
    regras = tuple(
        RegraComissao(
            id=uuid.UUID(str(item.id)),
            tipo=item.tipo,
            valor=item.valor,
            membership_id=uuid.UUID(str(item.membership_id)) if item.membership_id else None,
            servico_id=uuid.UUID(str(item.servico_id)) if item.servico_id else None,
        )
        for item in payload.regras
    )
    valor = CalcularComissaoAgendamento().executar(
        agendamento=agendamento,
        membership_id=uuid.UUID(str(payload.membership_id)),
        regras=regras,
        status_concluido=payload.status_concluido,
    )
    return {"valor": str(valor)}


@app.post(
    "/comissoes/regras",
    response_model=RegraComissaoOutput,
    tags=["Comissão"],
    summary="Cria regra de comissão",
    description="Persiste uma regra de comissão configurada para membership ou serviço.",
)
def criar_regra_comissao_endpoint(
    payload: RegraComissaoInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_comissao),
) -> RegraComissaoOutput:
    regra = RegraComissao(
        id=uuid.UUID(payload.id),
        tipo=payload.tipo,
        valor=payload.valor,
        membership_id=uuid.UUID(payload.membership_id) if payload.membership_id else None,
        servico_id=uuid.UUID(payload.servico_id) if payload.servico_id else None,
    )
    if regra.membership_id is not None:
        membership = MembershipRepository(app.state.engine).buscar_por_id(
            regra.membership_id
        )
        if membership is None or membership.organizacao_id is None:
            raise HTTPException(status_code=422, detail="membership da regra nao encontrado")
        exigir_acesso_organizacao(
            identidade,
            membership.organizacao_id,
            "comissao.configurar_regra",
        )
    elif regra.servico_id is not None:
        servico = ServicoRepository(app.state.engine).buscar_por_id(regra.servico_id)
        if servico is None:
            raise HTTPException(status_code=422, detail="servico da regra nao encontrado")
        exigir_acesso_oferta(
            identidade,
            organizacao_id=servico.organizacao_id,
            profissional_id=servico.profissional_id,
            permissao="comissao.configurar_regra",
        )
    salvo = RegraComissaoRepository(app.state.engine).salvar(regra)
    return RegraComissaoOutput(
        id=str(salvo.id),
        tipo=salvo.tipo,
        valor=salvo.valor,
        membership_id=str(salvo.membership_id) if salvo.membership_id else None,
        servico_id=str(salvo.servico_id) if salvo.servico_id else None,
    )


@app.get(
    "/comissoes/regras",
    response_model=list[RegraComissaoOutput],
    tags=["Comissão"],
    summary="Lista regras de comissão",
)
def listar_regras_comissao_endpoint(
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> list[RegraComissaoOutput]:
    usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
        identidade.provider,
        identidade.subject,
    )
    if usuario is None:
        raise HTTPException(status_code=403, detail="identidade externa sem usuario interno")
    memberships = MembershipRepository(app.state.engine).listar_por_usuario_id(usuario.id)
    organizacoes = {
        membership.organizacao_id
        for membership in memberships
        if membership.ativo
    }
    membership_ids = {membership.id for membership in memberships if membership.ativo}
    servicos = ServicoRepository(app.state.engine).listar()
    return [
        RegraComissaoOutput(
            id=str(regra.id),
            tipo=regra.tipo,
            valor=regra.valor,
            membership_id=str(regra.membership_id) if regra.membership_id else None,
            servico_id=str(regra.servico_id) if regra.servico_id else None,
        )
        for regra in RegraComissaoRepository(app.state.engine).listar()
        if (
            regra.membership_id in membership_ids
            or (
                regra.servico_id is not None
                and any(
                    servico.id == regra.servico_id
                    and (
                        servico.profissional_id == usuario.id
                        or servico.organizacao_id in organizacoes
                    )
                    for servico in servicos
                )
            )
        )
    ]


def _exigir_acesso_regra_comissao(
    identidade: IdentidadeExterna, regra: RegraComissao
) -> None:
    if regra.membership_id is not None:
        membership = MembershipRepository(app.state.engine).buscar_por_id(regra.membership_id)
        if membership is None or membership.organizacao_id is None:
            raise HTTPException(status_code=422, detail="membership da regra nao encontrado")
        exigir_acesso_organizacao(identidade, membership.organizacao_id, "comissao.configurar_regra")
    elif regra.servico_id is not None:
        servico = ServicoRepository(app.state.engine).buscar_por_id(regra.servico_id)
        if servico is None:
            raise HTTPException(status_code=422, detail="servico da regra nao encontrado")
        exigir_acesso_oferta(
            identidade,
            organizacao_id=servico.organizacao_id,
            profissional_id=servico.profissional_id,
            permissao="comissao.configurar_regra",
        )


@app.get(
    "/comissoes/regras/{regra_id}",
    response_model=RegraComissaoOutput,
    tags=["Comissão"],
    summary="Busca regra de comissão por ID",
)
def buscar_regra_comissao_endpoint(
    regra_id: str,
    identidade: IdentidadeExterna = Depends(exigir_configurar_comissao),
) -> RegraComissaoOutput:
    regra = RegraComissaoRepository(app.state.engine).buscar_por_id(uuid.UUID(regra_id))
    if regra is None:
        raise HTTPException(status_code=404, detail="Regra de comissão não encontrada")
    _exigir_acesso_regra_comissao(identidade, regra)
    return RegraComissaoOutput(
        id=str(regra.id),
        tipo=regra.tipo,
        valor=regra.valor,
        membership_id=str(regra.membership_id) if regra.membership_id else None,
        servico_id=str(regra.servico_id) if regra.servico_id else None,
    )


@app.put(
    "/comissoes/regras/{regra_id}",
    response_model=RegraComissaoOutput,
    tags=["Comissão"],
    summary="Atualiza regra de comissão",
    description="Altera tipo, valor ou associação de uma regra de comissão existente.",
)
def atualizar_regra_comissao_endpoint(
    regra_id: str,
    payload: RegraComissaoInput,
    identidade: IdentidadeExterna = Depends(exigir_configurar_comissao),
) -> RegraComissaoOutput:
    repo = RegraComissaoRepository(app.state.engine)
    regra = repo.buscar_por_id(uuid.UUID(regra_id))
    if regra is None:
        raise HTTPException(status_code=404, detail="Regra de comissão não encontrada")
    _exigir_acesso_regra_comissao(identidade, regra)
    atualizada = RegraComissao(
        id=regra.id,
        tipo=payload.tipo,
        valor=payload.valor,
        membership_id=uuid.UUID(payload.membership_id) if payload.membership_id else None,
        servico_id=uuid.UUID(payload.servico_id) if payload.servico_id else None,
    )
    _exigir_acesso_regra_comissao(identidade, atualizada)
    salvo = repo.atualizar(atualizada)
    return RegraComissaoOutput(
        id=str(salvo.id),
        tipo=salvo.tipo,
        valor=salvo.valor,
        membership_id=str(salvo.membership_id) if salvo.membership_id else None,
        servico_id=str(salvo.servico_id) if salvo.servico_id else None,
    )


@app.delete(
    "/comissoes/regras/{regra_id}",
    status_code=200,
    tags=["Comissão"],
    summary="Remove regra de comissão",
)
def remover_regra_comissao_endpoint(
    regra_id: str,
    identidade: IdentidadeExterna = Depends(exigir_configurar_comissao),
) -> dict[str, str]:
    repo = RegraComissaoRepository(app.state.engine)
    regra = repo.buscar_por_id(uuid.UUID(regra_id))
    if regra is None:
        raise HTTPException(status_code=404, detail="Regra de comissão não encontrada")
    _exigir_acesso_regra_comissao(identidade, regra)
    repo.remover(uuid.UUID(regra_id))
    return {"status": "deleted"}


@app.post(
    "/comissoes/relatorio",
    response_model=ComissaoRelatorioOutput,
    tags=["Comissão"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Gera relatório de comissão",
    description="Calcula a comissão devida sobre os agendamentos concluídos persistidos.",
)
def gerar_relatorio_comissao_endpoint(
    payload: ComissaoRelatorioInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> ComissaoRelatorioOutput:
    membership = MembershipRepository(app.state.engine).buscar_por_id(
        uuid.UUID(payload.membership_id)
    )
    if membership is None or membership.organizacao_id is None:
        raise HTTPException(status_code=404, detail="Membership nao encontrado")
    exigir_acesso_organizacao(
        identidade,
        membership.organizacao_id,
        "comissao.visualizar_relatorio",
    )
    regras = tuple(
        RegraComissao(
            id=uuid.UUID(item.id),
            tipo=item.tipo,
            valor=item.valor,
            membership_id=uuid.UUID(item.membership_id) if item.membership_id else None,
            servico_id=uuid.UUID(item.servico_id) if item.servico_id else None,
        )
        for item in payload.regras
    )
    if not regras:
        regras = tuple(RegraComissaoRepository(app.state.engine).listar())
    relatorio = gerar_relatorio_comissao(
        AgendamentoRepository(app.state.engine).listar(),
        uuid.UUID(payload.membership_id),
        regras,
        payload.status_concluido,
    )
    return ComissaoRelatorioOutput(
        membership_id=str(relatorio.membership_id),
        linhas=[
            LinhaComissaoOutput(
                agendamento_id=str(linha.agendamento_id),
                profissional_id=str(linha.profissional_id),
                valor=linha.valor,
            )
            for linha in relatorio.linhas
        ],
        total=relatorio.total,
    )


@app.get(
    "/clientes/{cliente_id}/ficha",
    response_model=FichaConfiabilidadeOutput,
    tags=["Agendamentos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Consulta ficha de confiabilidade",
    description="Retorna cancelamentos, nao comparecimentos e atendimentos concluidos do cliente.",
)
def consultar_ficha_cliente_endpoint(cliente_id: str) -> FichaConfiabilidadeOutput:
    ficha = construir_ficha(
        AgendamentoRepository(app.state.engine).listar(),
        uuid.UUID(cliente_id),
    )
    return FichaConfiabilidadeOutput(
        cliente_id=str(ficha.cliente_id),
        total_agendamentos=ficha.total_agendamentos,
        cancelamentos=ficha.cancelamentos,
        nao_comparecimentos=ficha.nao_comparecimentos,
        concluidos=ficha.concluidos,
    )


@app.get(
    "/estatisticas/operacao",
    response_model=EstatisticasOperacaoOutput,
    tags=["Agendamentos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Consulta estatisticas da operacao",
    description="Retorna volume, no-show, ocupacao e receita registrada dos agendamentos.",
)
def consultar_estatisticas_endpoint(
    organizacao_id: str | None = None,
    profissional_id: str | None = None,
) -> EstatisticasOperacaoOutput:
    estatisticas = construir_estatisticas(
        AgendamentoRepository(app.state.engine).listar(),
        organizacao_id=uuid.UUID(organizacao_id) if organizacao_id else None,
        profissional_id=uuid.UUID(profissional_id) if profissional_id else None,
    )
    return EstatisticasOperacaoOutput(
        total_agendamentos=estatisticas.total_agendamentos,
        concluidos=estatisticas.concluidos,
        cancelados=estatisticas.cancelados,
        nao_comparecimentos=estatisticas.nao_comparecimentos,
        ocupacao_minutos=estatisticas.ocupacao_minutos,
        receita_registrada=estatisticas.receita_registrada,
    )


def _papel_para_output(papel: Papel) -> PapelOutput:
    return PapelOutput(
        id=str(papel.id),
        chave=papel.chave,
        nome=papel.nome,
        permissoes=sorted(papel.permissoes),
    )


@app.get(
    "/catalogo/papeis",
    response_model=list[PapelOutput],
    tags=["Catálogos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista papéis do catálogo",
    description="Retorna todos os papéis (roles) disponíveis para composição de memberships.",
)
def listar_papeis_endpoint() -> list[PapelOutput]:
    return [_papel_para_output(item) for item in PapelRepository(app.state.engine).listar()]


@app.get(
    "/catalogo/papeis/{papel_id}",
    response_model=PapelOutput,
    tags=["Catálogos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca papel por ID",
)
def buscar_papel_endpoint(papel_id: str) -> PapelOutput:
    papel = PapelRepository(app.state.engine).buscar_por_id(uuid.UUID(papel_id))
    if papel is None:
        raise HTTPException(status_code=404, detail="Papel não encontrado")
    return _papel_para_output(papel)


@app.post(
    "/catalogo/papeis",
    response_model=PapelOutput,
    tags=["Catálogos"],
    summary="Cria papel no catálogo",
    description="Adiciona um novo papel (role) com seu conjunto de permissões.",
)
def criar_papel_endpoint(
    payload: PapelInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> PapelOutput:
    repo = PapelRepository(app.state.engine)
    if repo.buscar_por_chave(payload.chave) is not None:
        raise HTTPException(status_code=409, detail="chave de papel ja cadastrada")
    papel = Papel(
        id=uuid.uuid7(),
        chave=payload.chave,
        nome=payload.nome,
        permissoes=frozenset(payload.permissoes),
    )
    return _papel_para_output(repo.salvar(papel))


@app.put(
    "/catalogo/papeis/{papel_id}",
    response_model=PapelOutput,
    tags=["Catálogos"],
    summary="Atualiza papel do catálogo",
    description="Altera nome ou permissões de um papel existente.",
)
def atualizar_papel_endpoint(
    papel_id: str,
    payload: PapelInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> PapelOutput:
    repo = PapelRepository(app.state.engine)
    papel = repo.buscar_por_id(uuid.UUID(papel_id))
    if papel is None:
        raise HTTPException(status_code=404, detail="Papel não encontrado")
    atualizado = Papel(
        id=papel.id,
        chave=payload.chave,
        nome=payload.nome,
        permissoes=frozenset(payload.permissoes),
    )
    return _papel_para_output(repo.atualizar(atualizado))


@app.delete(
    "/catalogo/papeis/{papel_id}",
    status_code=200,
    tags=["Catálogos"],
    summary="Remove papel do catálogo",
    description="Exclui um papel do catálogo; não afeta memberships que já o referenciam.",
)
def remover_papel_endpoint(
    papel_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> dict[str, str]:
    repo = PapelRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(papel_id)) is None:
        raise HTTPException(status_code=404, detail="Papel não encontrado")
    repo.remover(uuid.UUID(papel_id))
    return {"status": "deleted"}


@app.get(
    "/catalogo/status-agendamento",
    response_model=CatalogoStatusOutput,
    tags=["Catálogos"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Consulta catálogo de status de agendamento",
    description="Retorna todos os status possíveis e as transições permitidas entre eles.",
)
def obter_catalogo_status_endpoint() -> CatalogoStatusOutput:
    catalogo = CatalogoStatusRepository(app.state.engine).obter()
    return CatalogoStatusOutput(
        status=[
            StatusAgendamentoInput(chave=item.chave, nome=item.nome)
            for item in catalogo.status
        ],
        transicoes=[
            TransicaoStatusInput(de=item.de, para=item.para, atores=sorted(item.atores))
            for item in catalogo.transicoes
        ],
    )


@app.put(
    "/catalogo/status-agendamento",
    response_model=CatalogoStatusOutput,
    tags=["Catálogos"],
    summary="Adiciona status/transições ao catálogo",
    description=(
        "Adiciona novos status e transições ao catálogo (operação aditiva: não remove "
        "entradas existentes, já que status/transições em uso não podem ser apagados)."
    ),
)
def atualizar_catalogo_status_endpoint(
    payload: CatalogoStatusInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> CatalogoStatusOutput:
    catalogo = CatalogoStatus(
        status=tuple(
            StatusAgendamento(chave=item.chave, nome=item.nome) for item in payload.status
        ),
        transicoes=tuple(
            TransicaoStatus(de=item.de, para=item.para, atores=frozenset(item.atores))
            for item in payload.transicoes
        ),
    )
    CatalogoStatusRepository(app.state.engine).salvar(catalogo)
    atualizado = CatalogoStatusRepository(app.state.engine).obter()
    return CatalogoStatusOutput(
        status=[
            StatusAgendamentoInput(chave=item.chave, nome=item.nome)
            for item in atualizado.status
        ],
        transicoes=[
            TransicaoStatusInput(de=item.de, para=item.para, atores=sorted(item.atores))
            for item in atualizado.transicoes
        ],
    )


def _nome_servico_para_output(nome_servico: NomeServico) -> NomeServicoOutput:
    return NomeServicoOutput(id=str(nome_servico.id), nome=nome_servico.nome)


@app.get(
    "/catalogo/nomes-servico",
    response_model=list[NomeServicoOutput],
    tags=["Catálogos"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista nomes de serviço",
    description="[Público, com rate limit] Lista nomes reutilizáveis do catálogo de serviços.",
)
def listar_nomes_servico_endpoint() -> list[NomeServicoOutput]:
    return [
        _nome_servico_para_output(item)
        for item in NomeServicoRepository(app.state.engine).listar()
    ]


@app.get(
    "/catalogo/nomes-servico/{nome_servico_id}",
    response_model=NomeServicoOutput,
    tags=["Catálogos"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Busca nome de serviço por ID",
)
def buscar_nome_servico_endpoint(nome_servico_id: str) -> NomeServicoOutput:
    nome_servico = NomeServicoRepository(app.state.engine).buscar_por_id(
        uuid.UUID(nome_servico_id)
    )
    if nome_servico is None:
        raise HTTPException(status_code=404, detail="Nome de serviço não encontrado")
    return _nome_servico_para_output(nome_servico)


@app.post(
    "/catalogo/nomes-servico",
    response_model=NomeServicoOutput,
    tags=["Catálogos"],
    summary="Cria nome de serviço",
)
def criar_nome_servico_endpoint(
    payload: NomeServicoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> NomeServicoOutput:
    repo = NomeServicoRepository(app.state.engine)
    if repo.buscar_por_nome(payload.nome) is not None:
        raise HTTPException(status_code=409, detail="nome de serviço já cadastrado")
    nome_servico = NomeServico(id=uuid.uuid7(), nome=payload.nome)
    return _nome_servico_para_output(repo.salvar(nome_servico))


@app.put(
    "/catalogo/nomes-servico/{nome_servico_id}",
    response_model=NomeServicoOutput,
    tags=["Catálogos"],
    summary="Atualiza nome de serviço",
)
def atualizar_nome_servico_endpoint(
    nome_servico_id: str,
    payload: NomeServicoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> NomeServicoOutput:
    repo = NomeServicoRepository(app.state.engine)
    nome_servico = repo.buscar_por_id(uuid.UUID(nome_servico_id))
    if nome_servico is None:
        raise HTTPException(status_code=404, detail="Nome de serviço não encontrado")
    existente = repo.buscar_por_nome(payload.nome)
    if existente is not None and existente.id != nome_servico.id:
        raise HTTPException(status_code=409, detail="nome de serviço já cadastrado")
    atualizado = NomeServico(id=nome_servico.id, nome=payload.nome)
    return _nome_servico_para_output(repo.atualizar(atualizado))


@app.delete(
    "/catalogo/nomes-servico/{nome_servico_id}",
    status_code=200,
    tags=["Catálogos"],
    summary="Remove nome de serviço",
    description="Remove um nome somente quando ele não estiver sendo usado por um serviço.",
)
def remover_nome_servico_endpoint(
    nome_servico_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> dict[str, str]:
    repo = NomeServicoRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(nome_servico_id)) is None:
        raise HTTPException(status_code=404, detail="Nome de serviço não encontrado")
    try:
        repo.remover(uuid.UUID(nome_servico_id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "deleted"}


def _tipo_procedimento_para_output(tipo: TipoProcedimento) -> TipoProcedimentoOutput:
    return TipoProcedimentoOutput(id=str(tipo.id), chave=tipo.chave, nome=tipo.nome)


@app.get(
    "/catalogo/tipos-procedimento",
    response_model=list[TipoProcedimentoOutput],
    tags=["Catálogos"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista tipos de procedimento",
    description=(
        "[Público, com rate limit] Catálogo controlado de tipos de procedimento "
        "(ex: Manicure), usado para manter consistência entre salões/autônomos. "
        "Servico.categoria (texto livre) continua existindo para casos fora do catálogo."
    ),
)
def listar_tipos_procedimento_endpoint() -> list[TipoProcedimentoOutput]:
    repo = TipoProcedimentoRepository(app.state.engine)
    return [_tipo_procedimento_para_output(item) for item in repo.listar()]


@app.get(
    "/catalogo/tipos-procedimento/{tipo_id}",
    response_model=TipoProcedimentoOutput,
    tags=["Catálogos"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Busca tipo de procedimento por ID",
)
def buscar_tipo_procedimento_endpoint(tipo_id: str) -> TipoProcedimentoOutput:
    tipo = TipoProcedimentoRepository(app.state.engine).buscar_por_id(uuid.UUID(tipo_id))
    if tipo is None:
        raise HTTPException(status_code=404, detail="Tipo de procedimento não encontrado")
    return _tipo_procedimento_para_output(tipo)


@app.post(
    "/catalogo/tipos-procedimento",
    response_model=TipoProcedimentoOutput,
    tags=["Catálogos"],
    summary="Cria tipo de procedimento",
    description="Adiciona um novo tipo de procedimento ao catálogo controlado.",
)
def criar_tipo_procedimento_endpoint(
    payload: TipoProcedimentoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> TipoProcedimentoOutput:
    repo = TipoProcedimentoRepository(app.state.engine)
    if repo.buscar_por_chave(payload.chave) is not None:
        raise HTTPException(status_code=409, detail="chave de tipo de procedimento ja cadastrada")
    tipo = TipoProcedimento(id=uuid.uuid7(), chave=payload.chave, nome=payload.nome)
    return _tipo_procedimento_para_output(repo.salvar(tipo))


@app.put(
    "/catalogo/tipos-procedimento/{tipo_id}",
    response_model=TipoProcedimentoOutput,
    tags=["Catálogos"],
    summary="Atualiza tipo de procedimento",
)
def atualizar_tipo_procedimento_endpoint(
    tipo_id: str,
    payload: TipoProcedimentoInput,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> TipoProcedimentoOutput:
    repo = TipoProcedimentoRepository(app.state.engine)
    tipo = repo.buscar_por_id(uuid.UUID(tipo_id))
    if tipo is None:
        raise HTTPException(status_code=404, detail="Tipo de procedimento não encontrado")
    atualizado = TipoProcedimento(id=tipo.id, chave=payload.chave, nome=payload.nome)
    return _tipo_procedimento_para_output(repo.atualizar(atualizado))


@app.delete(
    "/catalogo/tipos-procedimento/{tipo_id}",
    status_code=200,
    tags=["Catálogos"],
    summary="Remove tipo de procedimento",
    description="Exclui um tipo de procedimento do catálogo; não afeta serviços que já o referenciam.",
)
def remover_tipo_procedimento_endpoint(
    tipo_id: str,
    identidade: IdentidadeExterna = Depends(exigir_gerenciar_catalogos),
) -> dict[str, str]:
    repo = TipoProcedimentoRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(tipo_id)) is None:
        raise HTTPException(status_code=404, detail="Tipo de procedimento não encontrado")
    repo.remover(uuid.UUID(tipo_id))
    return {"status": "deleted"}


def _media_para_output(media: Media, *, reaproveitada: bool = False) -> MediaOutput:
    return MediaOutput(
        id=str(media.id),
        sha256=media.sha256,
        mime_type=media.mime_type,
        tamanho_bytes=media.tamanho_bytes,
        nome_original=media.nome_original,
        url=app.state.armazenamento.obter_url(media.storage_key),
        reaproveitada=reaproveitada,
    )


@app.post(
    "/medias",
    response_model=MediaOutput,
    tags=["Mídia"],
    summary="Envia um arquivo binário",
    description=(
        "Recebe qualquer arquivo binário (foto, vídeo, PDF, documento) e grava seus "
        "metadados. O conteúdo é deduplicado por sha256: reenviar um arquivo idêntico "
        "reaproveita o registro existente em vez de gravar de novo."
    ),
)
async def enviar_media_endpoint(
    arquivo: UploadFile = File(...),
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> MediaOutput:
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=422, detail="arquivo vazio")
    resultado = EnviarMedia(
        MediaRepository(app.state.engine),
        app.state.armazenamento,
    ).executar(
        conteudo=conteudo,
        mime_type=arquivo.content_type or "application/octet-stream",
        nome_original=arquivo.filename,
    )
    return _media_para_output(resultado.media, reaproveitada=resultado.reaproveitada)


@app.get(
    "/medias/{media_id}",
    response_model=MediaOutput,
    tags=["Mídia"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Consulta metadados de uma mídia",
)
def buscar_media_endpoint(media_id: str) -> MediaOutput:
    media = MediaRepository(app.state.engine).buscar_por_id(uuid.UUID(media_id))
    if media is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    return _media_para_output(media)


@app.delete(
    "/medias/{media_id}",
    status_code=200,
    tags=["Mídia"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Remove uma mídia",
    description="Só remove se nenhum anexo ainda referenciar esta mídia.",
)
def remover_media_endpoint(media_id: str) -> dict[str, str]:
    repo = MediaRepository(app.state.engine)
    media = repo.buscar_por_id(uuid.UUID(media_id))
    if media is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    if AnexoMediaRepository(app.state.engine).contar_por_media_id(media.id) > 0:
        raise HTTPException(
            status_code=409,
            detail="mídia ainda referenciada por um ou mais anexos",
        )
    app.state.armazenamento.remover(media.storage_key)
    repo.remover(media.id)
    return {"status": "deleted"}


# Tipos de entidade com autorizacao ja modelada. Novos tipos devem ganhar um ramo aqui
# antes de serem aceitos: por padrao (fail-closed), anexar a um tipo desconhecido e negado.
def _autorizar_anexo(
    identidade: IdentidadeExterna, entidade_tipo: str, entidade_id: uuid.UUID
) -> None:
    if entidade_tipo == "organizacao":
        exigir_acesso_organizacao(identidade, entidade_id, "estabelecimento.configurar_dados")
        return
    if entidade_tipo == "servico":
        servico = ServicoRepository(app.state.engine).buscar_por_id(entidade_id)
        if servico is None:
            raise HTTPException(status_code=422, detail="servico nao encontrado")
        exigir_acesso_oferta(
            identidade,
            organizacao_id=servico.organizacao_id,
            profissional_id=servico.profissional_id,
            permissao="servico.gerenciar",
        )
        return
    if entidade_tipo == "usuario":
        usuario = UsuarioRepository(app.state.engine).buscar_por_provider_subject(
            identidade.provider, identidade.subject
        )
        if usuario is None or usuario.id != entidade_id:
            raise HTTPException(status_code=403, detail="só é possível anexar mídia ao próprio usuário")
        return
    raise HTTPException(
        status_code=422,
        detail=f"entidade_tipo '{entidade_tipo}' ainda não tem autorização modelada",
    )


@app.post(
    "/anexos",
    response_model=AnexoMediaOutput,
    tags=["Mídia"],
    summary="Anexa uma mídia a uma entidade",
    description=(
        "Vincula uma mídia já enviada a uma entidade (organização, serviço, usuário, "
        "etc.) com um papel (ex: 'capa', 'galeria', 'documento'). Tipos de entidade "
        "novos precisam de autorização própria antes de serem aceitos."
    ),
)
def criar_anexo_endpoint(
    payload: AnexoMediaInput,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> AnexoMediaOutput:
    media = MediaRepository(app.state.engine).buscar_por_id(uuid.UUID(payload.media_id))
    if media is None:
        raise HTTPException(status_code=422, detail="mídia não encontrada")
    entidade_id = uuid.UUID(payload.entidade_id)
    _autorizar_anexo(identidade, payload.entidade_tipo, entidade_id)
    anexo = AnexarMedia(AnexoMediaRepository(app.state.engine)).executar(
        media_id=media.id,
        entidade_tipo=payload.entidade_tipo,
        entidade_id=entidade_id,
        papel=payload.papel,
        ordem=payload.ordem,
    )
    return AnexoMediaOutput(
        id=str(anexo.id),
        entidade_tipo=anexo.entidade_tipo,
        entidade_id=str(anexo.entidade_id),
        papel=anexo.papel,
        ordem=anexo.ordem,
        media=_media_para_output(media),
    )


@app.get(
    "/anexos",
    response_model=list[AnexoMediaOutput],
    tags=["Mídia"],
    dependencies=[Depends(limitar_endpoint_publico)],
    summary="Lista anexos de mídia de uma entidade",
    description="[Público, com rate limit] Retorna as mídias anexadas a uma entidade, ordenadas por 'ordem'.",
)
def listar_anexos_endpoint(entidade_tipo: str, entidade_id: str) -> list[AnexoMediaOutput]:
    repo = AnexoMediaRepository(app.state.engine)
    media_repo = MediaRepository(app.state.engine)
    anexos = repo.listar_por_entidade(entidade_tipo, uuid.UUID(entidade_id))
    resultado = []
    for anexo in anexos:
        media = media_repo.buscar_por_id(anexo.media_id)
        if media is None:
            continue
        resultado.append(
            AnexoMediaOutput(
                id=str(anexo.id),
                entidade_tipo=anexo.entidade_tipo,
                entidade_id=str(anexo.entidade_id),
                papel=anexo.papel,
                ordem=anexo.ordem,
                media=_media_para_output(media),
            )
        )
    return resultado


@app.delete(
    "/anexos/{anexo_id}",
    status_code=200,
    tags=["Mídia"],
    summary="Remove um anexo de mídia",
    description="Remove só o vínculo; a mídia em si permanece caso outras entidades a referenciem.",
)
def remover_anexo_endpoint(
    anexo_id: str,
    identidade: IdentidadeExterna = Depends(identidade_autenticada),
) -> dict[str, str]:
    repo = AnexoMediaRepository(app.state.engine)
    anexo = repo.buscar_por_id(uuid.UUID(anexo_id))
    if anexo is None:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    _autorizar_anexo(identidade, anexo.entidade_tipo, anexo.entidade_id)
    repo.remover(anexo.id)
    return {"status": "deleted"}


