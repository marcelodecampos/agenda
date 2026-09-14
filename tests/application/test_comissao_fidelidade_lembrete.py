from datetime import datetime, timedelta
from decimal import Decimal

from agenda.application.calcular_comissao_agendamento import CalcularComissaoAgendamento
from agenda.application.criar_lembrete_notificacao import CriarLembreteNotificacao
from agenda.application.registrar_atendimento_fidelidade import RegistrarAtendimentoFidelidade
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.comissao import RegraComissao
from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade, RecompensaFidelidade
from agenda.domain.ids import novo_id
from agenda.domain.lembrete import ConfiguracaoLembrete
from agenda.ports import DestinatarioNotificacao


def _agendamento() -> Agendamento:
    return Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9, 0),
        itens=(
            ItemAgendamento(
                servico_id=novo_id(),
                duracao_minutos=60,
                preco=Decimal("200.00"),
            ),
        ),
        status_atual="concluido",
    )


def test_calcular_comissao_agendamento_aplica_regra() -> None:
    use_case = CalcularComissaoAgendamento()
    membership_id = novo_id()
    agendamento = _agendamento()
    regras = (
        RegraComissao(
            id=novo_id(),
            tipo="percentual",
            valor=Decimal("10"),
            membership_id=membership_id,
        ),
    )

    valor = use_case.executar(agendamento, membership_id, regras, "concluido")

    assert valor == Decimal("20.00")


def test_registrar_atendimento_fidelidade_acumula_progresso() -> None:
    use_case = RegistrarAtendimentoFidelidade()
    programa = ProgramaFidelidade(
        id=novo_id(),
        nome="Cartao manicure",
        alvo_servico_id=novo_id(),
        atendimentos_necessarios=3,
        recompensa=RecompensaFidelidade(tipo="desconto_percentual", valor=Decimal("10")),
        profissional_id=novo_id(),
    )
    progresso = ProgressoFidelidade(programa_id=programa.id, cliente_id=novo_id())

    atualizado = use_case.executar(progresso, programa)

    assert atualizado.atendimentos_concluidos == 1
    assert atualizado.recompensa_disponivel(programa) is False


def test_criar_lembrete_notificacao_usa_configuracao() -> None:
    use_case = CriarLembreteNotificacao()
    agendamento = _agendamento()
    destinatario = DestinatarioNotificacao("dest-1", "email", "cliente@teste.com")
    configuracao = ConfiguracaoLembrete(timedelta(hours=2), "email")

    notificacao = use_case.executar(agendamento, configuracao, destinatario, "Seu horario esta proximo")

    assert notificacao.enviar_em == datetime(2026, 9, 14, 7, 0)
    assert notificacao.destinatario == destinatario
