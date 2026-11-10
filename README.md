# Práctica SGBD: Hugo + SQLite (Prototipo didáctico)

<p align="center">
  <a href="./practica_sgbd_hugo_sqlite.pdf" download>
    <img src="https://img.shields.io/badge/📥_Descargar_Práctica_en_PDF-red?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Descargar PDF" height="40"/>
  </a>
</p>

<p align="center">
  <a href="./practica_sgbd_hugo_sqlite.pdf"><b>Descargar o ver la memoria en PDF</b></a>
</p>

---

* **Alumno:** Víctor Verjano
* **Curso:** 2º ASIR
* **Módulo:** Sistemas Gestores de Bases de Datos (SGBD)

---

## Descripción de la práctica

En esta práctica integramos **SQLite** en el proceso de compilación (build) de un sitio web estático generado con **Hugo**.

La idea principal es seguir la filosofía Unix: la base de datos `build/site.db` solo se utiliza en local durante la ejecución de `tools/index.py` para leer los ficheros Markdown, guardarlos en tablas y extraer los datos necesarios en formato JSON. En producción (directorio `public/`) no hay base de datos, solo ficheros estáticos.

```text
content/*.md  -->  tools/index.py  -->  build/site.db  --+-->  static/search.json  -->  navegador (search.js)
 (Markdown)        (parsea + INSERT)    (SQLite local)   +-->  data/tags.json      -->  Hugo (index.html)
                                                         +-->  data/stats.json     -->  Hugo (footer.html)

                                        hugo  -->  public/ (sitio estático final)
```

---

## Ejercicios realizados

### Ejercicio 1: Nuevo post con etiqueta SQL
He creado el post `content/posts/sql-en-build-time.md` con etiquetas `[sql, sgbd, hugo]`. Al pasar la indexación, SQLite agrupa las etiquetas con la consulta `Q_TAGS` (`GROUP BY tag`) y muestra el recuento actualizado en la página de inicio.

### Ejercicio 2: Soporte para borradores (--drafts)
`hugo server -D` permite ver los posts en borrador (`draft: true`), pero la búsqueda no los encontraba porque `tools/index.py` los descartaba directamente. He añadido el parámetro `--drafts` al script y la regla `make serve-drafts` en el `Makefile` para poder indexar y probar borradores en local.

### Ejercicio 3: Tabla de recuento de palabras y footer
He añadido una tabla relacional `words(url, n)` al esquema de SQLite. Una función calcula las palabras de cada artículo y una consulta agregada (`SUM` y `AVG`) genera `data/stats.json`. Luego, en `layouts/partials/footer.html` se muestran el total de palabras y posts publicados.

### Ejercicio 4: Ordenar búsqueda por relevancia
He modificado `static/search.js` para que los resultados de búsqueda salgan ordenados de mayor a menor coincidencia, dando más peso a las palabras que aparecen en el título (x3) y en las etiquetas (x2) que en el cuerpo del texto. La función sigue siendo pura y en JavaScript vanilla sin librerías externas.

---

## Comandos para probar el proyecto

```bash
# Comprobar que los JSON generados son correctos
make check

# Compilar el sitio estático en public/
make build

# Arrancar el servidor de desarrollo local
make serve

# Arrancar el servidor incluyendo borradores
make serve-drafts

# Limpiar archivos generados
make clean
```
