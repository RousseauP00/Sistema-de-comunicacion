#!/usr/bin/env bash
set -e

PASS=confluent123

# 1) Limpiar viejos artefactos
rm -f ca.key ca.crt ca.srl
rm -f kafka-1.* kafka-2.* truststore.jks

# 2) Generar CA
openssl req -new -x509 -keyout ca.key -out ca.crt \
  -days 365 -passout pass:$PASS \
  -subj "/CN=MyKafkaCA"

# 3) Generar los keystores y luego limpiar intermedios
for HOST in kafka-1 kafka-2; do
  # clave + CSR + cert firmado
  openssl genrsa -out $HOST.key 2048
  openssl req -new -key $HOST.key -out $HOST.csr -subj "/CN=$HOST"
  openssl x509 -req -in $HOST.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out $HOST.crt -days 365 -passin pass:$PASS

  # empaquetar y crear Java keystore
  openssl pkcs12 -export -in $HOST.crt -inkey $HOST.key -certfile ca.crt \
    -name $HOST -out $HOST.p12 -passout pass:$PASS

  keytool -importkeystore \
    -deststorepass $PASS -destkeypass $PASS -destkeystore $HOST.keystore.jks \
    -srckeystore $HOST.p12 -srcstoretype PKCS12 -srcstorepass $PASS \
    -alias $HOST

  # borrar intermedios
  rm -f $HOST.key $HOST.csr $HOST.crt $HOST.p12
done

# 4) Generar truststore (solo la CA)
keytool -import -v -trustcacerts -alias CARoot -file ca.crt \
  -keystore truststore.jks -storepass $PASS -noprompt

# 5) Opcional: borrar serial
rm -f ca.srl

echo "→ Generado:"
echo "   ca.crt, ca.key"
echo "   kafka-1.keystore.jks"
echo "   kafka-2.keystore.jks"
echo "   truststore.jks"
echo "   (contraseña: $PASS)"
