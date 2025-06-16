# scripts/init_topics.ps1

$broker = 'localhost:9092'

docker exec -it kafka-1 bash -c "kafka-topics --bootstrap-server $broker --create --topic sensor.labels  --partitions 3 --replication-factor 2 --if-not-exists"
docker exec -it kafka-1 bash -c "kafka-topics --bootstrap-server $broker --create --topic sensor.images  --partitions 3 --replication-factor 2 --if-not-exists"

Write-Host 'Topics creados: sensor.labels, sensor.images'