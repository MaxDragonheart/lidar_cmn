#!/usr/bin/env bash
# Make the certificates of the HTTPS tests, valid for 100 years:
# - root_ca.pem: a root certificate authority;
# - intermediate_ca.pem: an intermediate certificate authority, signed by the root;
# - server.pem and server.key: the certificate of the local server (127.0.0.1,
#   localhost), signed by the intermediate, and its key.
# server.pem contains only the certificate of the server, without the
# intermediate: the server of the tests sends an incomplete chain, as
# sit.cittametropolitana.na.it does. The keys of the two authorities are deleted.
set -euo pipefail

# Git Bash on Windows converts the "/CN=..." subjects to paths; the temporary
# folder has a relative path, which needs no conversion
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"
work=$(mktemp -d ./tmp.XXXXXX)
trap 'rm -rf "$work"' EXIT
days=36500

cat > "$work/openssl.cnf" <<'EOF'
[req]
distinguished_name = dn

[dn]

[root]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash

[intermediate]
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always

[server]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = DNS:localhost, IP:127.0.0.1
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
EOF

serial() {
    echo "0x$(openssl rand -hex 16)"
}

# Root
openssl ecparam -name prime256v1 -genkey -noout -out "$work/root_ca.key"
openssl req -new -x509 -config "$work/openssl.cnf" -extensions root -key "$work/root_ca.key" \
    -subj "/CN=lidar_cmn test root CA" -days "$days" -set_serial "$(serial)" -out root_ca.pem

# Intermediate
openssl ecparam -name prime256v1 -genkey -noout -out "$work/intermediate_ca.key"
openssl req -new -config "$work/openssl.cnf" -key "$work/intermediate_ca.key" \
    -subj "/CN=lidar_cmn test intermediate CA" -out "$work/intermediate_ca.csr"
openssl x509 -req -in "$work/intermediate_ca.csr" -CA root_ca.pem -CAkey "$work/root_ca.key" \
    -set_serial "$(serial)" -days "$days" -extfile "$work/openssl.cnf" -extensions intermediate \
    -out intermediate_ca.pem

# Server
openssl ecparam -name prime256v1 -genkey -noout -out server.key
openssl req -new -config "$work/openssl.cnf" -key server.key -subj "/CN=localhost" -out "$work/server.csr"
openssl x509 -req -in "$work/server.csr" -CA intermediate_ca.pem -CAkey "$work/intermediate_ca.key" \
    -set_serial "$(serial)" -days "$days" -extfile "$work/openssl.cnf" -extensions server \
    -out server.pem

openssl verify -CAfile root_ca.pem -untrusted intermediate_ca.pem server.pem
