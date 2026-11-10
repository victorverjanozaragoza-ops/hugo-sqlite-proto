# ðŸš€ PrÃ¡ctica SGBD P1.1: Hugo + SQLite, un prototipo didÃ¡ctico

<p align="center">
  <a href="./practica_sgbd_hugo_sqlite.pdf" download>
    <img src="https://img.shields.io/badge/ðŸ“¥_DESCARGAR_ESTA_PRÃCTICA_EN_PDF-FF5722?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Descargar PDF" height="44"/>
  </a>
</p>

<p align="center">
  <b><a href="./practica_sgbd_hugo_sqlite.pdf">ðŸ“„ Ver / Descargar PDF desde el repositorio</a></b> &nbsp;|&nbsp; 
  <b><a href="https://raw.githubusercontent.com/victorverjanozaragoza-ops/hugo-sqlite-proto/main/practica_sgbd_hugo_sqlite.pdf">âš¡ Descarga directa del archivo PDF</a></b>
</p>

---

## ðŸ“‹ InformaciÃ³n de la Entrega

| Campo | Detalle |
| :--- | :--- |
| **MÃ³dulo** | Sistemas Gestores de Bases de Datos (SGBD - P1.1) |
| **Alumno** | VÃ­ctor Verjano |
| **Curso** | 2Âº ASIR |
| **Docente** | Jordi LÃ³pez Amat (`fenix011`) |
| **GuÃ­a Oficial** | [Librebits - SGBD P1.1 Hugo + SQLite](https://www.librebits.info/2asir/sgbd/hugo-sqlite-proto/) |
| **Repositorio Base** | [fp-bits/hugo-sqlite-proto](https://github.com/fp-bits/hugo-sqlite-proto) |
| **Entrega** | InvitaciÃ³n como colaborador enviada a `fenix011` |

---

## ðŸ’¡ Concepto: SQLite solo en tiempo de compilaciÃ³n (Build-Time)

A diferencia de los sitios web con bases de datos dinÃ¡micas tradicionales (donde un servidor MySQL o PostgreSQL estÃ¡ permanentemente activo atendiendo peticiones HTTP), en esta prÃ¡ctica **SQLite se utiliza exclusivamente durante la fase de construcciÃ³n (*build*)**:

```text
content/*.md  â”€â”€>  tools/index.py  â”€â”€>  build/site.db  â”€â”€â”¬â”€â”€>  static/search.json  â”€â”€>  Navegador (search.js)
 (Markdown)        (parsea + INSERT)    (SQLite local)   â”œâ”€â”€>  data/tags.json      â”€â”€>  Hugo (index.html)
                                                         â””â”€â”€>  data/stats.json     â”€â”€>  Hugo (footer.html)

                                        hugo  â”€â”€>  public/  (Lo Ãºnico que se despliega)
```

* **FilosofÃ­a Unix:** Cada herramienta hace una sola cosa bien y se comunican a travÃ©s de ficheros.
* **Seguridad y Rendimiento:** `build/site.db` es efÃ­mera y no se publica. El directorio `public/` generado contiene Ãºnicamente ficheros estÃ¡ticos HTML, CSS y JavaScript.

---

## ðŸ› ï¸ Ejercicios Resueltos

### âœ… Ejercicio 1: AÃ±adir post con `tags: [sql]`
* Se ha creado el artÃ­culo [`content/posts/sql-en-build-time.md`](./content/posts/sql-en-build-time.md).
* Incluye en su front matter `tags: [sql, sgbd, hugo]`.
* Al ejecutar `tools/index.py`, la consulta SQL agregada `Q_TAGS` agrupa y cuenta automÃ¡ticamente la nueva etiqueta `sql` sin necesidad de modificar lÃ³gica en el cÃ³digo fuente.

### âœ… Ejercicio 2: Flag `--drafts` en `tools/index.py` y soporte en `Makefile`
* **Problema:** `hugo server -D` compila los borradores (`draft: true`), pero la bÃºsqueda no los localizaba porque `tools/index.py` los descartaba de forma fija.
* **SoluciÃ³n:** Se ha modificado `read_all(include_drafts=False)` en `tools/index.py` para admitir el parÃ¡metro `--drafts` desde la lÃ­nea de comandos (`sys.argv`).
* **Regla en Makefile:** Se ha aÃ±adido el comando `make serve-drafts`:
  ```makefile
  serve-drafts: ## Servidor local con recarga incluyendo borradores
  	python3 tools/index.py --drafts
  	hugo server -D
  ```

### âœ… Ejercicio 3: Tabla `words(url, n)` y estadÃ­sticas globales en el footer
* Se ha ampliado el esquema de SQLite en `tools/index.py` incorporando la tabla relacional `words`:
  ```sql
  CREATE TABLE words (
    url TEXT PRIMARY KEY REFERENCES posts(url),
    n   INTEGER NOT NULL
  );
  ```
* Se implementÃ³ una funciÃ³n pura `count_words(text)` con expresiones regulares para calcular la longitud en palabras de cada post.
* Se aÃ±adiÃ³ la consulta `Q_STATS` que exporta mÃ©tricas agregadas a `data/stats.json`:
  ```sql
  SELECT json_object(
    'total_words', COALESCE(SUM(n), 0),
    'avg_words', COALESCE(ROUND(AVG(n), 1), 0),
    'total_posts', COUNT(*)
  ) FROM words;
  ```
* En [`layouts/partials/footer.html`](./layouts/partials/footer.html) se consume `hugo.Data.stats` para mostrar el conteo total de palabras indexadas y artÃ­culos.
* Se actualizaron las reglas `check` y `clean` del `Makefile` para validar y limpiar `data/stats.json`.

### âœ… Ejercicio 4: OrdenaciÃ³n de resultados de bÃºsqueda por relevancia ponderada
* En [`static/search.js`](./static/search.js) se refactorizÃ³ la funciÃ³n `search` para aplicar ponderaciÃ³n funcional:
  * Coincidencia en el **tÃ­tulo**: factor **x3**.
  * Coincidencia en las **etiquetas**: factor **x2**.
  * Coincidencia en el **cuerpo**: factor **x1**.
* Mantiene un estilo puramente funcional (funciones puras sin mutaciÃ³n, ES6+ vanilla) y ordena los resultados de mayor a menor puntuaciÃ³n antes de renderizarlos en el DOM.

---

## ðŸš€ Uso y ComprobaciÃ³n

```bash
# Validar que los JSON exportados son vÃ¡lidos
make check

# Compilar el sitio estÃ¡tico para producciÃ³n (public/)
make build

# Servidor de desarrollo estÃ¡ndar (puerto 1313)
make serve

# Servidor de desarrollo con borradores incluidos
make serve-drafts

# Limpiar ficheros generados
make clean
```

---

## ðŸ“Š RÃºbrica y Entrega

* **Entrega oficial:** Repositorio en fork con commits incrementales e invitaciÃ³n de colaborador enviada al profesor (`fenix011`).
* **Servidor de prÃ¡cticas SFTP:** `verjano@asir.fp-bits.org` (respaldo de la memoria en PDF).