# SGBD P1.2: De Hugo + SQLite a Chyrp Lite + SQLite

<p align="center">
  <a href="./practica_sgbd_chyrp_lite.pdf" download>
    <img src="https://img.shields.io/badge/📥_Descargar_Práctica_en_PDF-red?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Descargar PDF" height="40"/>
  </a>
</p>

<p align="center">
  <a href="./practica_sgbd_chyrp_lite.pdf"><b>Descargar o ver la memoria completa en PDF</b></a>
</p>

---

* **Alumno:** Víctor Verjano
* **Curso:** 2º ASIR
* **Módulo:** Sistemas de Gestión de Bases de Datos (SGBD)
* **Práctica:** P1.2 — Migrando el blog: del generador estático a un CMS con SQLite
* **Documento de entrega completo:** [P1.2-verjano.md](./P1.2-verjano.md)

---

## 🎯 Objetivo de la práctica

En la práctica anterior (P1.1), SQLite trabajaba exclusivamente durante la construcción estática del blog (*build time*), generando ficheros JSON consumidos luego por Nginx. En esta práctica damos el salto al modelo de blog dinámico: **la base de datos SQLite pasa a ser el corazón permanente de la aplicación**. 

He instalado **Chyrp Lite** (un CMS minimalista en PHP bajo licencia BSD) configurado con SQLite, y he desarrollado y probado el script ETL (`tools/migrar.py`) que extrae el contenido Markdown del prototipo de Hugo, transforma los datos al modelo EAV y los carga de forma atómica e idempotente en la base de datos de Chyrp Lite.

```text
  PROTOTIPO (P1.1 Hugo)               SCRIPT ETL (tools/migrar.py)            DESTINO (P1.2 Chyrp Lite)
┌───────────────────────┐   extraer   ┌─────────────────────────────┐   cargar   ┌─────────────────────────────┐
│ content/posts/*.md    │ ──────────► │ Transformación PURA:        │ ─────────► │ SQLite: blog.sqlite         │
│ (Front matter + texto)│             │ slugify, fecha, tags JSON   │   INSERT   │ posts + post_attributes     │
└───────────────────────┘             └─────────────────────────────┘            └──────────────┬──────────────┘
                                                                                                │ PHP en cada visita
                                                                   Navegador del visitante ◄────┘
```

---

## 🛠️ Instalación y Datos del Entorno (Parte 1)

* **PHP:** `PHP 8.2.20` con módulos `pdo_sqlite`, `sqlite3`, `mbstring`, `curl` y `xml`.
* **Chyrp Lite:** `v2025.01` instalado en `/home/verjano/chyrp/`.
* **Ruta de la base de datos:** `/home/verjano/chyrp-datos/blog.sqlite`
  > **Nota de seguridad:** Se ubica deliberadamente **fuera** de la carpeta pública de PHP (`~/chyrp/`) para evitar que cualquiera pueda descargar la base de datos completa por URL.
* **Módulo Tags:** Activado desde el panel de administración (*Extend → Modules*).
* **Entradas de prueba iniciales:**
  1. *Bienvenida y pruebas* (etiquetas: `prueba`, `sql`).
  2. *Segunda nota sin etiquetas*.

---

## 🔍 Exploración del Esquema y Modelo EAV (Parte 2)

Al examinar la base de datos con `sqlite3`, Chyrp Lite estructura el contenido en dos tablas principales:

```sql
-- Cabecera y metadatos fijos
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feather VARCHAR(32) NOT NULL,
    clean VARCHAR(128) NOT NULL,
    url VARCHAR(128) NOT NULL,
    pinned BOOLEAN NOT NULL DEFAULT '0',
    status VARCHAR(32) NOT NULL DEFAULT 'public',
    user_id INTEGER NOT NULL,
    created_at DATETIME,
    updated_at DATETIME
);

-- Atributos dinámicos en modelo EAV (Entity-Attribute-Value)
CREATE TABLE post_attributes (
    post_id INTEGER NOT NULL,
    name VARCHAR(128) NOT NULL,
    value LONGTEXT,
    PRIMARY KEY (post_id, name)
);
```

* **Distribución de filas:** Cada post ocupa 1 fila en `posts` y 3 filas en `post_attributes` (`title`, `body` y `tags`).
* **Etiquetas:** No existe una tabla relacional de etiquetas. Se almacenan serializadas en un JSON dentro de `post_attributes` con `name = 'tags'` (ej. `{"prueba":"prueba","sql":"sql"}`). Si el post no tiene etiquetas, guarda `[]`.
* **Fechas:** Formato ISO `YYYY-MM-DD HH:MM:SS`. En entradas no editadas, `updated_at` almacena el valor constante centinela `1000-01-01 00:00:00` (`SQL_DATETIME_ZERO`).

---

## 🔄 Tabla de Correspondencia entre Esquemas (Parte 3)

| Prototipo Hugo (P1.1) | -> | Chyrp Lite (Tabla / Atributo) | Transformación realizada |
| :--- | :---: | :--- | :--- |
| **Título (`title`)** | -> | `post_attributes(name='title')` | Copia directa como texto. |
| **Cuerpo (`cuerpo` de `.md`)** | -> | `post_attributes(name='body')` | Copia directa en Markdown (Chyrp Lite lo renderiza de forma nativa). |
| **Fecha (`date`)** | -> | `posts.created_at` | Normalización con `fecha_chyrp()` a `YYYY-MM-DD HH:MM:SS`. |
| **Nombre fichero (`.stem`)** | -> | `posts.clean` y `posts.url` | Sanitización mediante `slugify()` (sin tildes, minúsculas, guiones). |
| **Descripción (`summary`)** | -> | *Sin equivalente* | Se omite (Chyrp Lite lo genera al vuelo). |
| **Etiquetas (`tags`)** | -> | `post_attributes(name='tags')` | Lista de etiquetas convertida a JSON asociativo `{tag: slug}` o `[]`. |
| **Borrador (`draft: true`)** | -> | `posts.status` | Si `draft` es `true` se asigna `'draft'`; si no, `'public'`. |
| **Autor** | -> | `posts.user_id` | Se asocia al ID del usuario administrador en la tabla `users`. |
| **Valores por defecto** | -> | `feather='text'`, `pinned=0`, `updated_at='1000-01-01 00:00:00'` | Valores fijos del motor. |

---

## 🚀 Arquitectura ETL y Ejecución (Partes 4 y 5)

El script `tools/migrar.py` está diseñado separando la lógica pura de los efectos de disco y SQL:

```text
extraer() [disco] ──► transformar() [PURA: sin efectos] ──► cargar() [SQL transaccional]
```

### 1. Pruebas unitarias
He ampliado `tools/test_migrar.py` para probar todas las funciones puras sin necesidad de base de datos:
```bash
make test
# Ran 13 tests in 0.003s -- OK
```

### 2. Ejecución simulada y real (Demostración de Idempotencia)
```bash
# 1. Simulacro (sin modificar nada en la base de datos):
make migrar DESTINO=$HOME/chyrp-datos/copia.sqlite SIMULACRO=1
# Salida: simulada para todas las entradas

# 2. Migración real (transacción atómica):
make migrar DESTINO=$HOME/chyrp-datos/copia.sqlite
# Salida: creada (5 entradas insertadas)

# 3. Segunda ejecución (Idempotencia):
make migrar DESTINO=$HOME/chyrp-datos/copia.sqlite
# Salida: omitida (0 duplicados, respeta lo que ya estaba)
```

---

## 📊 Verificación y Consultas SQL (Parte 6)

```sql
sqlite> SELECT COUNT(*) FROM posts;
7  -- (2 entradas iniciales + 5 migradas)

sqlite> SELECT p.id, p.clean, p.status, a.value AS titulo
   ...> FROM posts p JOIN post_attributes a ON a.post_id = p.id AND a.name = 'title'
   ...> ORDER BY p.id;
1 | bienvenida-etiquetas  | public | Bienvenida y pruebas
2 | nota-sin-etiquetas    | public | Segunda nota sin etiquetas
3 | borrador              | draft  | Entrada en Borrador
4 | busqueda-sin-servidor | public | Búsqueda sin servidor
5 | hola-hugo             | public | Hola, Hugo
6 | sql-en-build-time     | public | SQL en tiempo de compilación
7 | sqlite-en-build-time  | public | SQLite en tiempo de construcción

-- Comprobación de entradas con etiqueta "static":
sqlite> SELECT COUNT(*) FROM post_attributes WHERE name = 'tags' AND value LIKE '%:"static"%';
2
```

* **Comprobación web:** Como visitante anónimo, la entrada `borrador` queda oculta (error 404), las entradas públicas conservan su Markdown (listas, negritas, bloques de código) y el filtrado por etiquetas en `/?action=tag&name=static` muestra exactamente las 2 entradas correspondientes.

---

## 💡 Ejercicios Resueltos

1. **Ejercicio 1: Romper la transacción a propósito.**
   Introduciendo un `raise RuntimeError` en el 3.er post, el bloque `with con:` ejecuta un `ROLLBACK` automático. No queda ninguna entrada a medias ni atributos huérfanos. Al probarlo sin `with con:`, quedan registros parciales e inconsistentes, evidenciando el principio de Atomicidad (ACID).
2. **Ejercicio 2: Migración de páginas estáticas (`content/about.md`).**
   Ampliación de `tools/migrar.py` con `transformar_pagina()` y `cargar_paginas()` para insertar páginas fijas en la tabla `pages` de Chyrp Lite, incluyendo pruebas unitarias en `test_migrar.py`.
3. **Ejercicio 6: Informe de etiquetas (Comparativa SQL).**
   * *Prototipo normalizado:* `SELECT tag, COUNT(*) FROM tags GROUP BY tag;` (rápido, indexable, 1FN).
   * *Chyrp Lite EAV:* Requiere `json_each()`:
     ```sql
     SELECT json_each.key AS tag, COUNT(*) AS total
     FROM post_attributes, json_each(post_attributes.value)
     WHERE name = 'tags'
     GROUP BY json_each.key;
     ```
     Demuestra cómo el modelo EAV penaliza las consultas de agregación analítica frente al diseño relacional clásico.

---

## 📁 Archivos principales del repositorio

* [`tools/migrar.py`](./tools/migrar.py): Script de migración ETL modular y transaccional.
* [`tools/test_migrar.py`](./tools/test_migrar.py): Banco de pruebas unitarias para funciones puras.
* [`Makefile`](./Makefile): Automatización con objetivos `make test` y `make migrar`.
* [`P1.2-verjano.md`](./P1.2-verjano.md): Memoria técnica detallada de la práctica.
* [`practica_sgbd_chyrp_lite.pdf`](./practica_sgbd_chyrp_lite.pdf): Documento PDF generado para entrega.
