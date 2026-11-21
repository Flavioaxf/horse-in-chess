"""Testes do módulo ``core/render.py`` e ``cli.py`` (Dono: P3 — Flávio).

Grupo 12: renderização numerada corresponde exatamente ao melhor percurso,
eixos 1-based, casas não visitadas indicadas por traço e suporte a ``passo_maximo``.

Os percursos abaixo são **escritos à mão** apenas para teste. Nunca são usados
por ``app.py``, ``cli.py`` ou no relatório. O ``resolver`` é substituído por um
dublê nos testes da CLI, pois o modo guloso (F6) ainda não está integrado.
"""

from __future__ import annotations

import pytest

import cli
from core.board import eh_salto_valido
from core.render import (
    construir_matriz_visitas,
    descrever_motivo_parada,
    formatar_resumo_execucao,
    formatar_tabuleiro_texto,
)
from core.tipos import MOTIVOS_PARADA_VALIDOS, ConfiguracaoExecucao, ResultadoExecucao

# Passeio aberto 5×5 a partir de (0, 0), escrito à mão (0-based).
PASSEIO_5X5_MANUAL = [
    (0, 0), (1, 2), (0, 4), (2, 3), (4, 4), (3, 2), (4, 0), (2, 1), (0, 2),
    (1, 4), (3, 3), (4, 1), (2, 0), (0, 1), (1, 3), (3, 4), (4, 2), (3, 0),
    (1, 1), (0, 3), (2, 4), (4, 3), (3, 1), (1, 0), (2, 2),
]
PERCURSO_PARCIAL_MANUAL = [(0, 0), (1, 2), (2, 4), (4, 3)]


def _resultado_manual(
    percurso: list[tuple[int, int]],
    *,
    n: int = 5,
    modo: str = "guloso",
    motivo: str = "sem_movimentos",
    paridade: bool = False,
    max_estados: int | None = None,
) -> ResultadoExecucao:
    total = n * n
    cfg = ConfiguracaoExecucao(
        n=n, inicio=percurso[0], modo=modo, seed=2026, max_estados=max_estados
    )
    return ResultadoExecucao(
        config=cfg,
        seed_utilizada=2026,
        melhor_percurso=percurso,
        casas_visitadas=len(percurso),
        total_casas=total,
        cobertura_percentual=100 * len(percurso) / total,
        passeio_completo=len(percurso) == total,
        motivo_parada=motivo,
        tempo_segundos=0.0,
        estados_explorados=len(percurso),
        verificacoes_movimentos=11,
        verificacoes_preparo=200,
        avaliacoes_candidatos=7,
        recuos=0,
        impossibilidade_paridade=paridade,
        versao_codigo="teste",
    )


def test_percurso_manual_e_um_passeio_valido() -> None:
    assert len(set(PASSEIO_5X5_MANUAL)) == 25
    assert all(eh_salto_valido(a, b) for a, b in zip(PASSEIO_5X5_MANUAL, PASSEIO_5X5_MANUAL[1:]))


def test_matriz_numera_cada_casa_pela_ordem_de_visita() -> None:
    matriz = construir_matriz_visitas(5, PASSEIO_5X5_MANUAL)
    for ordem, (linha, coluna) in enumerate(PASSEIO_5X5_MANUAL, start=1):
        assert matriz[linha][coluna] == ordem
    assert sorted(v for fileira in matriz for v in fileira) == list(range(1, 26))


def test_matriz_parcial_marca_nao_visitadas_com_none() -> None:
    matriz = construir_matriz_visitas(5, PERCURSO_PARCIAL_MANUAL)
    numeros = [v for fileira in matriz for v in fileira if v is not None]
    assert sorted(numeros) == [1, 2, 3, 4]
    assert sum(v is None for fileira in matriz for v in fileira) == 21
    assert matriz[4][3] == 4


@pytest.mark.parametrize("passo, esperado", [(0, 0), (2, 2), (4, 4), (99, 4)])
def test_passo_maximo_limita_casas_exibidas(passo: int, esperado: int) -> None:
    matriz = construir_matriz_visitas(5, PERCURSO_PARCIAL_MANUAL, passo_maximo=passo)
    numeros = sorted(v for fileira in matriz for v in fileira if v is not None)
    assert numeros == list(range(1, esperado + 1))


def test_percurso_vazio_gera_matriz_vazia() -> None:
    assert construir_matriz_visitas(5, []) == [[None] * 5 for _ in range(5)]


@pytest.mark.parametrize(
    "n, percurso, passo",
    [
        (0, [], None),
        (5, [(0, 0), (5, 0)], None),
        (5, [(0, 0), (-1, 2)], None),
        (5, [(0, 0), (1, 2), (0, 0)], None),
        (5, [(0, 0)], -1),
    ],
)
def test_entradas_invalidas_sao_rejeitadas(n, percurso, passo) -> None:
    with pytest.raises(ValueError):
        construir_matriz_visitas(n, percurso, passo_maximo=passo)


def test_texto_tem_eixos_1_based_e_traco_nas_nao_visitadas() -> None:
    texto = formatar_tabuleiro_texto(5, PERCURSO_PARCIAL_MANUAL)
    linhas = texto.splitlines()
    assert len(linhas) == 2 + 5
    assert linhas[0].split("|")[1].split() == ["1", "2", "3", "4", "5"]
    rotulos = [linha.split("|")[0].strip() for linha in linhas[2:]]
    assert rotulos == ["1", "2", "3", "4", "5"]
    assert linhas[2].split("|")[1].split() == ["1", "-", "-", "-", "-"]
    assert linhas[3].split("|")[1].split() == ["-", "-", "2", "-", "-"]
    assert linhas[6].split("|")[1].split() == ["-", "-", "-", "4", "-"]


def test_texto_8x8_tem_colunas_alinhadas() -> None:
    texto = formatar_tabuleiro_texto(8, [(0, 0), (2, 1)])
    larguras = {len(linha) for linha in texto.splitlines()}
    assert len(larguras) == 1


def test_texto_completo_bate_com_matriz() -> None:
    texto = formatar_tabuleiro_texto(5, PASSEIO_5X5_MANUAL)
    matriz = construir_matriz_visitas(5, PASSEIO_5X5_MANUAL)
    for fileira_texto, fileira in zip(texto.splitlines()[2:], matriz):
        assert [int(x) for x in fileira_texto.split("|")[1].split()] == fileira


def test_todos_os_motivos_tem_descricao() -> None:
    for motivo in MOTIVOS_PARADA_VALIDOS:
        assert descrever_motivo_parada(motivo)
    with pytest.raises(ValueError):
        descrever_motivo_parada("inexistente")


def test_resumo_exibe_metricas_do_resultado() -> None:
    resultado = _resultado_manual(PERCURSO_PARCIAL_MANUAL)
    texto = formatar_resumo_execucao(resultado)
    assert "4 de 25" in texto
    assert "16.00%" in texto
    assert "passeio completo ........ não" in texto
    assert "sem_movimentos" in texto
    assert "esgotamento da estratégia" in texto
    assert "semente utilizada ....... 2026" in texto
    assert "não se aplica" in texto
    assert "Aviso de paridade" not in texto


def test_resumo_mostra_orcamento_e_aviso_de_paridade() -> None:
    resultado = _resultado_manual(
        [(0, 1), (2, 0)], modo="recuo", motivo="limite_estados", paridade=True, max_estados=500
    )
    texto = formatar_resumo_execucao(resultado)
    assert "orçamento (max_estados) . 500" in texto
    assert "limite de execução" in texto
    assert "Aviso de paridade" in texto
    assert "24 casas" in texto


# --------------------------------------------------------------------------- CLI


def test_parser_converte_para_configuracao_0_based() -> None:
    parser = cli.construir_parser()
    args = parser.parse_args(
        ["--n", "8", "--linha", "4", "--coluna", "5", "--modo", "recuo",
         "--variante", "expansiva", "--seed", "7", "--max-estados", "500"]
    )
    cfg = cli.montar_configuracao(args, parser)
    assert cfg == ConfiguracaoExecucao(
        n=8, inicio=(3, 4), modo="recuo", variante="expansiva", seed=7, max_estados=500
    )


def test_recuo_sem_orcamento_usa_padrao_e_guloso_ignora_orcamento() -> None:
    parser = cli.construir_parser()
    recuo = cli.montar_configuracao(
        parser.parse_args(["--n", "5", "--linha", "1", "--coluna", "1", "--modo", "recuo"]), parser
    )
    assert recuo.max_estados == cli.MAX_ESTADOS_PADRAO
    guloso = cli.montar_configuracao(
        parser.parse_args(["--n", "5", "--linha", "1", "--coluna", "1", "--max-estados", "9"]),
        parser,
    )
    assert guloso.modo == "guloso" and guloso.max_estados is None


@pytest.mark.parametrize(
    "argv",
    [
        ["--n", "6", "--linha", "1", "--coluna", "1"],
        ["--n", "5", "--linha", "0", "--coluna", "1"],
        ["--n", "5", "--linha", "1", "--coluna", "6"],
        ["--n", "5", "--linha", "1", "--coluna", "1", "--modo", "outro"],
        ["--n", "5", "--linha", "1", "--coluna", "1", "--max-estados", "0"],
    ],
)
def test_cli_rejeita_entradas_invalidas(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(argv)
    assert excinfo.value.code == 2


def test_cli_imprime_tabuleiro_e_resumo(monkeypatch, capsys) -> None:
    recebido: list[ConfiguracaoExecucao] = []

    def resolver_duble(config: ConfiguracaoExecucao) -> ResultadoExecucao:
        recebido.append(config)
        return _resultado_manual(PERCURSO_PARCIAL_MANUAL)

    monkeypatch.setattr(cli, "resolver", resolver_duble)
    codigo = cli.main(["--n", "5", "--linha", "1", "--coluna", "1", "--seed", "2026"])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert recebido[0].inicio == (0, 0)
    assert "início (linha 1, coluna 1)" in saida
    assert formatar_tabuleiro_texto(5, PERCURSO_PARCIAL_MANUAL) in saida
    assert "4 de 25" in saida


def test_cli_informa_resolvedor_indisponivel(monkeypatch, capsys) -> None:
    def resolver_pendente(config: ConfiguracaoExecucao) -> ResultadoExecucao:
        raise NotImplementedError("F6 pendente")

    monkeypatch.setattr(cli, "resolver", resolver_pendente)
    assert cli.main(["--n", "5", "--linha", "1", "--coluna", "1"]) == 2
    assert "ainda não está disponível" in capsys.readouterr().err
