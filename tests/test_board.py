from __future__ import annotations

from collections import Counter

import pytest

from core.board import (
    KNIGHT_MOVES,
    cor_casa,
    dentro_do_tabuleiro,
    eh_salto_valido,
    gerar_adjacencias,
    validar_dimensao,
    validar_posicao,
    verificar_impossibilidade_paridade,
)

@pytest.mark.parametrize("dimensao", [5, 8])
def test_validar_dimensao_aceita_obrigatorias(dimensao: int) -> None:
    validar_dimensao(dimensao)


@pytest.mark.parametrize(
    "dimensao_invalida",
    [-8, -1, 0, 1, 3, 4, 6, 7, 9, 10, True, False, 5.0, "5", None],
)
def test_validar_dimensao_rejeita_valores_invalidos(dimensao_invalida: object) -> None:
    with pytest.raises(ValueError):
        validar_dimensao(dimensao_invalida)  # type: ignore[arg-type]


def test_validar_dimensao_respeita_permitidas_customizadas() -> None:
    validar_dimensao(3, permitidas=(3, 4))
    validar_dimensao(4, permitidas=(3, 4))

    with pytest.raises(ValueError):
        validar_dimensao(5, permitidas=(3, 4))

    with pytest.raises(ValueError):
        validar_dimensao(0, permitidas=(0, 3))


@pytest.mark.parametrize(
    ("n", "linha", "coluna", "esperado"),
    [
        (5, 0, 0, True),
        (5, 4, 4, True),
        (5, 2, 3, True),
        (5, -1, 0, False),
        (5, 0, -1, False),
        (5, 5, 0, False),
        (5, 0, 5, False),
        (8, 0, 0, True),
        (8, 7, 7, True),
        (8, 3, 4, True),
        (8, 8, 7, False),
        (8, -1, 7, False),
        (0, 0, 0, False),
        (-5, 0, 0, False),
    ],
)
def test_dentro_do_tabuleiro(n: int, linha: int, coluna: int, esperado: bool) -> None:
    assert dentro_do_tabuleiro(n, linha, coluna) is esperado


def test_dentro_do_tabuleiro_rejeita_tipos_nao_inteiros_estritos() -> None:
    assert dentro_do_tabuleiro(5, True, 0) is False
    assert dentro_do_tabuleiro(5, 0, False) is False
    assert dentro_do_tabuleiro(True, 0, 0) is False
    assert dentro_do_tabuleiro(5, 1.0, 2) is False  # type: ignore[arg-type]
    assert dentro_do_tabuleiro(5, "1", 2) is False  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("n", "posicao"),
    [
        (5, (0, 0)),
        (5, (0, 4)),
        (5, (4, 4)),
        (8, (0, 0)),
        (8, (3, 3)),
        (8, (7, 7)),
        (3, (1, 1)),
    ],
)
def test_validar_posicao_aceita_coordenadas_validas(n: int, posicao: tuple[int, int]) -> None:
    validar_posicao(n, posicao)


@pytest.mark.parametrize(
    ("n", "posicao_invalida"),
    [
        (5, (-1, 0)),
        (5, (0, -1)),
        (5, (5, 0)),
        (5, (0, 5)),
        (8, (8, 0)),
        (8, (3, 8)),
        (0, (0, 0)),
        (-5, (0, 0)),
        (True, (0, 0)),
        (5, [0, 0]),
        (5, (0,)),
        (5, (0, 0, 0)),
        (5, "00"),
        (5, None),
        (5, (True, 0)),
        (5, (0, False)),
        (5, (1.0, 2)),
        (5, ("1", 2)),
    ],
)
def test_validar_posicao_rejeita_entradas_invalidas(
    n: object,
    posicao_invalida: object,
) -> None:
    with pytest.raises(ValueError):
        validar_posicao(n, posicao_invalida)  # type: ignore[arg-type]

def test_knight_moves_contem_oito_deslocamentos_em_l() -> None:
    assert len(KNIGHT_MOVES) == 8
    assert len(set(KNIGHT_MOVES)) == 8
    for dl, dc in KNIGHT_MOVES:
        assert {abs(dl), abs(dc)} == {1, 2}


def test_eh_salto_valido_aceita_os_oito_saltos_e_eh_simetrico() -> None:
    origem = (3, 3)
    for dl, dc in KNIGHT_MOVES:
        destino = (origem[0] + dl, origem[1] + dc)
        assert eh_salto_valido(origem, destino) is True
        assert eh_salto_valido(destino, origem) is True


@pytest.mark.parametrize(
    ("origem", "destino"),
    [
        ((3, 3), (3, 3)),
        ((3, 3), (3, 4)),
        ((3, 3), (4, 4)),
        ((3, 3), (3, 5)),
        ((3, 3), (5, 5)),
        ((3, 3), (0, 0)),
        ((0, 0), (2, 2)),
        ((0, 0), (3, 1)),
        ([0, 0], (2, 1)),
        ((0, 0), (True, 2)),
        ((0, 0), (2.0, 1)),
    ],
)
def test_eh_salto_valido_rejeita_deslocamentos_ou_formatos_invalidos(
    origem: object,
    destino: object,
) -> None:
    assert eh_salto_valido(origem, destino) is False  # type: ignore[arg-type]


def test_gerar_adjacencias_8x8_graus_e_distribuicao() -> None:
    adjacencias = gerar_adjacencias(8)

    assert len(adjacencias) == 64

    # Amostras representativas de cantos, bordas e centro
    assert len(adjacencias[(0, 0)]) == 2
    assert set(adjacencias[(0, 0)]) == {(1, 2), (2, 1)}
    assert len(adjacencias[(0, 7)]) == 2
    assert len(adjacencias[(7, 0)]) == 2
    assert len(adjacencias[(7, 7)]) == 2

    assert len(adjacencias[(0, 1)]) == 3
    assert len(adjacencias[(1, 0)]) == 3

    assert len(adjacencias[(0, 3)]) == 4
    assert len(adjacencias[(1, 1)]) == 4

    assert len(adjacencias[(1, 3)]) == 6
    assert len(adjacencias[(3, 1)]) == 6

    assert len(adjacencias[(3, 3)]) == 8
    assert len(adjacencias[(4, 4)]) == 8

    distribuicao_graus = Counter(len(vizinhos) for vizinhos in adjacencias.values())
    assert set(distribuicao_graus.keys()) == {2, 3, 4, 6, 8}
    assert distribuicao_graus == {2: 4, 3: 8, 4: 20, 6: 16, 8: 16}
    assert sum(len(vizinhos) for vizinhos in adjacencias.values()) == 336


def test_gerar_adjacencias_5x5_graus_e_vizinhos() -> None:
    adjacencias = gerar_adjacencias(5)

    assert len(adjacencias) == 25
    assert set(adjacencias[(0, 0)]) == {(1, 2), (2, 1)}
    assert len(adjacencias[(2, 2)]) == 8

    distribuicao_graus = Counter(len(vizinhos) for vizinhos in adjacencias.values())
    assert distribuicao_graus == {2: 4, 3: 8, 4: 8, 6: 4, 8: 1}
    assert sum(len(vizinhos) for vizinhos in adjacencias.values()) == 96


@pytest.mark.parametrize("n", [3, 5, 8])
def test_gerar_adjacencias_propriedades_grafo_nao_direcionado(n: int) -> None:
    adjacencias = gerar_adjacencias(n)
    assert len(adjacencias) == n * n

    for origem, vizinhos in adjacencias.items():
        assert isinstance(vizinhos, tuple)
        assert len(vizinhos) == len(set(vizinhos))
        for destino in vizinhos:
            assert dentro_do_tabuleiro(n, destino[0], destino[1])
            assert eh_salto_valido(origem, destino)
            assert origem in adjacencias[destino]
            assert cor_casa(origem) != cor_casa(destino)


@pytest.mark.parametrize(("n", "esperado"), [(3, 72), (5, 200), (8, 512)])
def test_gerar_adjacencias_aciona_callback_verificacoes_preparo(n: int, esperado: int) -> None:
    contagem = 0

    def contar() -> None:
        nonlocal contagem
        contagem += 1

    gerar_adjacencias(n, ao_verificar_preparo=contar)
    assert contagem == esperado


@pytest.mark.parametrize("n_invalido", [-5, 0, False, True, 5.0, "5"])
def test_gerar_adjacencias_rejeita_dimensao_invalida(n_invalido: object) -> None:
    with pytest.raises(ValueError):
        gerar_adjacencias(n_invalido)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Grupo 13 — Cor da casa e detector de impossibilidade por paridade
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("posicao", "cor_esperada"),
    [
        ((0, 0), 0),
        ((0, 1), 1),
        ((1, 0), 1),
        ((1, 1), 0),
        ((2, 3), 1),
        ((4, 4), 0),
        ((7, 6), 1),
    ],
)
def test_cor_casa_paridade(posicao: tuple[int, int], cor_esperada: int) -> None:
    assert cor_casa(posicao) == cor_esperada


@pytest.mark.parametrize("posicao_invalida", [[0, 0], (0,), (True, 0), ("0", 1), None])
def test_cor_casa_rejeita_formato_invalido(posicao_invalida: object) -> None:
    with pytest.raises(ValueError):
        cor_casa(posicao_invalida)  # type: ignore[arg-type]


def test_verificar_impossibilidade_paridade_5x5() -> None:
    assert verificar_impossibilidade_paridade(5, (0, 1)) is True
    assert verificar_impossibilidade_paridade(5, (0, 0)) is False

    impossiveis = [
        (linha, coluna)
        for linha in range(5)
        for coluna in range(5)
        if verificar_impossibilidade_paridade(5, (linha, coluna))
    ]
    assert len(impossiveis) == 12
    assert all((linha + coluna) % 2 == 1 for linha, coluna in impossiveis)


def test_verificar_impossibilidade_paridade_8x8_sempre_falso() -> None:
    for linha in range(8):
        for coluna in range(8):
            assert verificar_impossibilidade_paridade(8, (linha, coluna)) is False


def test_verificar_impossibilidade_paridade_rejeita_entrada_invalida() -> None:
    with pytest.raises(ValueError):
        verificar_impossibilidade_paridade(5, (5, 0))
    with pytest.raises(ValueError):
        verificar_impossibilidade_paridade(0, (0, 0))
