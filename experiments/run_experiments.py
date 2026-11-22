from __future__ import annotations

import argparse
from collections.abc import Sequence
import csv
from pathlib import Path
import platform
import sys

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(_RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_PROJETO))

from core.api import resolver  # noqa: E402
from core.tipos import ResultadoExecucao, ResultadoValidacao  # noqa: E402
from core.validator import validar_percurso  # noqa: E402
from experiments.cenarios import (  # noqa: E402
    CENARIOS_OBRIGATORIOS,
    CenarioExperimental,
    MAX_ESTADOS_PADRAO,
    SEED_PADRAO,
    gerar_configuracoes_protocolo,
)

CAMINHO_SAIDA_PADRAO: Path = _RAIZ_PROJETO / "results" / "experiments.csv"

COLUNAS_CSV: tuple[str, ...] = (
    "cenario",
    "tabuleiro",
    "n",
    "linha_inicial",
    "coluna_inicial",
    "posicao_inicial",
    "objetivo",
    "modo",
    "variante",
    "seed",
    "max_estados",
    "casas_visitadas",
    "total_casas",
    "cobertura_percentual",
    "passeio_completo",
    "motivo_parada",
    "tempo_segundos",
    "estados_explorados",
    "verificacoes_movimentos",
    "verificacoes_preparo",
    "avaliacoes_candidatos",
    "recuos",
    "impossibilidade_paridade",
    "estados_sem_completo_possivel",
    "validador_aprovado",
    "versao_codigo",
    "python_versao",
    "sistema_operacional",
    "processador",
)


def _obter_metadados_ambiente() -> dict[str, str]:
    sistema = f"{platform.system()} {platform.release()}".strip()
    processador = platform.processor().strip() or platform.machine().strip() or "desconhecido"
    return {
        "python_versao": platform.python_version(),
        "sistema_operacional": sistema,
        "processador": processador,
    }


def _montar_linha_csv(
    cenario: CenarioExperimental,
    resultado: ResultadoExecucao,
    validacao: ResultadoValidacao,
    ambiente: dict[str, str],
) -> dict[str, object]:
    cfg = resultado.config
    return {
        "cenario": cenario.codigo,
        "tabuleiro": f"{cenario.n}x{cenario.n}",
        "n": cenario.n,
        "linha_inicial": cenario.linha_1based,
        "coluna_inicial": cenario.coluna_1based,
        "posicao_inicial": f"({cenario.linha_1based}, {cenario.coluna_1based})",
        "objetivo": cenario.objetivo,
        "modo": cfg.modo,
        "variante": cfg.variante,
        "seed": resultado.seed_utilizada,
        "max_estados": "" if cfg.max_estados is None else cfg.max_estados,
        "casas_visitadas": resultado.casas_visitadas,
        "total_casas": resultado.total_casas,
        "cobertura_percentual": f"{resultado.cobertura_percentual:.2f}",
        "passeio_completo": resultado.passeio_completo,
        "motivo_parada": resultado.motivo_parada,
        "tempo_segundos": f"{resultado.tempo_segundos:.6f}",
        "estados_explorados": resultado.estados_explorados,
        "verificacoes_movimentos": resultado.verificacoes_movimentos,
        "verificacoes_preparo": resultado.verificacoes_preparo,
        "avaliacoes_candidatos": resultado.avaliacoes_candidatos,
        "recuos": resultado.recuos,
        "impossibilidade_paridade": resultado.impossibilidade_paridade,
        "estados_sem_completo_possivel": resultado.estados_sem_completo_possivel,
        "validador_aprovado": validacao.valido,
        "versao_codigo": resultado.versao_codigo,
        "python_versao": ambiente["python_versao"],
        "sistema_operacional": ambiente["sistema_operacional"],
        "processador": ambiente["processador"],
    }


def executar_protocolo(
    caminho_saida: Path,
    seed: int = SEED_PADRAO,
    max_estados: int = MAX_ESTADOS_PADRAO,
    cenarios: Sequence[CenarioExperimental] = CENARIOS_OBRIGATORIOS,
) -> Path:
    """Executa todas as combinações do protocolo, valida cada percurso e grava o CSV.

    Args:
        caminho_saida: Caminho do arquivo CSV a ser gerado.
        seed: Semente determinística compartilhada por todas as execuções.
        max_estados: Orçamento máximo de estados para o modo ``recuo``.
        cenarios: Cenários experimentais em coordenadas 1-based.

    Returns:
        ``Path`` do arquivo CSV efetivamente escrito.

    Raises:
        ValueError: Se os parâmetros do protocolo forem inválidos.
        RuntimeError: Se qualquer percurso produzido falhar no validador
            independente ou apresentar inconsistência de completude.
    """
    destino = Path(caminho_saida)
    configuracoes = gerar_configuracoes_protocolo(
        seed=seed,
        max_estados=max_estados,
        cenarios=cenarios,
    )
    ambiente = _obter_metadados_ambiente()

    linhas: list[dict[str, object]] = []
    for cenario, config in configuracoes:
        resultado = resolver(config)
        validacao = validar_percurso(
            config.n,
            config.inicio,
            resultado.melhor_percurso,
        )
        if not validacao.valido:
            detalhes = "; ".join(validacao.erros)
            raise RuntimeError(
                f"Validador independente rejeitou o percurso de {cenario.codigo} "
                f"({config.modo}/{config.variante}): {detalhes}"
            )
        if resultado.passeio_completo != validacao.passeio_completo:
            raise RuntimeError(
                f"Inconsistência de completude em {cenario.codigo} "
                f"({config.modo}/{config.variante}): resultado={resultado.passeio_completo}, "
                f"validador={validacao.passeio_completo}."
            )

        linhas.append(_montar_linha_csv(cenario, resultado, validacao, ambiente))

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_CSV)
        escritor.writeheader()
        escritor.writerows(linhas)

    return destino


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Executa o protocolo experimental obrigatório (16 execuções: T01..T04 × "
            "2 modos × 2 variantes), valida todos os percursos e exporta CSV."
        )
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=CAMINHO_SAIDA_PADRAO,
        help="Caminho do arquivo CSV de saída (padrão: results/experiments.csv).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED_PADRAO,
        help=f"Semente determinística das execuções (padrão: {SEED_PADRAO}).",
    )
    parser.add_argument(
        "--max-estados",
        type=int,
        default=MAX_ESTADOS_PADRAO,
        dest="max_estados",
        help=f"Orçamento máximo de estados no modo recuo (padrão: {MAX_ESTADOS_PADRAO}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada de linha de comando para geração do CSV experimental."""
    parser = _criar_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        caminho_gerado = executar_protocolo(
            caminho_saida=args.saida,
            seed=args.seed,
            max_estados=args.max_estados,
        )
    except ValueError as erro:
        print(f"Erro de parâmetro: {erro}", file=sys.stderr)
        return 2

    with caminho_gerado.open("r", encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    print(
        f"Protocolo concluído: {len(linhas)} execuções validadas e gravadas em "
        f"{caminho_gerado}"
    )
    for linha in linhas:
        print(
            f"  {linha['cenario']} ({linha['tabuleiro']} {linha['posicao_inicial']}) | "
            f"{linha['modo']:6s} | {linha['variante']:10s} | "
            f"{linha['casas_visitadas']:>2s}/{linha['total_casas']:<2s} "
            f"({linha['cobertura_percentual']:>6s}%) | "
            f"estados={linha['estados_explorados']:>5s} | "
            f"verif={linha['verificacoes_movimentos']:>7s} | "
            f"recuos={linha['recuos']:>5s} | "
            f"tempo={linha['tempo_segundos']}s | {linha['motivo_parada']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
