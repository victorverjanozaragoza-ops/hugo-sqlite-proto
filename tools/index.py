#!/usr/bin/env python3
"""tools/index.py - content/**/*.md â†’ SQLite (solo en build) â†’ JSON estÃ¡tico.

FilosofÃ­a Unix: hace UNA cosa. Lee Markdown, rellena build/site.db y la
consulta con SQL para exportar tres ficheros:

  static/search.json    lo consume static/search.js en el navegador
  data/tags.json        lo consume Hugo en layouts/index.html
  data/stats.json       lo consume Hugo en layouts/partials/footer.html

La base de datos NO se despliega: public/ contiene solo ficheros estÃ¡ticos.

Solo biblioteca estÃ¡ndar (sqlite3, json, re, pathlib, sys). Estilo funcional:
funciones puras para parsear; los efectos (disco, SQL) quedan al final.

LÃ­mites (a propÃ³sito, KISS): front matter YAML con pares `clave: valor` y
listas en lÃ­nea `tags: [a, b]`. Nada de TOML (+++) ni listas multilÃ­nea.

Docs: https://docs.python.org/3/library/sqlite3.html
      https://www.sqlite.org/json1.html
"""
import json
import re
import sqlite3
import sys
from functools import reduce
from pathlib import Path

CONTENT = Path("content")
DB = Path("build/site.db")
OUT_SEARCH = Path("static/search.json")
OUT_TAGS = Path("data/tags.json")
OUT_STATS = Path("data/stats.json")

SCHEMA = """
CREATE TABLE posts (
  url     TEXT PRIMARY KEY,
  title   TEXT NOT NULL,
  date    TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  body    TEXT NOT NULL DEFAULT ''
);
CREATE TABLE tags (
  url TEXT NOT NULL REFERENCES posts(url),
  tag TEXT NOT NULL,
  PRIMARY KEY (url, tag)
);
CREATE TABLE words (
  url TEXT PRIMARY KEY REFERENCES posts(url),
  n   INTEGER NOT NULL
);
"""

# SQL produce directamente el JSON (extensiÃ³n json1 de SQLite).
Q_SEARCH = """
SELECT json_group_array(json_object(
  'url', url, 'title', title, 'date', date, 'summary', summary,
  'tags', json(tags), 'text', body))
FROM (
  SELECT p.*,
         (SELECT json_group_array(tag) FROM tags t WHERE t.url = p.url) AS tags
  FROM posts p
  ORDER BY date DESC, title
)
"""

# AgregaciÃ³n: cuÃ¡ntas pÃ¡ginas hay por etiqueta.
Q_TAGS = """
SELECT json_group_array(json_object('tag', tag, 'total', total))
FROM (
  SELECT tag, COUNT(*) AS total FROM tags GROUP BY tag ORDER BY total DESC, tag
)
"""

# AgregaciÃ³n: estadÃ­sticas de palabras globales y por post (Ejercicio 3).
Q_STATS = """
SELECT json_object(
  'total_words', COALESCE(SUM(n), 0),
  'avg_words', COALESCE(ROUND(AVG(n), 1), 0),
  'total_posts', COUNT(*)
)
FROM words
"""

# --- funciones puras ---------------------------------------------------------

def split_front_matter(text):
    """'---\nclave: valor\n---\ncuerpo' â†’ (bloque_yaml, cuerpo)."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def parse_scalar(raw):
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        return [parse_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v in ("true", "false"):
        return v == "true"
    return re.sub(r"^(['\"])(.*)\1$", r"\2", v)  # quita comillas simÃ©tricas


def parse_meta(block):
    pairs = (line.split(":", 1) for line in block.splitlines()
             if ":" in line and not line.lstrip().startswith("#"))
    return {k.strip(): parse_scalar(v) for k, v in pairs}


# (patrÃ³n, reemplazo) aplicados en orden: Markdown â†’ texto plano
CLEANERS = [
    (r"```.*?```", " "),                              # bloques de cÃ³digo
    (r"`([^`]*)`", r"\1"),                            # cÃ³digo en lÃ­nea
    (r"!?\[([^\]]*)\]\([^)]*\)", r"\1"),              # enlaces/imÃ¡genes â†’ texto
    (r"^[ \t]{0,3}(?:#{1,6}|>|[-*+]|\d+\.)[ \t]+", ""),  # marcas de bloque
    (r"\*{1,3}", ""),                                 # Ã©nfasis
    (r"\s+", " "),                                    # espacios
]


def plain(markdown):
    step = lambda s, pr: re.sub(pr[0], pr[1], s, flags=re.S | re.M)
    return reduce(step, CLEANERS, markdown).strip()


def shorten(text, n=160):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "."


def count_words(text):
    """FunciÃ³n pura: calcula el total de palabras en el texto plano."""
    return len(re.findall(r"\b[\w\-]+\b", text))


def url_of(path):
    """content/posts/x.md â†’ /posts/x/ (como hace Hugo)."""
    parts = path.relative_to(CONTENT).with_suffix("").parts
    parts = parts[:-1] if parts[-1] == "index" else parts
    return "/" + "/".join(parts) + "/"


def read_page(path):
    front, body = split_front_matter(path.read_text(encoding="utf-8"))
    meta = parse_meta(front)
    text = plain(body)
    tags = meta.get("tags", [])
    return {
        "url": url_of(path),
        "title": meta.get("title", path.stem),
        "date": str(meta.get("date", "")),
        "summary": meta.get("description") or shorten(text),
        "tags": tags if isinstance(tags, list) else [tags],
        "draft": meta.get("draft", False) is True,
        "text": text,
        "words": count_words(text),
    }


def read_all(include_drafts=False):
    """Lee pÃ¡ginas markdown. Si include_drafts es False, filtra borradores (Ejercicio 2)."""
    files = (p for p in sorted(CONTENT.rglob("*.md")) if p.name != "_index.md")
    return [page for page in map(read_page, files) if include_drafts or not page["draft"]]


# --- efectos: disco y SQL ----------------------------------------------------

def build_db(pages):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO posts(url, title, date, summary, body)"
        " VALUES (:url, :title, :date, :summary, :text)", pages)
    con.executemany(
        "INSERT OR IGNORE INTO tags(url, tag) VALUES (?, ?)",
        [(p["url"], t) for p in pages for t in p["tags"]])
    con.executemany(
        "INSERT OR REPLACE INTO words(url, n) VALUES (?, ?)",
        [(p["url"], p["words"]) for p in pages])
    con.commit()
    return con


def export(con, query, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    row = con.execute(query).fetchone()
    content = (row[0] if row and row[0] is not None else "[]") + "\n"
    out.write_text(content, encoding="utf-8")


def main():
    if not CONTENT.is_dir():
        sys.exit("index.py: ejecÃºtalo desde la raÃ­z del repo (make index)")

    include_drafts = "--drafts" in sys.argv
    pages = read_all(include_drafts=include_drafts)
    con = build_db(pages)
    export(con, Q_SEARCH, OUT_SEARCH)
    export(con, Q_TAGS, OUT_TAGS)
    export(con, Q_STATS, OUT_STATS)
    con.close()

    draft_info = " (incluyendo borradores)" if include_drafts else ""
    print(f"index: {len(pages)} pÃ¡ginas{draft_info} â†’ {OUT_SEARCH}, {OUT_TAGS}, {OUT_STATS}")


if __name__ == "__main__":
    main()