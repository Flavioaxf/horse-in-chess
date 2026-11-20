"""Testes do módulo ``core/busca.py`` (Dono: P2 — Diego).

Grupos de testes previstos na feature F7:
- Grupo 8: recuo desmarca casas corretamente e não mistura caminhos alternativos.
- Grupo 9: melhor percurso preservado ao atingir ``max_estados``, limite respeitado
  e ``motivo_parada`` classificado corretamente (``completo``, ``busca_esgotada``
  ou ``limite_estados``).
- Grupo 10: determinismo no modo com recuo com a mesma semente.
"""
