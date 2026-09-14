class ErroDominio(Exception):
    pass


class UsuarioInvalidoError(ErroDominio):
    pass


class OrganizacaoInvalidaError(ErroDominio):
    pass


class PapelInvalidoError(ErroDominio):
    pass


class MembershipSemPapelError(ErroDominio):
    pass


class ServicoInvalidoError(ErroDominio):
    pass


class PacoteInvalidoError(ErroDominio):
    pass


class DisponibilidadeInvalidaError(ErroDominio):
    pass


class AgendamentoInvalidoError(ErroDominio):
    pass


class TransicaoAgendamentoNaoPermitidaError(ErroDominio):
    pass


class FidelidadeInvalidaError(ErroDominio):
    pass


class ComissaoInvalidaError(ErroDominio):
    pass


class ClienteInvalidoError(ErroDominio):
    pass
