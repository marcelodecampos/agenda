from decimal import Decimal

from agenda.application.resgatar_fidelidade import ResgatarFidelidade
from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade, RecompensaFidelidade
from agenda.domain.ids import novo_id


class Repo:
    def __init__(self, itens=()):
        self.itens = list(itens)

    def buscar_por_id(self, programa_id, cliente_id=None):
        if cliente_id is None:
            return next((item for item in self.itens if item.id == programa_id), None)
        return next((item for item in self.itens if item.programa_id == programa_id and item.cliente_id == cliente_id), None)

    def salvar(self, item):
        self.itens = [old for old in self.itens if not hasattr(old, "programa_id") or old.programa_id != item.programa_id or old.cliente_id != item.cliente_id]
        self.itens.append(item)
        return item


class Resgates:
    def salvar(self, **kwargs):
        return novo_id()


def test_resgate_consumo_progresso_e_registra_desconto():
    cliente_id = novo_id()
    programa = ProgramaFidelidade(
        id=novo_id(), nome="Cartao", alvo_servico_id=novo_id(),
        atendimentos_necessarios=2,
        recompensa=RecompensaFidelidade("desconto_fixo", valor=Decimal("15")),
        organizacao_id=novo_id(),
    )
    progresso = ProgressoFidelidade(programa.id, cliente_id, 2)
    progressos = Repo([progresso])

    resultado = ResgatarFidelidade(Repo([programa]), progressos, Resgates()).executar(
        programa_id=programa.id, cliente_id=cliente_id, preco=Decimal("50")
    )

    assert resultado.aplicacao.preco_final == Decimal("35")
    assert resultado.progresso.atendimentos_concluidos == 0