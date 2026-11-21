from __future__ import annotations

from pathlib import Path
import random
import secrets
import subprocess

from core.board import (
    gerar_adjacencias,
    validar_dimensao,
    validar_posicao,
    verificar_impossibilidade_paridade,
)
from core.busca import executar_recuo
from core.metrics import RegistradorMetricas
from core.pare import executar_guloso
from core.tipos import (
    ConfiguracaoExecucao,
    MODOS_VALIDOS,
    MOTIVOS_PARADA_VALIDOS,
    ResultadoExecucao,
    VARIANTES_VALIDAS,
)
from core.validator import validar_percurso

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
_VERSAO_FALLBACK = "desconhecida"


def _eh_inteiro_estrito(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_configuracao(config: ConfiguracaoExecucao) -> None:
    if not isinstance(config, ConfiguracaoExecucao):
        raise ValueError(
            "Configuração inválida: esperado ConfiguracaoExecucao, "
            f"recebido {type(config).__name__}."
        )

    validar_dimensao(config.n)
    validar_posicao(config.n, config.inicio)

    if config.modo not in MODOS_VALIDOS:
        raise ValueError(
            f"Modo de execução inválido: {config.modo!r}. "
            f"Valores aceitos: {sorted(MODOS_VALIDOS)}."
        )

    if config.variante not in VARIANTES_VALIDAS:
        raise ValueError(
            f"Variante PARE inválida: {config.variante!r}. "
            f"Valores aceitos: {sorted(VARIANTES_VALIDAS)}."
        )

    if config.seed is not None and not _eh_inteiro_estrito(config.seed):
        raise ValueError(
            f"Semente inválida: esperado inteiro ou None, "
            f"recebido {type(config.seed).__name__} ({config.seed!r})."
        )

    if not isinstance(config.podar_inviaveis, bool):
        raise ValueError(
            "Parâmetro podar_inviaveis inválido: esperado bool, "
            f"recebido {type(config.podar_inviaveis).__name__}."
        )

    if config.modo == "recuo":
        if (
            config.max_estados is None
            or not _eh_inteiro_estrito(config.max_estados)
            or config.max_estados < 1
        ):
            raise ValueError(
                "Orçamento max_estados inválido para o modo 'recuo': "
                f"esperado inteiro >= 1, recebido {config.max_estados!r}."
            )
    elif config.max_estados is not None and (
        not _eh_inteiro_estrito(config.max_estados) or config.max_estados < 1
    ):
        raise ValueError(
            "Parâmetro max_estados inválido: esperado None ou inteiro >= 1, "
            f"recebido {config.max_estados!r}."
        )


def obter_versao_codigo() -> str:
    try:
        processo = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_RAIZ_PROJETO,
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return _VERSAO_FALLBACK

    if processo.returncode != 0:
        return _VERSAO_FALLBACK

    versao = processo.stdout.strip()
    return versao if versao else _VERSAO_FALLBACK


def resolver(config: ConfiguracaoExecucao) -> ResultadoExecucao:
    """Executa a estratégia PARE conforme ``config``, valida o resultado e mede o esforço.

    Etapas:
    1. Valida ``config`` (dimensão, posição inicial, modo, variante, semente e ``max_estados``).
    2. Define ``seed_utilizada`` (gerando via ``secrets`` quando ``config.seed is None``).
    3. Calcula ``impossibilidade_paridade`` de forma estritamente informativa.
    4. Pré-calcula adjacências registrando ``verificacoes_preparo`` à parte.
    5. Mede o tempo exclusivamente da resolução com ``RegistradorMetricas`` e despacha
       para ``executar_guloso`` ou ``executar_recuo``.
    6. Valida o percurso obtido via ``core.validator.validar_percurso`` antes de
       definir ``passeio_completo``.
    7. Devolve ``ResultadoExecucao`` preenchido apenas com medições reais.

    Args:
        config: Parâmetros imutáveis da execução (coordenadas 0-based).

    Returns:
        ``ResultadoExecucao`` completo e verificado.

    Raises:
        ValueError: Se algum parâmetro de ``config`` for inválido.
        RuntimeError: Se o algoritmo interno produzir um percurso inválido ou um
            motivo de parada inconsistente.
    """
    _validar_configuracao(config)

    seed_utilizada = (
        config.seed if config.seed is not None else secrets.randbits(32)
    )
    rng = random.Random(seed_utilizada)
    impossibilidade_paridade = verificar_impossibilidade_paridade(
        config.n, config.inicio
    )

    metricas = RegistradorMetricas()
    adjacencias = gerar_adjacencias(
        config.n,
        ao_verificar_preparo=metricas.registrar_verificacao_preparo,
    )

    metricas.iniciar_cronometro()
    try:
        if config.modo == "guloso":
            melhor_percurso, motivo_parada = executar_guloso(
                n=config.n,
                inicio=config.inicio,
                variante=config.variante,
                adjacencias=adjacencias,
                rng=rng,
                metricas=metricas,
            )
        else:
            assert config.max_estados is not None
            melhor_percurso, motivo_parada = executar_recuo(
                n=config.n,
                inicio=config.inicio,
                variante=config.variante,
                max_estados=config.max_estados,
                adjacencias=adjacencias,
                rng=rng,
                metricas=metricas,
                podar_inviaveis=config.podar_inviaveis,
            )
    finally:
        metricas.parar_cronometro()

    if motivo_parada not in MOTIVOS_PARADA_VALIDOS:
        raise RuntimeError(
            f"Motivo de parada inválido retornado pelo resolvedor: {motivo_parada!r}."
        )

    validacao = validar_percurso(config.n, config.inicio, melhor_percurso)
    if not validacao.valido:
        detalhes = "; ".join(validacao.erros)
        raise RuntimeError(
            f"Percurso inválido produzido pelo resolvedor: {detalhes}"
        )

    total_casas = config.n * config.n
    casas_visitadas = len(melhor_percurso)
    cobertura_percentual = (100.0 * casas_visitadas) / total_casas
    passeio_completo = (
        validacao.valido
        and validacao.passeio_completo
        and casas_visitadas == total_casas
    )

    if motivo_parada == "completo" and not passeio_completo:
        raise RuntimeError(
            "Inconsistência interna: motivo_parada='completo', porém o validador "
            "não confirmou passeio completo."
        )

    return ResultadoExecucao(
        config=config,
        seed_utilizada=seed_utilizada,
        melhor_percurso=list(melhor_percurso),
        casas_visitadas=casas_visitadas,
        total_casas=total_casas,
        cobertura_percentual=cobertura_percentual,
        passeio_completo=passeio_completo,
        motivo_parada=motivo_parada,
        tempo_segundos=metricas.tempo_segundos,
        estados_explorados=metricas.estados_explorados,
        verificacoes_movimentos=metricas.verificacoes_movimentos,
        verificacoes_preparo=metricas.verificacoes_preparo,
        avaliacoes_candidatos=metricas.avaliacoes_candidatos,
        recuos=metricas.recuos,
        impossibilidade_paridade=impossibilidade_paridade,
        versao_codigo=obter_versao_codigo(),
        estados_sem_completo_possivel=metricas.estados_sem_completo_possivel,
    )
