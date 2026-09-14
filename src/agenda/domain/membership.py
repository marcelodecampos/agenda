import uuid
from dataclasses import dataclass, field

from agenda.domain.exceptions import MembershipSemPapelError
from agenda.domain.papel import Papel


@dataclass
class Membership:
    """Vinculo Usuario<->Organizacao (N:N), com um ou mais papeis (papeis secundarios)."""

    id: uuid.UUID
    usuario_id: uuid.UUID
    organizacao_id: uuid.UUID | None
    papeis: list[Papel] = field(default_factory=list)
    ativo: bool = True

    def __post_init__(self) -> None:
        if not self.papeis:
            raise MembershipSemPapelError("membership precisa de ao menos um papel")

    def adicionar_papel(self, papel: Papel) -> None:
        if papel not in self.papeis:
            self.papeis.append(papel)

    def remover_papel(self, papel: Papel) -> None:
        if len(self.papeis) == 1:
            raise MembershipSemPapelError("membership nao pode ficar sem nenhum papel")
        self.papeis.remove(papel)

    def suspender(self) -> None:
        self.ativo = False

    def reativar(self) -> None:
        self.ativo = True

    def tem_permissao(self, permissao: str) -> bool:
        if not self.ativo:
            return False
        return any(papel.concede(permissao) for papel in self.papeis)

    def chaves_papeis(self) -> frozenset[str]:
        return frozenset(papel.chave for papel in self.papeis)
