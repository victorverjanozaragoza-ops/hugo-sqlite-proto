#!/usr/bin/env python3
"""tools/sqlite2maria.py — base de datos SQLite de Chyrp Lite → volcado SQL para MariaDB.

Filosofía Unix: un filtro. Lee un fichero .sqlite, escribe SQL por la salida
estándar y los avisos por la salida de errores. Quien carga el SQL en MariaDB
es el cliente `mariadb`, no este script (Python no trae un controlador de
MariaDB en la biblioteca estándar, y no hace falta):

  python3 tools/sqlite2maria.py --origen copia.sqlite > build/chyrp.sql
  mariadb -u chyrp -p chyrp < build/chyrp.sql

El volcado NO crea tablas: Chyrp Lite las crea al instalarse sobre MariaDB y
aquí solo se mueven los DATOS. Para que se pueda repetir sin duplicar, cada
tabla se vacía (DELETE) y se rellena (INSERT) dentro de UNA transacción.

  literal, ident, insert_lote, lotes, sentencias_tabla, volcado   (PURAS)
  listar_tablas, leer_tabla, main                                  (efectos)

Solo biblioteca estándar. Límites (a propósito, KISS): sin DDL, sin vistas,
sin disparadores; `sessions` se omite por defecto (son sesiones caducables).
"""
import argparse
import sqlite3
import sys

PREAMBULO = "SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\nSTART TRANSACTION;\n"
EPILOGO = "COMMIT;\nSET FOREIGN_KEY_CHECKS=1;\n"

# --- funciones puras ---------------------------------------------------------

def literal(valor):
    """Valor de Python → literal SQL de MariaDB."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, bytes):
        return "X'" + valor.hex() + "'"
    texto = (str(valor)
             .replace("\\", "\\\\")
             .replace("'", "''")
             .replace("\0", "\\0")
             .replace("\x1a", "\\Z"))
    return "'" + texto + "'"


def ident(nombre):
    """Nombre de tabla o columna entre comillas invertidas: `groups`."""
    return "`" + nombre.replace("`", "``") + "`"


def insert_lote(tabla, columnas, filas):
    """Un solo INSERT con varias filas."""
    cols = ", ".join(ident(c) for c in columnas)
    valores = ",\n".join("(" + ", ".join(literal(v) for v in fila) + ")" for fila in filas)
    return f"INSERT INTO {ident(tabla)} ({cols}) VALUES\n{valores};\n"


def lotes(filas, tamano):
    """[1,2,3,4,5], 2 → [[1,2],[3,4],[5]]"""
    return [filas[i:i + tamano] for i in range(0, len(filas), tamano)]


def sentencias_tabla(tabla, columnas, filas, tamano=100):
    """DELETE seguido de los INSERT de una tabla. Vaciar primero la hace repetible."""
    vaciar = f"DELETE FROM {ident(tabla)};\n"
    return [vaciar] + [insert_lote(tabla, columnas, lote) for lote in lotes(filas, tamano)]


def volcado(tablas, tamano=100):
    """[(nombre, columnas, filas)] → texto SQL completo."""
    cuerpo = []
    for nombre, columnas, filas in tablas:
        cuerpo.append(f"-- {nombre}: {len(filas)} filas\n")
        cuerpo.extend(sentencias_tabla(nombre, columnas, filas, tamano))
    return PREAMBULO + "".join(cuerpo) + EPILOGO

# --- efectos: leer SQLite, escribir en la salida -------------------------------

def listar_tablas(con, excluir):
    consulta = ("SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in con.execute(consulta) if r[0] not in excluir]


def leer_tabla(con, tabla):
    cur = con.execute(f'SELECT * FROM "{tabla}"')
    columnas = [d[0] for d in cur.description]
    return tabla, columnas, cur.fetchall()


def main():
    ap = argparse.ArgumentParser(description="SQLite de Chyrp Lite → SQL para MariaDB")
    ap.add_argument("--origen", required=True, help="fichero .sqlite (mejor una COPIA)")
    ap.add_argument("--excluir", nargs="*", default=["sessions"],
                    help="tablas que no se vuelcan (por defecto: sessions)")
    ap.add_argument("--lote", type=int, default=100, help="filas por INSERT (por defecto 100)")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.origen}?mode=ro", uri=True)  # solo lectura
    tablas = [leer_tabla(con, t) for t in listar_tablas(con, args.excluir)]
    con.close()

    sys.stdout.write(volcado(tablas, args.lote))
    for nombre, _, filas in tablas:
        print(f"sqlite2maria: {nombre:16} {len(filas):5} filas", file=sys.stderr)


if __name__ == "__main__":
    main()
