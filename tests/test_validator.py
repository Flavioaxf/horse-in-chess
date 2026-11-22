from __future__ import annotations

import pytest

from core.board import eh_salto_valido
from core.tipos import ResultadoValidacao
from core.validator import validar_percurso

# 5×5 a partir de (0, 0), terminando em (2, 2)
PASSEIO_5X5_COMPLETO: list[tuple[int, int]] = [
    (0, 0), (1, 2), (0, 4), (2, 3), (4, 4),
    (3, 2), (4, 0), (2, 1), (0, 2), (1, 4),
    (3, 3), (4, 1), (2, 0), (0, 1), (1, 3),
    (3, 4), (4, 2), (3, 0), (1, 1), (0, 3),
    (2, 4), (4, 3), (3, 1), (1, 0), (2, 2),
]

# 8×8 a partir de (0, 0), terminando em (4, 1)
PASSEIO_8X8_COMPLETO: list[tuple[int, int]] = [
    (0, 0), (2, 1), (3, 3), (1, 2),
    (2, 4), (0, 5), (1, 7), (3, 6),
    (5, 5), (4, 7), (6, 6), (7, 4),
    (6, 2), (7, 0), (5, 1), (4, 3),
    (2, 2), (3, 0), (1, 1), (0, 3),
    (1, 5), (0, 7), (2, 6), (3, 4),
    (4, 6), (6, 7), (7, 5), (5, 4),
    (4, 2), (5, 0), (7, 1), (6, 3),
    (4, 4), (6, 5), (7, 7), (5, 6),
    (3, 5), (2, 7), (0, 6), (1, 4),
    (0, 2), (1, 0), (3, 1), (2, 3),
    (0, 4), (1, 6), (3, 7), (2, 5),
    (1, 3), (0, 1), (2, 0), (3, 2),
    (4, 0), (6, 1), (7, 3), (5, 2),
    (6, 4), (7, 6), (5, 7), (4, 5),
    (5, 3), (7, 2), (6, 0), (4, 1),
]

def test_aceita_passeio_5x5_completo_aberto() -> None:
    assert not eh_salto_valido(PASSEIO_5X5_COMPLETO[-1], PASSEIO_5X5_COMPLETO[0])

    resultado = validar_percurso(5, (0, 0), PASSEIO_5X5_COMPLETO)

    assert isinstance(resultado, ResultadoValidacao)
    assert resultado.valido is True
    assert resultado.passeio_completo is True
    assert resultado.erros == ()


def test_aceita_passeio_8x8_completo_aberto() -> None:
    assert not eh_salto_valido(PASSEIO_8X8_COMPLETO[-1], PASSEIO_8X8_COMPLETO[0])

    resultado = validar_percurso(8, (0, 0), PASSEIO_8X8_COMPLETO)

    assert resultado.valido is True
    assert resultado.passeio_completo is True
    assert resultado.erros == ()


def test_aceita_percurso_parcial_valido_sem_marcar_completo() -> None:
    percurso_24 = PASSEIO_5X5_COMPLETO[:-1]
    resultado = validar_percurso(5, (0, 0), percurso_24)

    assert len(percurso_24) == 24
    assert resultado.valido is True
    assert resultado.passeio_completo is False
    assert resultado.erros == ()


def test_aceita_percurso_unitario_na_posicao_inicial() -> None:
    resultado_5x5 = validar_percurso(5, (2, 3), [(2, 3)])
    assert resultado_5x5.valido is True
    assert resultado_5x5.passeio_completo is False
    assert resultado_5x5.erros == ()

    resultado_1x1 = validar_percurso(1, (0, 0), [(0, 0)])
    assert resultado_1x1.valido is True
    assert resultado_1x1.passeio_completo is True
    assert resultado_1x1.erros == ()


def test_aceita_tupla_como_sequencia_e_nao_muta_percurso_de_entrada() -> None:
    percurso_lista = [(0, 0), (1, 2), (2, 4), (4, 3)]
    copia_original = list(percurso_lista)

    res_lista = validar_percurso(5, (0, 0), percurso_lista)
    res_tupla = validar_percurso(5, (0, 0), tuple(percurso_lista))

    assert res_lista == ResultadoValidacao(valido=True, passeio_completo=False, erros=())
    assert res_tupla == res_lista
    assert percurso_lista == copia_original

def test_rejeita_percurso_vazio() -> None:
    resultado = validar_percurso(5, (0, 0), [])

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert len(resultado.erros) == 1
    assert "vazio" in resultado.erros[0].lower()


@pytest.mark.parametrize("percurso_invalido", [None, 123, "00", b"00", {(0, 0)}])
def test_rejeita_percurso_que_nao_e_sequencia_de_posicoes(
    percurso_invalido: object,
) -> None:
    resultado = validar_percurso(5, (0, 0), percurso_invalido)  # type: ignore[arg-type]

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert len(resultado.erros) >= 1


def test_rejeita_inicio_diferente_da_entrada() -> None:
    percurso = [(1, 2), (0, 0), (2, 1)]
    resultado = validar_percurso(5, (0, 0), percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("iniciar" in erro.lower() for erro in resultado.erros)


@pytest.mark.parametrize(
    ("n", "inicio", "percurso"),
    [
        (5, (0, 0), [(0, 0), (-1, 2)]),
        (5, (0, 0), [(0, 0), (2, -1)]),
        (5, (4, 4), [(4, 4), (5, 2)]),
        (5, (4, 4), [(4, 4), (3, 6)]),
        (8, (7, 7), [(7, 7), (8, 5)]),
    ],
)
def test_rejeita_posicao_fora_dos_limites(
    n: int,
    inicio: tuple[int, int],
    percurso: list[tuple[int, int]],
) -> None:
    resultado = validar_percurso(n, inicio, percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("fora dos limites" in erro.lower() for erro in resultado.erros)


def test_rejeita_casa_repetida_com_salto_valido() -> None:
    percurso = [(0, 0), (1, 2), (0, 0)]
    resultado = validar_percurso(5, (0, 0), percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert len(resultado.erros) == 1
    assert "repetida" in resultado.erros[0].lower()


def test_rejeita_casa_repetida_nao_consecutiva() -> None:
    percurso = [(0, 0), (1, 2), (3, 1), (1, 2)]
    resultado = validar_percurso(5, (0, 0), percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("repetida" in erro.lower() for erro in resultado.erros)


@pytest.mark.parametrize(
    "percurso",
    [
        [(0, 0), (0, 1)],
        [(0, 0), (1, 1)],
        [(0, 0), (2, 2)],
        [(0, 0), (3, 1)],
        [(0, 0), (0, 0)],
        [(0, 0), (1, 2), (1, 3)],
    ],
)
def test_rejeita_salto_invalido_entre_casas_consecutivas(
    percurso: list[tuple[int, int]],
) -> None:
    resultado = validar_percurso(5, (0, 0), percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("salto inválido" in erro.lower() for erro in resultado.erros)


@pytest.mark.parametrize("n_invalido", [0, -5, True, False, 5.0, "5", None])
def test_rejeita_dimensao_invalida(n_invalido: object) -> None:
    resultado = validar_percurso(n_invalido, (0, 0), [(0, 0)])  # type: ignore[arg-type]

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("dimensão inválida" in erro.lower() for erro in resultado.erros)


@pytest.mark.parametrize(
    "inicio_invalido",
    [(-1, 0), (5, 0), [0, 0], (0,), (True, 0), (0, 1.0), "00", None],
)
def test_rejeita_posicao_inicial_invalida(inicio_invalido: object) -> None:
    resultado = validar_percurso(5, inicio_invalido, [(0, 0)])  # type: ignore[arg-type]

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert len(resultado.erros) >= 1


def test_rejeita_coordenadas_booleanas_ou_formato_invalido_no_percurso() -> None:
    resultado_bool = validar_percurso(5, (1, 0), [(True, 0)])  # type: ignore[list-item]
    assert resultado_bool.valido is False
    assert resultado_bool.passeio_completo is False
    assert any("posição inválida" in erro.lower() for erro in resultado_bool.erros)

    resultado_misto = validar_percurso(5, (0, 0), [(0, 0), [1, 2], (2, 4)])  # type: ignore[list-item]
    assert resultado_misto.valido is False
    assert resultado_misto.passeio_completo is False
    assert any("índice 1" in erro.lower() for erro in resultado_misto.erros)

def test_passeio_completo_falso_com_v_casas_mas_repeticao() -> None:
    percurso_com_repeticao = PASSEIO_5X5_COMPLETO[:-1] + [(0, 2)]
    assert len(percurso_com_repeticao) == 25

    resultado = validar_percurso(5, (0, 0), percurso_com_repeticao)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("repetida" in erro.lower() for erro in resultado.erros)


def test_passeio_completo_falso_com_v_casas_distintas_mas_salto_invalido() -> None:
    percurso_trocado = list(PASSEIO_5X5_COMPLETO)
    percurso_trocado[5], percurso_trocado[10] = percurso_trocado[10], percurso_trocado[5]
    assert len(percurso_trocado) == 25
    assert len(set(percurso_trocado)) == 25

    resultado = validar_percurso(5, (0, 0), percurso_trocado)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("salto inválido" in erro.lower() for erro in resultado.erros)


def test_passeio_completo_falso_com_v_casas_mas_inicio_divergente() -> None:
    resultado = validar_percurso(5, (1, 2), PASSEIO_5X5_COMPLETO)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("iniciar" in erro.lower() for erro in resultado.erros)


def test_passeio_completo_falso_quando_excede_v_casas() -> None:
    percurso_26 = PASSEIO_5X5_COMPLETO + [(0, 1)]
    resultado = validar_percurso(5, (0, 0), percurso_26)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert any("repetida" in erro.lower() for erro in resultado.erros)


def test_acumula_multiplos_erros_em_um_unico_percurso() -> None:
    percurso = [(1, 1), (5, 5), (1, 1)]
    resultado = validar_percurso(5, (0, 0), percurso)

    assert resultado.valido is False
    assert resultado.passeio_completo is False
    assert isinstance(resultado.erros, tuple)
    assert any("iniciar" in erro.lower() for erro in resultado.erros)
    assert any("fora dos limites" in erro.lower() for erro in resultado.erros)
    assert any("repetida" in erro.lower() for erro in resultado.erros)
    assert any("salto inválido" in erro.lower() for erro in resultado.erros)
