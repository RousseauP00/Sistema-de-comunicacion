#!/usr/bin/env python3
import os
import time
import csv
import argparse
from confluent_kafka import Consumer, KafkaError, KafkaException

# Constants
TOPIC       = 'sensor.camera'
OUT_DIR     = 'out_images'
LATENCY_LOG = 'latencies.csv'

def init_log():
    """
    Trunca o crea el CSV de latencias y escribe la cabecera.
    """
    with open(LATENCY_LOG, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'frame',
            'xmin', 'ymin', 'xmax', 'ymax',
            'class',
            'ts_sent', 'ts_recv', 'latency_ms'
        ])

def log_row(frame, xmin, ymin, xmax, ymax, label,
            ts_sent, ts_recv, latency_ms):
    """
    Añade una fila al CSV de latencias.
    """
    with open(LATENCY_LOG, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            frame,
            xmin, ymin, xmax, ymax,
            label,
            ts_sent, ts_recv, latency_ms
        ])

def main():
    # Parsear argumentos
    parser = argparse.ArgumentParser(
        description='Consumer para sensor.camera que limpia el CSV al arrancar'
    )
    parser.add_argument(
        '--bootstrap-servers',
        required=True,
        help='Lista de brokers Kafka, por ejemplo kafka-1:9092,kafka-2:9093'
    )
    args = parser.parse_args()
    bootstrap = args.bootstrap_servers

    # Inicializar CSV y carpeta de salida
    init_log()
    os.makedirs(OUT_DIR, exist_ok=True)

    # Configurar consumer
    c = Consumer({
        'bootstrap.servers': bootstrap,
        'group.id':          'camera-group',
        'auto.offset.reset': 'earliest',
        'fetch.min.bytes':   1,
        'fetch.wait.max.ms': 0,
        'max.partition.fetch.bytes': 5_000_000
    })
    c.subscribe([TOPIC])
    print("Gemelo digital: esperando cámara…")

    try:
        while True:
            msg = c.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            # Extraer key y headers
            frame = msg.key().decode('utf-8') if msg.key() else ''
            hdrs  = dict(msg.headers() or [])

            try:
                xmin    = float(hdrs.get('xmin', b'0').decode())
                ymin    = float(hdrs.get('ymin', b'0').decode())
                xmax    = float(hdrs.get('xmax', b'0').decode())
                ymax    = float(hdrs.get('ymax', b'0').decode())
                label   = hdrs.get('label', b'').decode()
                ts_sent = int(hdrs.get('ts_sent', b'0').decode())
            except Exception:
                # Si falta algún header, lo saltamos
                continue

            ts_recv    = int(time.time() * 1000)
            latency_ms = ts_recv - ts_sent

            # Mostrar y registrar latencia
            print(
                f"[Cámara] frame={frame}, latency={latency_ms} ms, "
                f"bbox=({xmin},{ymin})-({xmax},{ymax}), class={label}",
                flush=True
            )
            log_row(frame, xmin, ymin, xmax, ymax, label,
                    ts_sent, ts_recv, latency_ms)

            # Guardar imagen recibida
            out_path = os.path.join(OUT_DIR, frame)
            with open(out_path, 'wb') as fd:
                fd.write(msg.value())

    except KeyboardInterrupt:
        print("Consumer cámara detenido.")
    finally:
        c.close()

if __name__ == '__main__':
    main()
