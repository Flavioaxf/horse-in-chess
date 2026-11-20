from __future__ import annotations


class RegistradorMetricas:
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
        raise NotImplementedError("Implementar iniciar_cronometro na feature F2 (metricas).")

    def parar_cronometro(self) -> float:
        raise NotImplementedError("Implementar parar_cronometro na feature F2 (metricas).")

    def registrar_estado(self) -> None:
        raise NotImplementedError("Implementar registrar_estado na feature F2 (metricas).")

    def registrar_verificacao_movimento(self, quantidade: int = 1) -> None:
        raise NotImplementedError(
            "Implementar registrar_verificacao_movimento na feature F2 (metricas)."
        )

    def registrar_verificacao_preparo(self, quantidade: int = 1) -> None:
        raise NotImplementedError(
            "Implementar registrar_verificacao_preparo na feature F2 (metricas)."
        )

    def registrar_avaliacao_candidato(self) -> None:
        raise NotImplementedError(
            "Implementar registrar_avaliacao_candidato na feature F2 (metricas)."
        )

    def registrar_recuo(self) -> None:
        raise NotImplementedError("Implementar registrar_recuo na feature F2 (metricas).")

    def registrar_estado_sem_completo_possivel(self) -> None:
        raise NotImplementedError(
            "Implementar registrar_estado_sem_completo_possivel na feature F2 (metricas)."
        )

    def resetar(self) -> None:
        raise NotImplementedError("Implementar resetar na feature F2 (metricas).")
