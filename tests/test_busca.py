from __future__ import annotations

import random

import pytest

import cli
import core.busca as busca_module
from core.api import resolver
from core.board import gerar_adjacencias
from core.busca import executar_recuo
from core.metrics import RegistradorMetricas
from core.tipos import (
    Adjacencias,
    AvaliacaoCandidato,
    ConfiguracaoExecucao,
    Posicao,
    VariantePARE,
)
from core.validator import validar_percurso


def _criar_grafo(
    arestas: list[tuple[Posicao, Posicao]],
    vertices: list[Posicao],
) -> Adjacencias:
    vizinhos_por_vertice: dict[Posicao, list[Posicao]] = {v: [] for v in vertices}
    for u, v in arestas:
        if v not in vizinhos_por_vertice[u]:
            vizinhos_por_vertice[u].append(v)
        if u not in vizinhos_por_vertice[v]:
            vizinhos_por_vertice[v].append(u)
    return {v: tuple(vizinhos) for v, vizinhos in vizinhos_por_vertice.items()}


def _avaliacao_simples(
    candidato: Posicao,
    completo_ainda_possivel: bool = True,
) -> AvaliacaoCandidato:
    return AvaliacaoCandidato(
        candidato=candidato,
        fragmentacao=1,
        isolamento=0,
        pressao=0,
        acessibilidade=1,
        completo_ainda_possivel=completo_ainda_possivel,
    )

@pytest.mark.parametrize("n_invalido", [0, -5, True, "5"])
def test_executar_recuo_rejeita_dimensao_invalida(n_invalido: object) -> None:
    adjacencias = gerar_adjacencias(5)
    with pytest.raises(ValueError, match="Dimensão inválida"):
        executar_recuo(
            n=n_invalido,  # type: ignore[arg-type]
            inicio=(0, 0),
            variante="restritiva",
            max_estados=10,
            adjacencias=adjacencias,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
        )


def test_executar_recuo_rejeita_variante_invalida() -> None:
    adjacencias = gerar_adjacencias(5)
    with pytest.raises(ValueError, match="Variante PARE inválida"):
        executar_recuo(
            n=5,
            inicio=(0, 0),
            variante="invalida",  # type: ignore[arg-type]
            max_estados=10,
            adjacencias=adjacencias,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
        )


@pytest.mark.parametrize("max_invalido", [0, -1, True, False, "10", 1.5])
def test_executar_recuo_rejeita_max_estados_invalido(max_invalido: object) -> None:
    adjacencias = gerar_adjacencias(5)
    with pytest.raises(ValueError, match="max_estados inválido"):
        executar_recuo(
            n=5,
            inicio=(0, 0),
            variante="restritiva",
            max_estados=max_invalido,  # type: ignore[arg-type]
            adjacencias=adjacencias,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
        )


def test_executar_recuo_rejeita_podar_inviaveis_nao_booleano() -> None:
    adjacencias = gerar_adjacencias(5)
    with pytest.raises(ValueError, match="podar_inviaveis inválido"):
        executar_recuo(
            n=5,
            inicio=(0, 0),
            variante="restritiva",
            max_estados=10,
            adjacencias=adjacencias,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
            podar_inviaveis=1,  # type: ignore[arg-type]
        )


def test_executar_recuo_rejeita_adjacencias_incompativeis_e_inicio_ausente() -> None:
    adjacencias_3x3 = gerar_adjacencias(3)
    with pytest.raises(ValueError, match="incompatível"):
        executar_recuo(
            n=5,
            inicio=(0, 0),
            variante="restritiva",
            max_estados=10,
            adjacencias=adjacencias_3x3,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
        )

    adjacencias_5x5 = gerar_adjacencias(5)
    with pytest.raises(ValueError, match="Posição inicial inválida"):
        executar_recuo(
            n=5,
            inicio=(5, 5),
            variante="restritiva",
            max_estados=10,
            adjacencias=adjacencias_5x5,
            rng=random.Random(1),
            metricas=RegistradorMetricas(),
        )


def test_executar_recuo_tabuleiro_1x1_completa_no_primeiro_estado() -> None:
    adjacencias = gerar_adjacencias(1)
    metricas = RegistradorMetricas()

    caminho, motivo = executar_recuo(
        n=1,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=1,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas,
    )

    assert caminho == [(0, 0)]
    assert motivo == "completo"
    assert metricas.estados_explorados == 1
    assert metricas.recuos == 0
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.verificacoes_movimentos == 0


def test_executar_recuo_tabuleiro_2x2_sem_movimentos_esgota_ou_atinge_limite() -> None:
    adjacencias = gerar_adjacencias(2)

    metricas_esgotada = RegistradorMetricas()
    caminho, motivo = executar_recuo(
        n=2,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=10,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas_esgotada,
    )
    assert caminho == [(0, 0)]
    assert motivo == "busca_esgotada"
    assert metricas_esgotada.estados_explorados == 1
    assert metricas_esgotada.recuos == 0
    assert metricas_esgotada.avaliacoes_candidatos == 0

    metricas_limite = RegistradorMetricas()
    caminho_lim, motivo_lim = executar_recuo(
        n=2,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=1,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas_limite,
    )
    assert caminho_lim == [(0, 0)]
    assert motivo_lim == "limite_estados"
    assert metricas_limite.estados_explorados == 1
    assert metricas_limite.recuos == 0

def test_recuo_desmarca_casas_e_reutiliza_vertice_no_ramo_alternativo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a, b, c, d = (0, 0), (0, 1), (1, 0), (1, 1)
    adjacencias = _criar_grafo([(a, b), (a, d), (b, c), (d, b)], [a, b, c, d])
    metricas = RegistradorMetricas()

    def ordenar_controlado(
        atual: Posicao,
        visitadas: set[Posicao],
        adjacencias: Adjacencias,
        variante: VariantePARE,
        rng: random.Random,
        metricas: RegistradorMetricas,
    ) -> list[AvaliacaoCandidato]:
        metricas.registrar_verificacao_movimento(len(adjacencias[atual]))
        avaliacoes: list[AvaliacaoCandidato] = []
        for vizinho in adjacencias[atual]:
            if vizinho not in visitadas:
                metricas.registrar_avaliacao_candidato()
                avaliacoes.append(_avaliacao_simples(vizinho))
        return avaliacoes

    monkeypatch.setattr(busca_module, "ordenar_candidatos", ordenar_controlado)

    caminho, motivo = executar_recuo(
        n=2,
        inicio=a,
        variante="restritiva",
        max_estados=20,
        adjacencias=adjacencias,
        rng=random.Random(1),
        metricas=metricas,
    )

    assert caminho == [a, d, b, c]
    assert motivo == "completo"
    assert len(set(caminho)) == 4
    assert metricas.estados_explorados == 7
    assert metricas.recuos == 3


def test_recuo_em_3x3_esgota_ciclo_sem_misturar_ramos() -> None:
    adjacencias = gerar_adjacencias(3)
    metricas = RegistradorMetricas()

    caminho, motivo = executar_recuo(
        n=3,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=200,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas,
    )

    validacao = validar_percurso(3, (0, 0), caminho)
    assert validacao.valido is True
    assert validacao.passeio_completo is False
    assert len(caminho) == 8
    assert (1, 1) not in caminho
    assert motivo == "busca_esgotada"
    assert metricas.estados_explorados == 15
    assert metricas.recuos == 14
    assert metricas.estados_sem_completo_possivel == 14

def test_recuo_preserva_melhor_caminho_mais_longo_ao_atingir_max_estados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a, b, c, d = (0, 0), (0, 1), (1, 0), (1, 1)
    adjacencias = _criar_grafo([(a, b), (a, d), (b, c), (d, b)], [a, b, c, d])
    metricas = RegistradorMetricas()

    def ordenar_controlado(
        atual: Posicao,
        visitadas: set[Posicao],
        adjacencias: Adjacencias,
        variante: VariantePARE,
        rng: random.Random,
        metricas: RegistradorMetricas,
    ) -> list[AvaliacaoCandidato]:
        metricas.registrar_verificacao_movimento(len(adjacencias[atual]))
        return [
            _avaliacao_simples(vizinho)
            for vizinho in adjacencias[atual]
            if vizinho not in visitadas
        ]

    monkeypatch.setattr(busca_module, "ordenar_candidatos", ordenar_controlado)

    caminho, motivo = executar_recuo(
        n=2,
        inicio=a,
        variante="restritiva",
        max_estados=5,
        adjacencias=adjacencias,
        rng=random.Random(1),
        metricas=metricas,
    )

    assert caminho == [a, b, c]
    assert motivo == "limite_estados"
    assert metricas.estados_explorados == 5
    assert metricas.recuos == 3


def test_resolver_recuo_max_estados_um_retorna_apenas_inicio() -> None:
    config = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 0),
        modo="recuo",
        variante="restritiva",
        seed=2026,
        max_estados=1,
    )
    resultado = resolver(config)

    assert resultado.melhor_percurso == [(0, 0)]
    assert resultado.casas_visitadas == 1
    assert resultado.passeio_completo is False
    assert resultado.motivo_parada == "limite_estados"
    assert resultado.estados_explorados == 1
    assert resultado.recuos == 0
    assert resultado.avaliacoes_candidatos == 0


@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_resolver_recuo_5x5_canto_completa_em_ambas_variantes(
    variante: VariantePARE,
) -> None:
    config = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 0),
        modo="recuo",
        variante=variante,
        seed=2026,
        max_estados=2_000,
    )
    resultado = resolver(config)

    validacao = validar_percurso(5, (0, 0), resultado.melhor_percurso)
    assert validacao.valido is True
    assert validacao.passeio_completo is True
    assert resultado.passeio_completo is True
    assert resultado.casas_visitadas == 25
    assert resultado.cobertura_percentual == pytest.approx(100.0)
    assert resultado.motivo_parada == "completo"
    assert resultado.impossibilidade_paridade is False
    assert 25 <= resultado.estados_explorados <= 2_000


def test_resolver_recuo_5x5_paridade_impossivel_respeita_orcamento_e_sinaliza() -> None:
    config = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 1),
        modo="recuo",
        variante="restritiva",
        seed=2026,
        max_estados=300,
    )
    resultado = resolver(config)

    validacao = validar_percurso(5, (0, 1), resultado.melhor_percurso)
    assert validacao.valido is True
    assert validacao.passeio_completo is False
    assert resultado.impossibilidade_paridade is True
    assert resultado.passeio_completo is False
    assert 1 <= resultado.casas_visitadas <= 24
    assert resultado.motivo_parada == "limite_estados"
    assert resultado.estados_explorados == 300
    assert resultado.recuos > 0


@pytest.mark.parametrize("inicio", [(0, 0), (3, 3)])
def test_resolver_recuo_8x8_restritiva_valido_e_respeita_orcamento(
    inicio: Posicao,
) -> None:
    config = ConfiguracaoExecucao(
        n=8,
        inicio=inicio,
        modo="recuo",
        variante="restritiva",
        seed=2026,
        max_estados=1_000,
    )
    resultado = resolver(config)

    validacao = validar_percurso(8, inicio, resultado.melhor_percurso)
    assert validacao.valido is True
    assert resultado.impossibilidade_paridade is False
    assert resultado.estados_explorados <= 1_000
    assert resultado.motivo_parada in {"completo", "limite_estados", "busca_esgotada"}
    if resultado.motivo_parada == "completo":
        assert resultado.passeio_completo is True
        assert resultado.casas_visitadas == 64
    elif resultado.motivo_parada == "limite_estados":
        assert resultado.estados_explorados == 1_000


def test_resolver_recuo_8x8_expansiva_preserva_melhor_e_respeita_orcamento() -> None:
    config = ConfiguracaoExecucao(
        n=8,
        inicio=(0, 0),
        modo="recuo",
        variante="expansiva",
        seed=2026,
        max_estados=200,
    )
    resultado = resolver(config)

    validacao = validar_percurso(8, (0, 0), resultado.melhor_percurso)
    assert validacao.valido is True
    assert resultado.casas_visitadas == len(resultado.melhor_percurso)
    assert resultado.estados_explorados <= 200
    assert resultado.motivo_parada in {"completo", "limite_estados", "busca_esgotada"}

@pytest.mark.parametrize("variante", ["restritiva", "expansiva"])
def test_resolver_recuo_deterministico_com_mesma_semente_e_sem_alterar_random_global(
    variante: VariantePARE,
) -> None:
    estado_global_antes = random.getstate()
    config = ConfiguracaoExecucao(
        n=5,
        inicio=(0, 1),
        modo="recuo",
        variante=variante,
        seed=2026,
        max_estados=150,
    )

    r1 = resolver(config)
    r2 = resolver(config)

    assert random.getstate() == estado_global_antes
    assert r1.seed_utilizada == r2.seed_utilizada == 2026
    assert r1.melhor_percurso == r2.melhor_percurso
    assert r1.motivo_parada == r2.motivo_parada
    assert r1.estados_explorados == r2.estados_explorados
    assert r1.verificacoes_movimentos == r2.verificacoes_movimentos
    assert r1.verificacoes_preparo == r2.verificacoes_preparo
    assert r1.avaliacoes_candidatos == r2.avaliacoes_candidatos
    assert r1.recuos == r2.recuos
    assert r1.estados_sem_completo_possivel == r2.estados_sem_completo_possivel

def test_recuo_coincide_com_guloso_quando_primeiro_ramo_completa() -> None:
    res_guloso = resolver(
        ConfiguracaoExecucao(
            n=5,
            inicio=(0, 0),
            modo="guloso",
            variante="restritiva",
            seed=2026,
        )
    )
    assert res_guloso.passeio_completo is True

    res_recuo = resolver(
        ConfiguracaoExecucao(
            n=5,
            inicio=(0, 0),
            modo="recuo",
            variante="restritiva",
            seed=2026,
            max_estados=500,
        )
    )

    assert res_recuo.melhor_percurso == res_guloso.melhor_percurso
    assert res_recuo.motivo_parada == "completo"
    assert res_recuo.recuos == 0
    assert res_recuo.estados_explorados == res_guloso.estados_explorados
    assert res_recuo.verificacoes_movimentos == res_guloso.verificacoes_movimentos
    assert res_recuo.avaliacoes_candidatos == res_guloso.avaliacoes_candidatos


def test_recuo_podar_inviaveis_opcional_descartando_estados_inviaveis() -> None:
    adjacencias = gerar_adjacencias(3)

    metricas_sem_poda = RegistradorMetricas()
    caminho_sem_poda, motivo_sem_poda = executar_recuo(
        n=3,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=100,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas_sem_poda,
        podar_inviaveis=False,
    )
    assert len(caminho_sem_poda) == 8
    assert motivo_sem_poda == "busca_esgotada"
    assert metricas_sem_poda.estados_sem_completo_possivel > 0

    metricas_com_poda = RegistradorMetricas()
    caminho_com_poda, motivo_com_poda = executar_recuo(
        n=3,
        inicio=(0, 0),
        variante="restritiva",
        max_estados=100,
        adjacencias=adjacencias,
        rng=random.Random(2026),
        metricas=metricas_com_poda,
        podar_inviaveis=True,
    )
    assert caminho_com_poda == [(0, 0)]
    assert motivo_com_poda == "busca_esgotada"
    assert metricas_com_poda.estados_explorados == 1
    assert metricas_com_poda.estados_sem_completo_possivel == 0


def test_integracao_cli_com_resolver_recuo_real(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = cli.main(
        [
            "--n",
            "5",
            "--linha",
            "1",
            "--coluna",
            "1",
            "--modo",
            "recuo",
            "--variante",
            "restritiva",
            "--seed",
            "2026",
            "--max-estados",
            "500",
        ]
    )
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "tabuleiro 5×5" in saida
    assert "início (linha 1, coluna 1)" in saida
    assert "recuo" in saida
    assert "semente utilizada ....... 2026" in saida
