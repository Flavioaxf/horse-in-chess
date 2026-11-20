from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Posicao = tuple[int, int]
Adjacencias = dict[Posicao, tuple[Posicao, ...]]

ModoExecucao = Literal["guloso", "recuo"]
VariantePARE = Literal["restritiva", "expansiva"]
MotivoParada = Literal[
    "completo",
    "sem_movimentos",
    "busca_esgotada",
    "limite_estados",
]

DIMENSOES_OBRIGATORIAS: tuple[int, ...] = (5, 8)
MODOS_VALIDOS: frozenset[str] = frozenset({"guloso", "recuo"})
VARIANTES_VALIDAS: frozenset[str] = frozenset({"restritiva", "expansiva"})
MOTIVOS_PARADA_VALIDOS: frozenset[str] = frozenset(
    {"completo", "sem_movimentos", "busca_esgotada", "limite_estados"}
)


@dataclass(frozen=True)
class ConfiguracaoExecucao:
    """Parâmetros imutáveis de uma execução da estratégia PARE.

    Attributes:
        n: Dimensão do tabuleiro quadrado (5 ou 8 nas execuções obrigatórias).
        inicio: Posição inicial ``(linha, coluna)`` em índices 0-based.
        modo: Estratégia de exploração (``"guloso"`` ou ``"recuo"``).
        variante: Critério final de ordenação em ``A`` (``"restritiva"`` ou ``"expansiva"``).
        seed: Semente opcional para desempate determinístico; quando ``None``,
            uma semente é gerada e registrada em ``ResultadoExecucao.seed_utilizada``.
        max_estados: Orçamento máximo de estados explorados (obrigatório no modo ``"recuo"``).
        podar_inviaveis: Opção explícita de poda baseada na Proposição 5.3;
            permanece desligada por padrão (``False``).
    """

    n: int
    inicio: Posicao
    modo: ModoExecucao
    variante: VariantePARE = "restritiva"
    seed: int | None = None
    max_estados: int | None = None
    podar_inviaveis: bool = False


@dataclass(frozen=True)
class AvaliacaoCandidato:
    """Indicadores estruturais PARE calculados sobre o grafo residual ``G_v``.

    Attributes:
        candidato: Casa candidata ``v = (linha, coluna)`` em índices 0-based.
        fragmentacao: ``F`` — número de componentes conexas de ``G_v``.
        isolamento: ``I`` — vértices em ``U`` (excluindo ``v``) com grau residual 0.
        pressao: ``P`` — vértices em ``U`` (excluindo ``v``) com grau residual 1.
        acessibilidade: ``A`` — grau de ``v`` em ``G_v`` (vizinhos de ``v`` em ``U``).
        completo_ainda_possivel: Sinalizador da condição necessária (Proposição 5.3):
            ``F == 1 and I == 0 and P <= 1``.
    """

    candidato: Posicao
    fragmentacao: int
    isolamento: int
    pressao: int
    acessibilidade: int
    completo_ainda_possivel: bool


@dataclass(frozen=True)
class ResultadoValidacao:
    """Resultado produzido pelo validador independente de percursos.

    Attributes:
        valido: ``True`` se o percurso respeita limites, início, saltos do cavalo
            e unicidade de casas.
        passeio_completo: ``True`` somente se ``valido`` e todas as ``n * n``
            casas do tabuleiro foram visitadas.
        erros: Tupla com descrições objetivas das violações encontradas.
    """

    valido: bool
    passeio_completo: bool
    erros: tuple[str, ...] = ()


@dataclass
class ResultadoExecucao:
    """Resultado completo e mensurável retornado por ``core.api.resolver``.

    Attributes:
        config: Configuração que originou a execução.
        seed_utilizada: Semente efetivamente utilizada no gerador local ``random.Random``.
        melhor_percurso: Melhor sequência válida encontrada (0-based, em ordem de visita).
        casas_visitadas: Comprimento de ``melhor_percurso``.
        total_casas: Total de casas do tabuleiro (``n * n``).
        cobertura_percentual: Percentual de cobertura ``100 * casas_visitadas / total_casas``.
        passeio_completo: ``True`` apenas quando ``casas_visitadas == total_casas``
            e aprovado pelo validador independente.
        motivo_parada: Condição explícita de encerramento da busca.
        tempo_segundos: Tempo real de resolução medido por ``time.perf_counter()``.
        estados_explorados: Quantidade de entradas em caminhos parciais válidos (inclui início).
        verificacoes_movimentos: Entradas lidas de listas de adjacência durante a resolução.
        verificacoes_preparo: Deslocamentos testados contra limites no pré-cálculo de adjacências.
        avaliacoes_candidatos: Quantidade de cálculos da chave ``(F, I, P, A)``.
        recuos: Remoções de casas do caminho atual (sempre ``0`` no modo guloso).
        impossibilidade_paridade: Indicador informativo de impossibilidade estrutural por cor.
        versao_codigo: Hash curto do commit Git em execução.
        estados_sem_completo_possivel: Quantidade de estados expandidos com o sinalizador
            ``completo_ainda_possivel`` falso (métrica opcional da seção 5.3).
    """

    config: ConfiguracaoExecucao
    seed_utilizada: int
    melhor_percurso: list[Posicao]
    casas_visitadas: int
    total_casas: int
    cobertura_percentual: float
    passeio_completo: bool
    motivo_parada: MotivoParada
    tempo_segundos: float
    estados_explorados: int
    verificacoes_movimentos: int
    verificacoes_preparo: int
    avaliacoes_candidatos: int
    recuos: int
    impossibilidade_paridade: bool
    versao_codigo: str
    estados_sem_completo_possivel: int = 0
