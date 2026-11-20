from __future__ import annotations

from core.board import (  # noqa: F401
    gerar_adjacencias,
    validar_dimensao,
    validar_posicao,
    verificar_impossibilidade_paridade,
)
from core.busca import executar_recuo  # noqa: F401
from core.metrics import RegistradorMetricas  # noqa: F401
from core.pare import executar_guloso  # noqa: F401
from core.tipos import ConfiguracaoExecucao, ResultadoExecucao
from core.validator import validar_percurso  # noqa: F401


def obter_versao_codigo() -> str:
    raise NotImplementedError("Implementar obter_versao_codigo na feature F6 (modo-guloso).")


def resolver(config: ConfiguracaoExecucao) -> ResultadoExecucao:
    """Executa a estratégia PARE conforme ``config``, valida o resultado e mede o esforço.

    Deve:
    1. Validar ``config`` (dimensão, posição inicial, modo, variante, ``max_estados``).
    2. Definir ``seed_utilizada`` (gerando e registrando se ``config.seed is None``).
    3. Calcular ``impossibilidade_paridade`` apenas de forma informativa.
    4. Medir o tempo exclusivamente da resolução com ``RegistradorMetricas``.
    5. Despachar para ``executar_guloso`` ou ``executar_recuo``.
    6. Validar o percurso obtido via ``core.validator.validar_percurso`` antes de
       definir ``passeio_completo``.
    7. Devolver ``ResultadoExecucao`` preenchido apenas com medições reais.

    Args:
        config: Parâmetros imutáveis da execução (coordenadas 0-based).

    Returns:
        ``ResultadoExecucao`` completo e verificado.
    """
    raise NotImplementedError("Implementar resolver na feature F6 (modo-guloso).")
