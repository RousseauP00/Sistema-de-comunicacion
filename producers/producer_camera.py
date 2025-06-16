#!/usr/bin/env python3
import csv, time, os
from confluent_kafka import Producer

INTERVAL_S = 1.0 / 30.0  # 30 fps aprox.
TOPIC      = 'sensor.camera'
LATENCY_LOG = 'latencies.csv'

def make_producer(bootstrap):
    return Producer({
        'bootstrap.servers':       bootstrap,
        'client.id':               'vehicle-camera',
        'acks':                    '1',      # sólo líder
        'linger.ms':               0,
        'queue.buffering.max.ms':  1,
        'socket.nagle.disable':    True
})


def warm_up(p: Producer) -> int:
    """Envía mensaje vacío para forzar metadata + handshake."""
    start = time.time() * 1000
    p.produce(TOPIC, key='warmup', value=b'')
    p.flush()
    return int(time.time() * 1000 - start)

def delivery_report(err, msg):
    if err:
        print(f"ERROR envío cámara: {err}", flush=True)
    else:
        print(f"OK offset {msg.offset()}", flush=True)

def load_data():
    with open('labels_trainval.csv', newline='') as f:
        reader = csv.reader(f); next(reader)
        labels = list(reader)
    images = sorted(fn for fn in os.listdir('images')
                    if fn.lower().endswith(('.jpg','.png')))
    return labels, images

def main():
    import sys
    bootstrap = sys.argv[1] if len(sys.argv)>1 else 'kafka-1:9092'
    p = make_producer(bootstrap)
    warm_ms = warm_up(p)
    print(f"✅ Warm-up completado en {warm_ms} ms")

    # Prompt interactivo
    resp = input("¿Empezar envío? [s/N]: ").strip().lower()
    if resp != 's':
        print("✋ Envío cancelado."); return

    labels, images = load_data()
    n = min(len(labels), len(images))
    idx = 0

    # Inicializa CSV
    if not os.path.exists(LATENCY_LOG):
        with open(LATENCY_LOG, 'w', newline='') as f:
            csv.writer(f).writerow(
                ['frame','xmin','ymin','xmax','ymax','class','ts_sent','ts_recv','latency_ms']
            )

    try:
        while True:
            frame, xmin, xmax, ymin, ymax, label = labels[idx]
            img_path = os.path.join('images', images[idx])
            with open(img_path, 'rb') as f: img_bytes = f.read()

            ts_sent = int(time.time() * 1000)
            hdrs = [
                ('xmin', xmin.encode()),
                ('xmax', xmax.encode()),
                ('ymin', ymin.encode()),
                ('ymax', ymax.encode()),
                ('label', label.encode()),
                ('ts_sent', str(ts_sent).encode())
            ]

            p.produce(TOPIC, key=frame, value=img_bytes, headers=hdrs,
                      callback=delivery_report)
            p.poll(0)

            # log latencia local
            ts_recv = int(time.time() * 1000)
            lat = ts_recv - ts_sent
            with open(LATENCY_LOG, 'a', newline='') as f:
                csv.writer(f).writerow(
                    [frame, xmin, ymin, xmax, ymax, label, ts_sent, ts_recv, lat]
                )

            idx = (idx + 1) % n
            time.sleep(INTERVAL_S)

    except KeyboardInterrupt:
        print("\n🛑 Envío detenido por el usuario.")
    finally:
        p.flush()

if __name__ == '__main__':
    main()
