.PHONY: dev down logs test test-go test-web check generate

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker web

test: test-go test-web

test-go:
	docker run --rm -v "$(CURDIR):/src" -w /src golang:1.23-alpine go test ./...

test-web:
	cd web && pnpm test && pnpm check && pnpm lint

check:
	docker compose config --quiet

generate:
	docker run --rm -v "$(CURDIR):/src" -w /src sqlc/sqlc:1.29.0 generate

