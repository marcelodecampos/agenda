"""Provisiona os administradores da plataforma no banco da Agenda.

O role platform_admin do Keycloak autentica o usuário, mas as permissões de
negócio permanecem no banco da Agenda. Esta rotina cria o membership global
com o papel administrador_plataforma para os usuários declarados no realm.

Uso:
    poetry run python scripts/seed_platform_admins.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agenda.config import settings
from agenda.domain.ids import novo_id
from agenda.domain.membership import Membership
from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.membership_repository import MembershipRepository, PapelRepository
from agenda.infrastructure.usuario_repository import UsuarioRepository


ROOT = Path(__file__).resolve().parents[1]
REALM_PATH = ROOT / "keycloak" / "config" / "realm.json"

if settings.environment == "production":
    raise SystemExit("Provisionamento de administradores não deve rodar em produção.")


def main() -> None:
    config = json.loads(REALM_PATH.read_text(encoding="utf-8"))
    engine = criar_engine(settings.database_url)
    usuario_repo = UsuarioRepository(engine)
    membership_repo = MembershipRepository(engine)
    papel_repo = PapelRepository(engine)
    papel = papel_repo.buscar_por_chave("administrador_plataforma")
    if papel is None:
        raise SystemExit("Papel administrador_plataforma não encontrado. Rode as migrações primeiro.")

    provisionados = 0
    for declarado in config.get("users", []):
        cpf = declarado.get("attributes", {}).get("cpf", [None])[0]
        usuario = usuario_repo.buscar_por_cpf(cpf) if cpf else None
        if usuario is None:
            print(f"Aguardando primeiro login do CPF {cpf}; usuário interno ainda não existe.")
            continue
        existente = next(
            (
                membership
                for membership in membership_repo.listar_por_usuario_id(usuario.id)
                if membership.organizacao_id is None
            ),
            None,
        )
        if existente is None:
            membership_repo.salvar(
                Membership(
                    id=novo_id(),
                    usuario_id=usuario.id,
                    organizacao_id=None,
                    papeis=[papel],
                )
            )
        elif not existente.tem_permissao("plataforma.gerenciar_catalogos"):
            existente.adicionar_papel(papel)
            membership_repo.atualizar(existente)
        provisionados += 1
        print(f"Administrador provisionado: {usuario.nome} ({cpf}).")

    print(f"Provisionamento concluído: {provisionados} administrador(es).")


if __name__ == "__main__":
    main()
