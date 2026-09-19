from agenda.application.busca_textual import corresponde_busca, normalizar_texto


def test_normaliza_caixa_acentos_e_cedilha() -> None:
    assert normalizar_texto("CÍlios e Maçã") == "cilios e maca"


def test_encontra_variante_com_s_e_z() -> None:
    assert corresponde_busca("massajem", "Massagem")
    assert corresponde_busca("manizure", "Manicure")


def test_encontra_erro_de_digitação_e_nao_confunde_termo_curto() -> None:
    assert corresponde_busca("manicuri", "Manicure")
    assert not corresponde_busca("ma", "Massagem")


def test_busca_por_nome_ou_categoria() -> None:
    assert corresponde_busca("unhas", "Manicure", "Beleza e unhas")