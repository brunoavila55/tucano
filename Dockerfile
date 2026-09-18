FROM golang:1.23-alpine AS build

WORKDIR /src
RUN apk add --no-cache ca-certificates git

COPY go.mod go.sum* ./
RUN go mod download

COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/api ./cmd/api && \
    CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/worker ./cmd/worker

FROM alpine:3.22

RUN apk add --no-cache ca-certificates su-exec tzdata && \
    addgroup -S tucano && adduser -S -G tucano tucano

WORKDIR /app
COPY --from=build --chown=tucano:tucano /out/api /out/worker ./
COPY --chmod=755 docker/entrypoint-go.sh /usr/local/bin/entrypoint-go

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint-go"]
CMD ["/app/api"]
