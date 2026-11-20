"""Testes do módulo ``core/board.py`` (Dono: P1 — Lucas).

Grupos de testes previstos na feature F1:
- Grupo 1: dimensões 5×5 e 8×8 aceitas; dimensões e coordenadas inválidas rejeitadas.
- Grupo 2: vizinhança correta em cantos, bordas e centro (graus 2, 3, 4, 6, 8 no 8×8).
- Grupo 13: detector de paridade verdadeiro para 5×5 (1,2) 1-based / (0,1) 0-based,
  falso para 5×5 (1,1) 1-based / (0,0) 0-based e para todo 8×8.
"""
