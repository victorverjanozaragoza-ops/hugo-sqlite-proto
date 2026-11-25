# Hugo + SQLite (solo en build). Cada objetivo hace una cosa.
.DEFAULT_GOAL := help
.PHONY: index build serve serve-drafts check clean check-invites test migrar maria help

index:   ## Markdown → SQLite → static/search.json + data/tags.json + data/stats.json
	python3 tools/index.py

build: index   ## Genera el sitio estático en public/ (esto es lo que se despliega)
	hugo --gc --minify

serve: index   ## Servidor local con recarga: http://localhost:1313/
	hugo server

serve-drafts:   ## Servidor local con recarga incluyendo borradores (Ejercicio 2)
	python3 tools/index.py --drafts
	hugo server -D

check: index   ## Valida que los JSON generados son JSON de verdad
	python3 -m json.tool static/search.json > /dev/null
	python3 -m json.tool data/tags.json > /dev/null
	python3 -m json.tool data/stats.json > /dev/null
	@echo "check: OK"

clean:   ## Borra todo lo generado (public/, resources/, build/, JSON)
	rm -rf public resources build static/search.json data/tags.json data/stats.json .hugo_build.lock

test:   ## Prueba las funciones puras de tools/migrar.py
	python3 -m unittest discover -s tools -v

migrar:   ## Markdown → SQLite de Chyrp Lite: make migrar DESTINO=/ruta/copia.sqlite [SIMULACRO=1]
	@test -n "$(DESTINO)" || { echo "Uso: make migrar DESTINO=/ruta/copia.sqlite [SIMULACRO=1]"; exit 1; }
	python3 tools/migrar.py --destino "$(DESTINO)" $(if $(SIMULACRO),--simulacro,)

maria:   ## SQLite de Chyrp Lite ──► SQL para MariaDB: make maria ORIGEN=/ruta/blog.sqlite (escribe build/chyrp.sql)
	@test -n "$(ORIGEN)" || { echo "Uso: make maria ORIGEN=/ruta/blog.sqlite"; exit 1; }
	@mkdir -p build
	python3 tools/sqlite2maria.py --origen "$(ORIGEN)" > build/chyrp.sql
	@echo "build/chyrp.sql listo. Cárgalo con: mariadb -u chyrp -p chyrp < build/chyrp.sql"

check-invites:   ## [profesor] Lista invitaciones de colaborador pendientes (gh auth login)
	@gh api user/repository_invitations --jq '.[] | "\(.id)\t\(.repository.full_name)\tinvited_by=\(.invited_by.login)\t\(.created_at)"' \
		| { grep . || echo "Sin invitaciones pendientes."; }

help:   ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
