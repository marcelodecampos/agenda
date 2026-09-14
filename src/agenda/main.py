from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Lock
from time import monotonic

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from agenda.application.calcular_comissao_agendamento import CalcularComissaoAgendamento
from agenda.application.criar_agendamento import CriarAgendamento
from agenda.application.criar_disponibilidade import CriarDisponibilidade
from agenda.application.criar_lembrete_notificacao import CriarLembreteNotificacao
from agenda.application.criar_membership import CriarMembership
from agenda.application.criar_notificacao_agendamento import CriarNotificacaoAgendamento
from agenda.application.criar_organizacao import CriarOrganizacao
from agenda.application.criar_pacote import CriarPacote
from agenda.application.criar_programa_fidelidade import CriarProgramaFidelidade
from agenda.application.criar_servico import CriarServico
from agenda.application.registrar_atendimento_fidelidade import RegistrarAtendimentoFidelidade
from agenda.application.registrar_progresso_fidelidade import RegistrarProgressoFidelidade
from agenda.application.registrar_usuario import RegistrarUsuario
from agenda.application.sincronizar_usuario_identidade import SincronizarUsuarioIdentidade
from agenda.adapters.keycloak_identity_adapter import (
    IdentidadeNaoAutenticadaError,
    KeycloakIdentityAdapter,
    ProvedorIdentidadeIndisponivelError,
)
from agenda.config import settings
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.comissao import RegraComissao
from agenda.domain.disponibilidade import Disponibilidade, ExcecaoAgenda, IntervaloHorario, JanelaSemanal
from agenda.domain.endereco import Endereco
from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade, RecompensaFidelidade
from agenda.domain.lembrete import ConfiguracaoLembrete
from agenda.domain.membership import Membership
from agenda.domain.organizacao import Organizacao
from agenda.domain.pacote import Pacote
from agenda.domain.papel import Papel
from agenda.domain.servico import ModalidadeAtendimento, Servico
from agenda.domain.usuario import Usuario
from agenda.infrastructure.agendamento_repository import AgendamentoRepository
from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.disponibilidade_repository import DisponibilidadeRepository
from agenda.infrastructure.fidelidade_repository import ProgramaFidelidadeRepository, ProgressoFidelidadeRepository
from agenda.infrastructure.membership_repository import MembershipRepository
from agenda.infrastructure.notificacao_repository import NotificacaoAgendamentoRepository
from agenda.infrastructure.organizacao_repository import OrganizacaoRepository
from agenda.infrastructure.pacote_repository import PacoteRepository
from agenda.infrastructure.servico_repository import ServicoRepository
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
    ],
)
if not hasattr(app.state, "engine"):
    app.state.engine = criar_engine(settings.database_url)
if not hasattr(app.state, "identity_adapter"):
    app.state.identity_adapter = KeycloakIdentityAdapter(
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
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
    duracao_base_minutos: int = Field(..., gt=0)
    preco_base: Decimal = Field(..., ge=0)
    profissional_id: str | None = None
    organizacao_id: str | None = None
    modalidades: list[ModalidadeInput] = Field(default_factory=list)


class ServicoOutput(BaseModel):
    id: str
    nome: str
    categoria: str
    duracao_base_minutos: int
    preco_base: Decimal
    profissional_id: str | None = None
    organizacao_id: str | None = None
    modalidades: list[ModalidadeOutput] = Field(default_factory=list)


class PapelInput(BaseModel):
    chave: str = Field(..., min_length=1)
    nome: str = Field(..., min_length=1)
    permissoes: list[str] = Field(default_factory=list)


class PapelOutput(BaseModel):
    id: str
    chave: str
    nome: str
    permissoes: list[str] = Field(default_factory=list)


class MembershipInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "usuario_id": "0190a7b0-7f4d-7000-8000-000000000001",
                "organizacao_id": "0190a7b0-7f4d-7000-8000-000000000002",
                "papeis": [
                    {
                        "chave": "profissional",
                        "nome": "Profissional",
                        "permissoes": ["agendamento:gerenciar"],
                    }
                ],
            }
        }
    )
    usuario_id: str
    organizacao_id: str | None = None
    papeis: list[PapelInput] = Field(default_factory=list)


class MembershipOutput(BaseModel):
    id: str
    usuario_id: str
    organizacao_id: str | None = None
    ativo: bool
    papeis: list[PapelOutput] = Field(default_factory=list)


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


class DisponibilidadeOutput(BaseModel):
    id: str
    semanal: list[dict[str, object]] = Field(default_factory=list)
    excecoes: list[dict[str, object]] = Field(default_factory=list)
    profissional_id: str | None = None
    organizacao_id: str | None = None


class ItemAgendamentoInput(BaseModel):
    servico_id: str | None = None
    pacote_id: str | None = None
    duracao_minutos: int = Field(..., gt=0)
    preco: Decimal = Field(..., ge=0)


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


class AgendamentoOutput(BaseModel):
    id: str
    cliente_id: str
    profissional_id: str
    inicio: datetime
    itens: list[dict[str, object]] = Field(default_factory=list)
    status_atual: str
    organizacao_id: str | None = None


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


class LembreteOutput(BaseModel):
    agendamento_id: str
    destinatario: DestinatarioNotificacaoInput
    mensagem: str
    enviar_em: datetime


class RegraComissaoInput(BaseModel):
    id: str
    tipo: str
    valor: Decimal
    membership_id: str | None = None
    servico_id: str | None = None


class ComissaoInput(BaseModel):
    agendamento: AgendamentoInput
    membership_id: str
    regras: list[RegraComissaoInput] = Field(default_factory=list)
    status_concluido: str = Field(..., min_length=1)


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


exigir_gerenciar_servico = exigir_permissao("servico.gerenciar")
exigir_configurar_estabelecimento = exigir_permissao(
    "estabelecimento.configurar_dados"
)
exigir_gerenciar_equipe = exigir_permissao("estabelecimento.gerenciar_equipe")
exigir_gerenciar_pacote = exigir_permissao("pacote.gerenciar")
exigir_configurar_agenda = exigir_permissao("agenda.configurar")
exigir_solicitar_agendamento = exigir_permissao("agendamento.solicitar")
exigir_configurar_fidelidade = exigir_permissao("fidelidade.configurar_programa")


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


def servico_para_output(servico: Servico) -> ServicoOutput:
    return ServicoOutput(
        id=str(servico.id),
        nome=servico.nome,
        categoria=servico.categoria,
        duracao_base_minutos=servico.duracao_base_minutos,
        preco_base=servico.preco_base,
        profissional_id=str(servico.profissional_id) if servico.profissional_id else None,
        organizacao_id=str(servico.organizacao_id) if servico.organizacao_id else None,
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
def atualizar_organizacao_endpoint(organizacao_id: str, payload: OrganizacaoInput) -> OrganizacaoOutput:
    repo = OrganizacaoRepository(app.state.engine)
    organizacao = repo.buscar_por_id(uuid.UUID(organizacao_id))
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
def remover_organizacao_endpoint(organizacao_id: str) -> dict[str, str]:
    repo = OrganizacaoRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(organizacao_id)) is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    repo.remover(uuid.UUID(organizacao_id))
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
    _: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> ServicoOutput:
    repo = ServicoRepository(app.state.engine)
    servico = repo.buscar_por_id(uuid.UUID(servico_id))
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    atualizado = Servico(
        id=servico.id,
        nome=payload.nome,
        categoria=payload.categoria,
        duracao_base_minutos=payload.duracao_base_minutos,
        preco_base=payload.preco_base,
        profissional_id=uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
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
    _: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> dict[str, str]:
    repo = ServicoRepository(app.state.engine)
    if repo.buscar_por_id(uuid.UUID(servico_id)) is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    repo.remover(uuid.UUID(servico_id))
    return {"status": "deleted"}


@app.get(
    "/memberships",
    response_model=list[MembershipOutput],
    tags=["Memberships"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Lista memberships",
    description="Recupera os vínculos entre usuários, organizações e papéis do sistema.",
)
def listar_memberships_endpoint() -> list[MembershipOutput]:
    repo = MembershipRepository(app.state.engine)
    return [membership_para_output(item) for item in repo.listar()]


@app.get(
    "/memberships/{membership_id}",
    response_model=MembershipOutput,
    tags=["Memberships"],
    dependencies=[Depends(identidade_autenticada)],
    summary="Busca membership por ID",
    description="Consulta o vínculo específico de usuário e organização em um perfil funcional.",
)
def buscar_membership_endpoint(membership_id: str) -> MembershipOutput:
    repo = MembershipRepository(app.state.engine)
    membership = repo.buscar_por_id(uuid.UUID(membership_id))
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership não encontrado")
    return membership_para_output(membership)


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
    "/servicos",
    response_model=ServicoOutput,
    tags=["Serviços"],
    summary="Cria serviço",
    description="Cadastra um novo serviço com duração, preço e modalidades de atendimento.",
)
def criar_servico_endpoint(
    payload: ServicoInput,
    _: IdentidadeExterna = Depends(exigir_gerenciar_servico),
) -> ServicoOutput:
    repo = ServicoRepository(app.state.engine)
    use_case = CriarServico(repo)
    servico = Servico(
        id=uuid.uuid7(),
        nome=payload.nome,
        categoria=payload.categoria,
        duracao_base_minutos=payload.duracao_base_minutos,
        preco_base=payload.preco_base,
        profissional_id=uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
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
    return ServicoOutput(
        id=str(salvo.id),
        nome=salvo.nome,
        categoria=salvo.categoria,
        duracao_base_minutos=salvo.duracao_base_minutos,
        preco_base=salvo.preco_base,
        profissional_id=str(salvo.profissional_id) if salvo.profissional_id else None,
        organizacao_id=str(salvo.organizacao_id) if salvo.organizacao_id else None,
        modalidades=[
            ModalidadeOutput(
                chave=item.chave,
                nome=item.nome,
                ajuste_preco_fixo=item.ajuste_preco_fixo,
                ajuste_preco_percentual=item.ajuste_preco_percentual,
                ajuste_duracao_minutos=item.ajuste_duracao_minutos,
            )
            for item in salvo.modalidades
        ],
    )


@app.post(
    "/memberships",
    response_model=MembershipOutput,
    tags=["Memberships"],
    dependencies=[Depends(exigir_gerenciar_equipe)],
    summary="Cria membership",
    description="Vincula usuário, organização e papéis para compor o perfil funcional da operação.",
)
def criar_membership_endpoint(payload: MembershipInput) -> MembershipOutput:
    repo = MembershipRepository(app.state.engine)
    use_case = CriarMembership(repo)
    papeis = tuple(
        Papel(
            id=uuid.uuid7(),
            chave=item.chave,
            nome=item.nome,
            permissoes=frozenset(item.permissoes),
        )
        for item in payload.papeis
    )
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
    dependencies=[Depends(exigir_gerenciar_pacote)],
    summary="Cria pacote",
    description="Agrupa serviços em um pacote com preço e duração totais.",
)
def criar_pacote_endpoint(payload: PacoteInput) -> PacoteOutput:
    repo = PacoteRepository(app.state.engine)
    use_case = CriarPacote(repo)
    pacote = Pacote(
        id=uuid.uuid7(),
        nome=payload.nome,
        servico_ids=tuple(uuid.UUID(str(item)) for item in payload.servico_ids),
        duracao_total_minutos=payload.duracao_total_minutos,
        preco=payload.preco,
        profissional_id=uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
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


@app.post(
    "/disponibilidades",
    response_model=DisponibilidadeOutput,
    tags=["Disponibilidade"],
    dependencies=[Depends(exigir_configurar_agenda)],
    summary="Cria disponibilidade",
    description="Define janelas de agenda recorrentes e exceções para profissionais ou organizações.",
)
def criar_disponibilidade_endpoint(payload: DisponibilidadeInput) -> DisponibilidadeOutput:
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
        profissional_id=uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
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
    salvo = use_case.executar(agendamento)
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
    "/programas-fidelidade",
    response_model=ProgramaFidelidadeOutput,
    tags=["Fidelidade"],
    dependencies=[Depends(exigir_configurar_fidelidade)],
    summary="Cria programa de fidelidade",
    description="Define um programa de fidelidade com regra de atendimento e recompensa.",
)
def criar_programa_fidelidade_endpoint(payload: ProgramaFidelidadeInput) -> ProgramaFidelidadeOutput:
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
        profissional_id=uuid.UUID(str(payload.profissional_id)) if payload.profissional_id else None,
        organizacao_id=uuid.UUID(str(payload.organizacao_id)) if payload.organizacao_id else None,
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