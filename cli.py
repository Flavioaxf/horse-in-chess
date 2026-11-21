"""Execução da estratégia PARE pelo terminal.

Recebe coordenadas **1-based** do usuário, converte para 0-based apenas aqui
(borda do sistema), chama ``core.api.resolver`` e imprime o tabuleiro numerado
e as métricas reais da execução.

Exemplo::

    python cli.py --n 8 --linha 1 --coluna 1 --modo recuo --variante restritiva \\
        --seed 2026 --max-estados 10000
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from core.api import resolver
from core.render import formatar_resumo_execucao, formatar_tabuleiro_texto
from core.tipos import DIMENSOES_OBRIGATORIAS, ConfiguracaoExecucao

MAX_ESTADOS_PADRAO = 10_000


def _inteiro_positivo(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError as erro:
        raise argparse.ArgumentTypeError(f"esperado inteiro, recebido {texto!r}") from erro
    if valor <= 0:
        raise argparse.ArgumentTypeError(f"esperado inteiro positivo, recebido {valor}")
    return valor


def construir_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Passeio do Cavalo — Estratégia PARE (execução por terminal).",
    )
    parser.add_argument(
        "--n",
        type=int,
        required=True,
        choices=DIMENSOES_OBRIGATORIAS,
        help="dimensão do tabuleiro n×n",
    )
    parser.add_argument(
        "--linha", type=int, required=True, help="linha inicial, de 1 a n"
    )
    parser.add_argument(
        "--coluna", type=int, required=True, help="coluna inicial, de 1 a n"
    )
    parser.add_argument(
        "--modo",
        choices=("guloso", "recuo"),
        default="guloso",
        help="guloso (sem recuo) ou recuo (busca com orçamento); padrão: guloso",
    )
    parser.add_argument(
        "--variante",
        choices=("restritiva", "expansiva"),
        default="restritiva",
        help="restritiva (principal, menor A) ou expansiva (comparação, maior A)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="semente do desempate; se omitida, é gerada e exibida",
    )
    parser.add_argument(
        "--max-estados",
        type=_inteiro_positivo,
        default=None,
        help=f"orçamento do modo recuo; padrão: {MAX_ESTADOS_PADRAO}",
    )
    return parser


def montar_configuracao(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> ConfiguracaoExecucao:
    """Valida os argumentos 1-based e devolve a configuração 0-based."""
    for nome in ("linha", "coluna"):
        valor = getattr(args, nome)
        if not 1 <= valor <= args.n:
            parser.error(f"--{nome} deve estar entre 1 e {args.n}; recebido {valor}.")

    if args.modo == "recuo":
        max_estados = args.max_estados if args.max_estados is not None else MAX_ESTADOS_PADRAO
    else:
        if args.max_estados is not None:
            print("Aviso: --max-estados é ignorado no modo guloso.", file=sys.stderr)
        max_estados = None

    return ConfiguracaoExecucao(
        n=args.n,
        inicio=(args.linha - 1, args.coluna - 1),
        modo=args.modo,
        variante=args.variante,
        seed=args.seed,
        max_estados=max_estados,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada da CLI. Retorna o código de saída do processo."""
    parser = construir_parser()
    args = parser.parse_args(argv)
    config = montar_configuracao(args, parser)

    try:
        resultado = resolver(config)
    except NotImplementedError as erro:
        print(f"Erro: o resolvedor ainda não está disponível ({erro}).", file=sys.stderr)
        return 2
    except ValueError as erro:
        print(f"Erro: configuração rejeitada pelo resolvedor: {erro}", file=sys.stderr)
        return 2

    linha_1, coluna_1 = config.inicio[0] + 1, config.inicio[1] + 1
    print(
        f"Passeio do Cavalo — PARE | tabuleiro {config.n}×{config.n} | "
        f"início (linha {linha_1}, coluna {coluna_1})"
    )
    print()
    print(formatar_tabuleiro_texto(config.n, resultado.melhor_percurso))
    print()
    print(formatar_resumo_execucao(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
