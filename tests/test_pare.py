"""Testes dos módulos ``core/pare.py`` e ``core/api.py`` (Dono: P1 — Lucas).

Grupos de testes previstos nas features F5 e F6:
- Grupo 5: indicadores F, I, P, A corretos em casos pequenos montados à mão,
  incluindo exclusão de ``v`` em ``I`` e ``P``.
- Grupo 6: Proposição 5.3 verificada em instâncias pequenas com força bruta
  (sempre que existe passeio completo a partir de ``v``, ``F == 1, I == 0, P <= 1``).
- Grupo 7: com mesmos ``(F, I, P)``, variante restritiva escolhe menor ``A``
  e expansiva escolhe maior ``A``.
- Grupo 10: determinismo — mesmos parâmetros e semente geram resultados idênticos
  (exceto ``tempo_segundos``).
"""
