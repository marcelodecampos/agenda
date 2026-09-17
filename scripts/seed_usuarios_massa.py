"""Popula a tabela usuarios da Agenda em massa, gravando direto no banco (sem HTTP).

Não é idempotente por design: destina-se a gerar volume de dados para testes de
carga/paginação, não a manter um conjunto fixo de registros. Rodar de novo soma
mais usuários aos já existentes. Para dados de exemplo "com sentido de negócio"
(salões, profissionais, memberships), use scripts/seed_dev_data.py.

Uso:
    poetry run python scripts/seed_usuarios_massa.py --quantidade 5000
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from faker import Faker

from agenda.config import settings
from agenda.domain.ids import novo_id
from agenda.domain.usuario import Usuario
from agenda.infrastructure.db import criar_engine, criar_session
from agenda.infrastructure.usuario_repository import Base, UsuarioModel

FAKE = Faker("pt_BR")
TAMANHO_LOTE = 500


def gerar_usuario(indice: int, base: int) -> Usuario:
    id_ = novo_id()
    # cpf/telefone vem de um contador com base no timestamp em nanossegundos:
    # zero colisao dentro da execucao e risco desprezivel entre execucoes.
    cpf = str(base + indice)[-11:].zfill(11)
    telefone = str(base + 10**15 + indice)[-11:].zfill(11)
    return Usuario(
        id=id_,
        provider="seed-massa",
        subject=f"seed-massa-{id_}",
        nome=FAKE.name(),
        cpf=cpf,
        # uuidv7 tem timestamp nos primeiros bits; usa o final (aleatorio) do hex
        # para nao colidir entre ids gerados no mesmo milissegundo.
        email=f"{FAKE.user_name()}.{id_.hex[-10:]}@example.test",
        telefone=telefone,
    )


def main(quantidade: int) -> None:
    if settings.environment == "production":
        raise SystemExit("Seed de massa não deve rodar em produção.")

    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)

    criados = 0
    base = time.time_ns()
    with criar_session(engine) as session:
        lote = []
        for indice in range(quantidade):
            lote.append(UsuarioModel.from_domain(gerar_usuario(indice, base)))
            if len(lote) >= TAMANHO_LOTE:
                session.add_all(lote)
                session.commit()
                criados += len(lote)
                lote = []
        if lote:
            session.add_all(lote)
            session.commit()
            criados += len(lote)

    print(f"{criados} usuários criados em massa.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Popula usuarios em massa direto no banco.")
    parser.add_argument("--quantidade", type=int, default=5000)
    args = parser.parse_args()
    main(args.quantidade)
