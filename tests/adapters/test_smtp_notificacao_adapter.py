from agenda.adapters.smtp_notificacao_adapter import SMTPNotificacaoAdapter
from agenda.ports import DestinatarioNotificacao, NotificacaoAgendamento
from datetime import datetime


def test_smtp_adapter_envia_email(monkeypatch) -> None:
    chamadas = []

    class SMTPFalso:
        def __init__(self, host, port, timeout):
            chamadas.append((host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, mensagem):
            chamadas.append((mensagem["To"], mensagem["From"], mensagem.get_content()))

    monkeypatch.setattr("agenda.adapters.smtp_notificacao_adapter.smtplib.SMTP", SMTPFalso)
    SMTPNotificacaoAdapter(
        host="localhost", port=1025, remetente="agenda@localhost"
    ).enviar(
        NotificacaoAgendamento(
            agendamento_id="a1",
            destinatario=DestinatarioNotificacao("d1", "email", "cliente@teste.com"),
            mensagem="Lembrete",
            enviar_em=datetime(2026, 9, 14, 7),
        )
    )

    assert chamadas[0] == ("localhost", 1025, 10)
    assert chamadas[1][0] == "cliente@teste.com"