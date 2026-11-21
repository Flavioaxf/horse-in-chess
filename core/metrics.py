from __future__ import annotations

import time


def _validar_quantidade_nao_negativa(quantidade: int, nome_metodo: str) -> int:
    if not isinstance(quantidade, int) or isinstance(quantidade, bool):
        raise ValueError(
            f"Quantidade inválida em {nome_metodo}: esperado inteiro não negativo, "
            f"recebido {type(quantidade).__name__} ({quantidade!r})."
        )
    if quantidade < 0:
        raise ValueError(
            f"Quantidade inválida em {nome_metodo}: esperado valor >= 0, recebido {quantidade}."
        )
    return quantidade


class RegistradorMetricas:
    """Centraliza os contadores operacionais e o cronômetro de uma execução.

    Todos os contadores são somente leitura externamente e só podem ser alterados
    pelos métodos desta classe, garantindo a rastreabilidade das convenções de
    medição definidas para a estratégia PARE:

    - ``estados_explorados``: +1 a cada entrada em caminho parcial válido (inclui início).
    - ``verificacoes_movimentos``: +1 a cada entrada lida de uma lista de adjacência
      durante a resolução (enumeração de candidatos, graus residuais, BFS/DFS).
    - ``verificacoes_preparo``: +1 a cada deslocamento testado contra os limites
      ao pré-calcular as adjacências (contado separadamente da resolução).
    - ``avaliacoes_candidatos``: +1 a cada cálculo da chave ``(F, I, P, A)``.
    - ``recuos``: +1 a cada remoção de uma casa do caminho atual (0 no modo guloso).
    - ``estados_sem_completo_possivel``: +1 a cada estado expandido com o sinalizador
      da Proposição 5.3 falso.
    - ``tempo_segundos``: tempo real de resolução medido com ``time.perf_counter()``.
    """

    def __init__(self) -> None:
        self._estados_explorados: int = 0
        self._verificacoes_movimentos: int = 0
        self._verificacoes_preparo: int = 0
        self._avaliacoes_candidatos: int = 0
        self._recuos: int = 0
        self._estados_sem_completo_possivel: int = 0
        self._inicio_cronometro: float | None = None
        self._tempo_segundos: float = 0.0

    @property
    def estados_explorados(self) -> int:
        return self._estados_explorados

    @property
    def verificacoes_movimentos(self) -> int:
        return self._verificacoes_movimentos

    @property
    def verificacoes_preparo(self) -> int:
        return self._verificacoes_preparo

    @property
    def avaliacoes_candidatos(self) -> int:
        return self._avaliacoes_candidatos

    @property
    def recuos(self) -> int:
        return self._recuos

    @property
    def estados_sem_completo_possivel(self) -> int:
        return self._estados_sem_completo_possivel

    @property
    def tempo_segundos(self) -> float:
        return self._tempo_segundos

    def iniciar_cronometro(self) -> None:
        """Inicia a medição de tempo da resolução usando ``time.perf_counter()``.

        Raises:
            RuntimeError: Se o cronômetro já estiver em execução.
        """
        if self._inicio_cronometro is not None:
            raise RuntimeError("Cronômetro já está em execução.")
        self._inicio_cronometro = time.perf_counter()

    def parar_cronometro(self) -> float:
        """Encerra a medição de tempo, acumula em ``tempo_segundos`` e retorna o total.

        Returns:
            Tempo acumulado em segundos (``self.tempo_segundos``).

        Raises:
            RuntimeError: Se o cronômetro não tiver sido iniciado.
        """
        if self._inicio_cronometro is None:
            raise RuntimeError("Cronômetro não foi iniciado.")
        decorrido = time.perf_counter() - self._inicio_cronometro
        self._inicio_cronometro = None
        if decorrido < 0.0:
            decorrido = 0.0
        self._tempo_segundos += decorrido
        return self._tempo_segundos

    def registrar_estado(self) -> None:
        self._estados_explorados += 1

    def registrar_verificacao_movimento(self, quantidade: int = 1) -> None:
        """Incrementa ``verificacoes_movimentos`` em ``quantidade`` (padrão 1).

        Args:
            quantidade: Número inteiro não negativo de entradas lidas de adjacência.

        Raises:
            ValueError: Se ``quantidade`` não for inteiro não negativo (ou for ``bool``).
        """
        valor = _validar_quantidade_nao_negativa(
            quantidade, "registrar_verificacao_movimento"
        )
        self._verificacoes_movimentos += valor

    def registrar_verificacao_preparo(self, quantidade: int = 1) -> None:
        """Incrementa ``verificacoes_preparo`` em ``quantidade`` (padrão 1).

        Args:
            quantidade: Número inteiro não negativo de deslocamentos testados no preparo.

        Raises:
            ValueError: Se ``quantidade`` não for inteiro não negativo (ou for ``bool``).
        """
        valor = _validar_quantidade_nao_negativa(
            quantidade, "registrar_verificacao_preparo"
        )
        self._verificacoes_preparo += valor

    def registrar_avaliacao_candidato(self) -> None:
        self._avaliacoes_candidatos += 1

    def registrar_recuo(self) -> None:
        self._recuos += 1

    def registrar_estado_sem_completo_possivel(self) -> None:
        self._estados_sem_completo_possivel += 1

    def resetar(self) -> None:
        self._estados_explorados = 0
        self._verificacoes_movimentos = 0
        self._verificacoes_preparo = 0
        self._avaliacoes_candidatos = 0
        self._recuos = 0
        self._estados_sem_completo_possivel = 0
        self._inicio_cronometro = None
        self._tempo_segundos = 0.0
