"""Popula o banco de desenvolvimento com dados de exemplo (salões, profissionais, clientes).

Idempotente: pode ser executado várias vezes sem duplicar registros (usa CPF/nome
como chave de busca). Não cria usuários no Keycloak — os usuários aqui não fazem
login, servem apenas para exercitar regras de negócio (agenda, comissão, fidelidade).

Uso:
    poetry run python scripts/seed_dev_data.py
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from faker import Faker

from agenda.config import settings
from agenda.domain.endereco import Cliente, Endereco
from agenda.domain.ids import novo_id
from agenda.domain.membership import Membership
from agenda.domain.organizacao import Organizacao
from agenda.domain.papel import Papel
from agenda.domain.servico import Servico
from agenda.domain.usuario import Usuario
from agenda.infrastructure.cliente_repository import ClienteRepository
from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.membership_repository import MembershipRepository, PapelRepository
from agenda.infrastructure.organizacao_repository import OrganizacaoRepository
from agenda.infrastructure.servico_repository import ServicoRepository
from agenda.infrastructure.usuario_repository import UsuarioRepository

if settings.environment == "production":
    raise SystemExit("Seed de dados de desenvolvimento não deve rodar em produção.")

engine = criar_engine(settings.database_url)

FAKE = Faker("pt_BR")
Faker.seed(1234)


def _cpf_digits() -> str:
    return re.sub(r"\D", "", FAKE.cpf())


def _endereco() -> Endereco:
    return Endereco(
        logradouro=FAKE.street_name(),
        numero=str(FAKE.building_number()),
        cidade=FAKE.city(),
        estado=FAKE.estado_sigla(),
        cep=re.sub(r"\D", "", FAKE.postcode()),
    )


def obter_papel(chave: str) -> Papel:
    papel = PapelRepository(engine).buscar_por_chave(chave)
    if papel is None:
        raise SystemExit(
            f"Papel '{chave}' nao encontrado. Rode as migracoes (alembic upgrade head) antes do seed."
        )
    return papel


def criar_usuario(nome: str) -> Usuario:
    repo = UsuarioRepository(engine)
    existente = next((u for u in repo.listar() if u.nome == nome), None)
    if existente is not None:
        return existente
    cpf = _cpf_digits()
    usuario = Usuario(
        id=novo_id(),
        provider="seed",
        subject=f"seed-{cpf}",
        nome=nome,
        cpf=cpf,
        email=FAKE.unique.email(),
        telefone=re.sub(r"\D", "", FAKE.phone_number()),
    )
    return repo.salvar(usuario)


def criar_organizacao(nome: str, *, unipessoal: bool) -> Organizacao:
    repo = OrganizacaoRepository(engine)
    existente = next((o for o in repo.listar() if o.nome == nome), None)
    if existente is not None:
        return existente
    organizacao = Organizacao(
        id=novo_id(), nome=nome, unipessoal=unipessoal, endereco=_endereco()
    )
    return repo.salvar(organizacao)


def criar_membership(
    usuario: Usuario, organizacao: Organizacao | None, papeis: list[Papel]
) -> Membership:
    repo = MembershipRepository(engine)
    organizacao_id = organizacao.id if organizacao else None
    existente = next(
        (
            m
            for m in repo.listar()
            if m.usuario_id == usuario.id and m.organizacao_id == organizacao_id
        ),
        None,
    )
    if existente is not None:
        return existente
    membership = Membership(
        id=novo_id(),
        usuario_id=usuario.id,
        organizacao_id=organizacao_id,
        papeis=papeis,
    )
    return repo.salvar(membership)


def criar_servico(
    nome: str,
    *,
    organizacao: Organizacao | None = None,
    profissional: Usuario | None = None,
    categoria: str = "beleza",
    duracao_base_minutos: int = 45,
    preco_base: str = "60.00",
) -> Servico:
    repo = ServicoRepository(engine)
    organizacao_id = organizacao.id if organizacao else None
    existente = next(
        (s for s in repo.listar() if s.nome == nome and s.organizacao_id == organizacao_id),
        None,
    )
    if existente is not None:
        return existente
    servico = Servico(
        id=novo_id(),
        nome=nome,
        categoria=categoria,
        duracao_base_minutos=duracao_base_minutos,
        preco_base=Decimal(preco_base),
        profissional_id=profissional.id if profissional else None,
        organizacao_id=organizacao_id,
    )
    return repo.salvar(servico)


def criar_cliente(nome: str, *, usuario: Usuario | None = None) -> Cliente:
    repo = ClienteRepository(engine)
    existente = next((c for c in repo.listar() if c.nome == nome), None)
    if existente is not None:
        return existente
    cpf = _cpf_digits()
    cliente = Cliente(
        id=novo_id(),
        nome=nome,
        usuario_id=usuario.id if usuario else None,
        telefone=re.sub(r"\D", "", FAKE.phone_number()),
        email=FAKE.unique.email(),
        cpf=cpf,
        endereco=_endereco(),
    )
    return repo.salvar(cliente)


def seed() -> None:
    papel_dono = obter_papel("dono")
    papel_funcionario = obter_papel("funcionario")
    papel_autonomo_associado = obter_papel("autonomo_associado")
    papel_autonomo_puro = obter_papel("autonomo_puro")
    papel_cliente = obter_papel("cliente")

    # Salão com equipe fixa (caso do piloto real: dono + funcionários).
    salao_beleza = criar_organizacao("Salão Beleza Pura", unipessoal=False)
    dono_beleza = criar_usuario("Camila Fernandes")
    criar_membership(dono_beleza, salao_beleza, [papel_dono])
    for nome_func in ("Beatriz Souza", "Rafael Lima"):
        funcionario = criar_usuario(nome_func)
        criar_membership(funcionario, salao_beleza, [papel_funcionario])
    criar_servico(
        "Corte de Cabelo", organizacao=salao_beleza, categoria="cabelo", preco_base="50.00"
    )
    criar_servico(
        "Manicure", organizacao=salao_beleza, categoria="unhas", preco_base="35.00"
    )

    # Salão com equipe mista (funcionário + autônomo associado).
    espaco_estetica = criar_organizacao("Espaço Estética Mista", unipessoal=False)
    dono_estetica = criar_usuario("Patrícia Gomes")
    criar_membership(dono_estetica, espaco_estetica, [papel_dono])
    funcionaria_estetica = criar_usuario("Larissa Costa")
    criar_membership(funcionaria_estetica, espaco_estetica, [papel_funcionario])
    autonoma_associada = criar_usuario("Juliana Ribeiro")
    criar_membership(autonoma_associada, espaco_estetica, [papel_autonomo_associado])
    criar_servico(
        "Depilação", organizacao=espaco_estetica, categoria="depilacao", preco_base="70.00"
    )
    criar_servico(
        "Massagem Relaxante",
        organizacao=espaco_estetica,
        categoria="bem-estar",
        preco_base="120.00",
    )

    # Profissionais autônomos puros (organização unipessoal).
    for nome_autonomo, nome_servico in (
        ("Fernanda Alves", "Design de Sobrancelhas"),
        ("Marcos Pereira", "Consulta Nutricional"),
    ):
        organizacao_unipessoal = criar_organizacao(f"{nome_autonomo} (Autônomo)", unipessoal=True)
        autonomo = criar_usuario(nome_autonomo)
        criar_membership(autonomo, organizacao_unipessoal, [papel_autonomo_puro])
        criar_servico(
            nome_servico,
            organizacao=organizacao_unipessoal,
            profissional=autonomo,
            categoria="saude" if "Nutricional" in nome_servico else "beleza",
            preco_base="90.00",
        )

    # Clientes: alguns com conta de usuário (papel cliente), outros só com ficha.
    for nome_cliente in ("Ana Paula Martins", "Bruno Teixeira"):
        usuario_cliente = criar_usuario(nome_cliente)
        criar_membership(usuario_cliente, None, [papel_cliente])
        criar_cliente(nome_cliente, usuario=usuario_cliente)
    for nome_cliente in ("Carla Nogueira", "Diego Barbosa", "Elaine Rocha"):
        criar_cliente(nome_cliente)

    print("Seed de dados de desenvolvimento concluído.")


if __name__ == "__main__":
    seed()
