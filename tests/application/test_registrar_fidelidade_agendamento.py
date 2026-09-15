from datetime import datetime
from decimal import Decimal

from agenda.application.registrar_fidelidade_agendamento import RegistrarFidelidadeAgendamento
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.fidelidade import ProgramaFidelidade, RecompensaFidelidade
from agenda.domain.ids import novo_id


class Repositorio:
    def __init__(self, itens=None):
        self.itens = list(itens or [])

    def listar(self):
        return self.itens

    def buscar_por_id(self, programa_id, cliente_id):
        return next(
            (item for item in self.itens if item.programa_id == programa_id and item.cliente_id == cliente_id),
            None,
        )

    def salvar(self, item):
        self.itens = [
            atual for atual in self.itens
            if not (atual.programa_id == item.programa_id and atual.cliente_id == item.cliente_id)
        ]
        self.itens.append(item)
        return item


def test_registra_progresso_para_programas_do_servico_concluido() -> None:
    cliente_id = novo_id()
    profissional_id = novo_id()
    servico_id = novo_id()
    programa = ProgramaFidelidade(
        id=novo_id(),
        nome="Cartao",
        alvo_servico_id=servico_id,
        atendimentos_necessarios=3,
        recompensa=RecompensaFidelidade("desconto", valor=Decimal("10")),
        profissional_id=profissional_id,
    )
    agendamento = Agendamento(
        id=novo_id(),
        cliente_id=cliente_id,
        profissional_id=profissional_id,
        inicio=datetime(2026, 9, 14, 10),
        itens=(ItemAgendamento(servico_id=servico_id, duracao_minutos=30, preco=Decimal("40")),),
        status_atual="concluido",
    )
    progressos = Repositorio()

    atualizados = RegistrarFidelidadeAgendamento(
        Repositorio([programa]), progressos
    ).executar(agendamento)

    assert len(atualizados) == 1
    assert atualizados[0].atendimentos_concluidos == 1
    assert progressos.buscar_por_id(programa.id, cliente_id) == atualizados[0]