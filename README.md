# 🚀 Práctica SGBD P1.1: Hugo + SQLite, un prototipo didáctico

<p align="center">
  <a href="./practica_sgbd_hugo_sqlite.pdf" download>
    <img src="https://img.shields.io/badge/📥_DESCARGAR_ESTA_PRÁCTICA_EN_PDF-FF5722?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Descargar PDF" height="44"/>
  </a>
</p>

<p align="center">
  <b><a href="./practica_sgbd_hugo_sqlite.pdf">📄 Ver / Descargar PDF desde el repositorio</a></b> &nbsp;|&nbsp; 
  <b><a href="https://raw.githubusercontent.com/victorverjanozaragoza-ops/hugo-sqlite-proto/main/practica_sgbd_hugo_sqlite.pdf">⚡ Descarga directa del archivo PDF</a></b>
</p>

---

## 📋 Información de la Entrega

| Campo | Detalle |
| :--- | :--- |
| **Módulo** | Sistemas Gestores de Bases de Datos (SGBD - P1.1) |
| **Alumno** | Víctor Verjano |
| **Curso** | 2º ASIR |
| **Docente** | Jordi López Amat (`fenix011`) |
| **Guía Oficial** | [Librebits - SGBD P1.1 Hugo + SQLite](https://www.librebits.info/2asir/sgbd/hugo-sqlite-proto/) |
| **Repositorio Base** | [fp-bits/hugo-sqlite-proto](https://github.com/fp-bits/hugo-sqlite-proto) |
| **Entrega** | Invitación como colaborador enviada a `fenix011` |

---

## 💡 Concepto: SQLite solo en tiempo de compilación (Build-Time)

A diferencia de los sitios web con bases de datos dinámicas tradicionales (donde un servidor MySQL o PostgreSQL está permanentemente activo atendiendo peticiones HTTP), en esta práctica **SQLite se utiliza exclusivamente durante la fase de construcción (*build*)**:

```text
content/*.md  ──>  tools/index.py  ──>  build/site.db  ──┬──>  static/search.json  ──>  Navegador (search.js)
 (Markdown)        (parsea + INSERT)    (SQLite local)   ├──>  data/tags.json      ──>  Hugo (index.html)
                                                         └──>  data/stats.json     ──>  Hugo (footer.html)

                                        hugo  ──>  public/  (Lo único que se despliega)
```

* **Filosofía Unix:** Cada herramienta hace una sola cosa bien y se comunican a través de ficheros.
* **Seguridad y Rendimiento:** `build/site.db` es efímera y no se publica. El directorio `public/` generado contiene únicamente ficheros estáticos HTML, CSS y JavaScript.

---

## 🛠️ Ejercicios Resueltos

### ✅ Ejercicio 1: Añadir post con `tags: [sql]`
* Se ha creado el artículo [`content/posts/sql-en-build-time.md`](./content/posts/sql-en-build-time.md).
* Incluye en su front matter `tags: [sql, sgbd, hugo]`.
* Al ejecutar `tools/index.py`, la consulta SQL agregada `Q_TAGS` agrupa y cuenta automáticamente la nueva etiqueta `sql` sin necesidad de modificar lógica en el código fuente.

### ✅ Ejercicio 2: Flag `--drafts` en `tools/index.py` y soporte en `Makefile`
* **Problema:** `hugo server -D` compila los borradores (`draft: true`), pero la búsqueda no los localizaba porque `tools/index.py` los descartaba de forma fija.
* **Solución:** Se ha modificado `read_all(include_drafts=False)` en `tools/index.py` para admitir el parámetro `--drafts` desde la línea de comandos (`sys.argv`).
* **Regla en Makefile:** Se ha añadido el comando `make serve-drafts`:
  ```makefile
  serve-drafts: ## Servidor local con recarga incluyendo borradores
  	python3 tools/index.py --drafts
  	hugo server -D
  ```

### ✅ Ejercicio 3: Tabla `words(url, n)` y estadísticas globales en el footer
* Se ha ampliado el esquema de SQLite en `tools/index.py` incorporando la tabla relacional `words`:
  ```sql
  CREATE TABLE words (
    url TEXT PRIMARY KEY REFERENCES posts(url),
    n   INTEGER NOT NULL
  );
  ```
* Se implementó una función pura `count_words(text)` con expresiones regulares para calcular la longitud en palabras de cada post.
* Se añadió la consulta `Q_STATS` que exporta métricas agregadas a `data/stats.json`:
  ```sql
  SELECT json_object(
    'total_words', COALESCE(SUM(n), 0),
    'avg_words', COALESCE(ROUND(AVG(n), 1), 0),
    'total_posts', COUNT(*)
  ) FROM words;
  ```
* En [`layouts/partials/footer.html`](./layouts/partials/footer.html) se consume `hugo.Data.stats` para mostrar el conteo total de palabras indexadas y artículos.
* Se actualizaron las reglas `check` y `clean` del `Makefile` para validar y limpiar `data/stats.json`.

### ✅ Ejercicio 4: Ordenación de resultados de búsqueda por relevancia ponderada
* En [`static/search.js`](./static/search.js) se refactorizó la función `search` para aplicar ponderación funcional:
  * Coincidencia en el **título**: factor **x3**.
  * Coincidencia en las **etiquetas**: factor **x2**.
  * Coincidencia en el **cuerpo**: factor **x1**.
* Mantiene un estilo puramente funcional (funciones puras sin mutación, ES6+ vanilla) y ordena los resultados de mayor a menor puntuación antes de renderizarlos en el DOM.

---

## 🚀 Uso y Comprobación

```bash
# Validar que los JSON exportados son válidos
make check

# Compilar el sitio estático para producción (public/)
make build

# Servidor de desarrollo estándar (puerto 1313)
make serve

# Servidor de desarrollo con borradores incluidos
make serve-drafts

# Limpiar ficheros generados
make clean
```

---
