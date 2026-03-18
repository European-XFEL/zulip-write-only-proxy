#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="certs"

mkdir -p "$CERT_DIR"

rm -f "$CERT_DIR"/ca.key "$CERT_DIR"/ca.crt "$CERT_DIR"/ca.srl
rm -f "$CERT_DIR"/server.key "$CERT_DIR"/server.crt "$CERT_DIR"/server.csr
rm -f "$CERT_DIR"/client.key "$CERT_DIR"/client.crt "$CERT_DIR"/client.csr

openssl genrsa -out "$CERT_DIR/ca.key" 4096
openssl req -x509 -new -nodes \
  -key "$CERT_DIR/ca.key" \
  -sha256 \
  -days 3650 \
  -out "$CERT_DIR/ca.crt" \
  -addext "keyUsage = digitalSignature, keyEncipherment, dataEncipherment, cRLSign, keyCertSign" -addext "extendedKeyUsage = serverAuth, clientAuth" \
  -subj "/CN=zwop-local-ca"

openssl genrsa -out "$CERT_DIR/server.key" 2048
openssl req -new \
  -key "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.csr" \
  -subj "/CN=token-writer"
openssl x509 -req \
  -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" \
  -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/server.crt" \
  -days 825 \
  -sha256 \
  -extfile <(printf "subjectAltName=DNS:localhost,DNS:max-exfl463.desy.de,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n")

openssl genrsa -out "$CERT_DIR/client.key" 2048
openssl req -new \
  -key "$CERT_DIR/client.key" \
  -out "$CERT_DIR/client.csr" \
  -subj "/CN=zwop-service"
openssl x509 -req \
  -in "$CERT_DIR/client.csr" \
  -CA "$CERT_DIR/ca.crt" \
  -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/client.crt" \
  -days 825 \
  -sha256 \
  -extfile <(printf "extendedKeyUsage=clientAuth\n")

rm -f "$CERT_DIR/server.csr" "$CERT_DIR/client.csr" "$CERT_DIR/ca.srl"

echo "mTLS certificates generated in $CERT_DIR"
