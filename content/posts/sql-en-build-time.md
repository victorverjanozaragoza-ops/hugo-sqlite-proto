---
title: "SQL en tiempo de build con SQLite"
date: 2026-11-10
description: "CÃ³mo indexar y agregar metadatos de un sitio web estÃ¡tico usando consultas relacionales SQL durante la compilaciÃ³n."
tags: [sql, sgbd, hugo]
---
En esta prÃ¡ctica incorporamos **SQLite** en el proceso de construcciÃ³n de nuestro sitio web estÃ¡tico generado con Hugo.

A diferencia de las arquitecturas web tradicionales donde el motor de base de datos corre permanentemente como un servicio en producciÃ³n atendiendo peticiones HTTP en tiempo real, aquÃ­ la base de datos `build/site.db` solo existe en local mientras se ejecuta `tools/index.py`.

### Â¿QuÃ© aporta SQL en el build?

1. **Modelado relacional limpio**: Tablas `posts`, `tags` y `words` con claves primarias y forÃ¡neas bien definidas.
2. **GeneraciÃ³n directa de JSON**: Gracias a las funciones `json_group_array` y `json_object` de la extensiÃ³n JSON1 de SQLite, la consulta SQL produce directamente la estructura exacta que necesita `static/search.json` y `data/tags.json`.
3. **Agregaciones eficientes sin bucles en cÃ³digo**: Consultas con `GROUP BY` y `COUNT(*)` como `Q_TAGS` para calcular el conteo de posts por etiqueta automÃ¡ticamente, y `SUM(n)` sobre `words` para el recuento global de palabras.