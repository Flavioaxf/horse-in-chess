from __future__ import annotations

import pytest

import core.metrics as metrics_module
from core.board import gerar_adjacencias
from core.metrics import RegistradorMetricas


def test_estado_inicial_zerado() -> None:
    metricas = RegistradorMetricas()

    assert metricas.estados_explorados == 0
    assert metricas.verificacoes_movimentos == 0
    assert metricas.verificacoes_preparo == 0
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.recuos == 0
    assert metricas.estados_sem_completo_possivel == 0
    assert metricas.tempo_segundos == 0.0


@pytest.mark.parametrize(
    "propriedade",
    [
        "estados_explorados",
        "verificacoes_movimentos",
        "verificacoes_preparo",
        "avaliacoes_candidatos",
        "recuos",
        "estados_sem_completo_possivel",
        "tempo_segundos",
    ],
)
def test_propriedades_sao_somente_leitura(propriedade: str) -> None:
    metricas = RegistradorMetricas()

    with pytest.raises(AttributeError):
        setattr(metricas, propriedade, 1)


def test_incremento_isolado_de_cada_contador() -> None:
    metricas = RegistradorMetricas()

    metricas.registrar_estado()
    assert metricas.estados_explorados == 1
    assert metricas.verificacoes_movimentos == 0
    assert metricas.verificacoes_preparo == 0
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.recuos == 0
    assert metricas.estados_sem_completo_possivel == 0

    metricas.registrar_verificacao_movimento()
    metricas.registrar_verificacao_movimento(4)
    metricas.registrar_verificacao_movimento(0)
    assert metricas.verificacoes_movimentos == 5
    assert metricas.verificacoes_preparo == 0

    metricas.registrar_verificacao_preparo()
    metricas.registrar_verificacao_preparo(7)
    metricas.registrar_verificacao_preparo(0)
    assert metricas.verificacoes_preparo == 8
    assert metricas.verificacoes_movimentos == 5

    metricas.registrar_avaliacao_candidato()
    metricas.registrar_avaliacao_candidato()
    assert metricas.avaliacoes_candidatos == 2

    metricas.registrar_recuo()
    metricas.registrar_recuo()
    metricas.registrar_recuo()
    assert metricas.recuos == 3

    metricas.registrar_estado_sem_completo_possivel()
    assert metricas.estados_sem_completo_possivel == 1
    assert metricas.estados_explorados == 1


@pytest.mark.parametrize("quantidade_invalida", [-1, -10, True, False, 1.0, 2.5, "1", None])
def test_registrar_verificacoes_rejeita_quantidades_invalidas(
    quantidade_invalida: object,
) -> None:
    metricas = RegistradorMetricas()

    with pytest.raises(ValueError):
        metricas.registrar_verificacao_movimento(quantidade_invalida)  # type: ignore[arg-type]
    assert metricas.verificacoes_movimentos == 0

    with pytest.raises(ValueError):
        metricas.registrar_verificacao_preparo(quantidade_invalida)  # type: ignore[arg-type]
    assert metricas.verificacoes_preparo == 0


def test_cronometro_usa_perf_counter_deterministico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instantes = iter([100.0, 102.25, 200.0, 200.75])
    monkeypatch.setattr(metrics_module.time, "perf_counter", lambda: next(instantes))

    metricas = RegistradorMetricas()

    metricas.iniciar_cronometro()
    decorrido_1 = metricas.parar_cronometro()
    assert decorrido_1 == pytest.approx(2.25)
    assert metricas.tempo_segundos == pytest.approx(2.25)

    metricas.iniciar_cronometro()
    decorrido_2 = metricas.parar_cronometro()
    assert decorrido_2 == pytest.approx(3.0)
    assert metricas.tempo_segundos == pytest.approx(3.0)


def test_cronometro_real_mede_tempo_nao_negativo() -> None:
    metricas = RegistradorMetricas()

    metricas.iniciar_cronometro()
    _ = sum(range(10_000))
    decorrido = metricas.parar_cronometro()

    assert isinstance(decorrido, float)
    assert decorrido >= 0.0
    assert metricas.tempo_segundos == decorrido


def test_cronometro_rejeita_transicoes_invalidas() -> None:
    metricas = RegistradorMetricas()

    with pytest.raises(RuntimeError):
        metricas.parar_cronometro()

    metricas.iniciar_cronometro()
    with pytest.raises(RuntimeError):
        metricas.iniciar_cronometro()

    metricas.parar_cronometro()
    with pytest.raises(RuntimeError):
        metricas.parar_cronometro()


def test_cronometro_protege_contra_delta_negativo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instantes = iter([50.0, 49.5])
    monkeypatch.setattr(metrics_module.time, "perf_counter", lambda: next(instantes))

    metricas = RegistradorMetricas()
    metricas.iniciar_cronometro()
    decorrido = metricas.parar_cronometro()

    assert decorrido == 0.0
    assert metricas.tempo_segundos == 0.0


def test_resetar_zera_contadores_e_estado_do_cronometro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instantes = iter([10.0, 11.5, 20.0, 30.0, 30.5])
    monkeypatch.setattr(metrics_module.time, "perf_counter", lambda: next(instantes))

    metricas = RegistradorMetricas()
    metricas.registrar_estado()
    metricas.registrar_verificacao_movimento(3)
    metricas.registrar_verificacao_preparo(8)
    metricas.registrar_avaliacao_candidato()
    metricas.registrar_recuo()
    metricas.registrar_estado_sem_completo_possivel()
    metricas.iniciar_cronometro()
    metricas.parar_cronometro()

    metricas.iniciar_cronometro()
    metricas.resetar()

    assert metricas.estados_explorados == 0
    assert metricas.verificacoes_movimentos == 0
    assert metricas.verificacoes_preparo == 0
    assert metricas.avaliacoes_candidatos == 0
    assert metricas.recuos == 0
    assert metricas.estados_sem_completo_possivel == 0
    assert metricas.tempo_segundos == 0.0

    metricas.iniciar_cronometro()
    assert metricas.parar_cronometro() == pytest.approx(0.5)


@pytest.mark.parametrize(("n", "preparo_esperado"), [(3, 72), (5, 200), (8, 512)])
def test_integracao_gerar_adjacencias_separa_preparo_de_resolucao(
    n: int,
    preparo_esperado: int,
) -> None:
    metricas = RegistradorMetricas()
    adjacencias = gerar_adjacencias(
        n, ao_verificar_preparo=metricas.registrar_verificacao_preparo
    )

    assert len(adjacencias) == n * n
    assert metricas.verificacoes_preparo == preparo_esperado
    assert metricas.verificacoes_movimentos == 0
    assert metricas.estados_explorados == 0


def test_contagem_manual_em_tabuleiro_minimo_3x3() -> None:
    """Confere à mão cada ponto de contagem em um tabuleiro mínimo 3×3.

    Preparo (3×3): 9 casas × 8 deslocamentos de KNIGHT_MOVES = 72 verificações.
    Resolução simulada a partir de (0, 0), cujos vizinhos válidos são (1, 2) e (2, 1):
      1. Entrada no estado inicial (0, 0): estados_explorados = 1.
      2. Leitura da lista de adjacência de (0, 0): 2 verificacoes_movimentos.
      3. Avaliação dos 2 candidatos: 2 avaliacoes_candidatos.
      4. Registro de 1 candidato com sinalizador da Proposição 5.3 falso.
      5. Avanço para (1, 2): estados_explorados = 2.
      6. Leitura da adjacência de (1, 2) (grau 2: (0, 0) e (2, 0)): +2 verificacoes_movimentos.
      7. Recuo removendo (1, 2) do caminho: recuos = 1.
    """
    metricas = RegistradorMetricas()
    adjacencias = gerar_adjacencias(
        3, ao_verificar_preparo=metricas.registrar_verificacao_preparo
    )

    inicio = (0, 0)
    caminho = [inicio]
    visitadas = {inicio}

    metricas.iniciar_cronometro()
    metricas.registrar_estado()

    candidatos_inicio = []
    for vizinho in adjacencias[inicio]:
        metricas.registrar_verificacao_movimento()
        if vizinho not in visitadas:
            candidatos_inicio.append(vizinho)

    assert set(candidatos_inicio) == {(1, 2), (2, 1)}

    for _ in candidatos_inicio:
        metricas.registrar_avaliacao_candidato()

    metricas.registrar_estado_sem_completo_possivel()

    proximo = (1, 2)
    caminho.append(proximo)
    visitadas.add(proximo)
    metricas.registrar_estado()

    for _ in adjacencias[proximo]:
        metricas.registrar_verificacao_movimento()

    removido = caminho.pop()
    visitadas.remove(removido)
    metricas.registrar_recuo()
    metricas.parar_cronometro()

    assert metricas.verificacoes_preparo == 72
    assert metricas.estados_explorados == 2
    assert metricas.verificacoes_movimentos == 4
    assert metricas.avaliacoes_candidatos == 2
    assert metricas.estados_sem_completo_possivel == 1
    assert metricas.recuos == 1
    assert metricas.tempo_segundos >= 0.0


def test_instancias_independentes_sem_estado_global() -> None:
    m1 = RegistradorMetricas()
    m2 = RegistradorMetricas()

    m1.registrar_estado()
    m1.registrar_verificacao_movimento(3)
    m1.registrar_recuo()

    assert m2.estados_explorados == 0
    assert m2.verificacoes_movimentos == 0
    assert m2.recuos == 0
