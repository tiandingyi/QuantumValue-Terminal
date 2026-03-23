FROM golang:1.23-alpine AS build

WORKDIR /app

COPY services/go-gateway/go.mod ./
RUN go mod download

COPY services/go-gateway ./
RUN go build -o /bin/api-go ./cmd/api

FROM alpine:3.21

WORKDIR /app

COPY --from=build /bin/api-go /usr/local/bin/api-go

EXPOSE 8080

CMD ["api-go"]
