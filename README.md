# Assignment 3 — Dashboard for Analysis of Consumed Data

Extends the pipeline from Assignments 1-2:

```
Producer -> Topic: aqi_data -> consumer.py -> MongoDB -> dashboard.py (3 live charts)
```

## New files in this assignment

| File | Purpose |
|---|---|
| `consumer.py` | Reads every message from the `aqi_data` Kafka topic, validates it, writes it into MongoDB |
| `dashboard.py` | Flask app serving a live, auto-refreshing dashboard with 3 charts, reading straight from MongoDB |
| `business_insight_writeup.md` | The required business insight write-up, grounded in the actual sample data's numbers |
| `docker-compose.yml` | Updated — now also starts a local MongoDB alongside Kafka + Zookeeper |
| `requirements.txt` | Updated — adds `pymongo` and `flask` |

## About the dashboard tool choice

The assignment allows MongoDB Atlas Charts, Grafana, or "another tool."
This project uses a **custom Flask + Chart.js dashboard** as the "another
tool" option, because Atlas Charts and Grafana both need a cloud account
or extra setup only you can complete. If your course specifically wants
one of those instead:

- **MongoDB Atlas Charts**: point Atlas at the same `aqi_pipeline.readings`
  collection this consumer writes to (you'll need to migrate from local
  MongoDB to an Atlas cluster, or use Atlas's local-to-cloud sync).
- **Grafana**: add a Grafana container to `docker-compose.yml` and use the
  official MongoDB data source plugin against `mongodb:27017`.

Either is a drop-in swap for `dashboard.py` — `consumer.py` and the
MongoDB schema don't need to change either way.

## How to run the whole thing

**1. Install the new dependencies**
```bash
pip install -r requirements.txt
```

**2. Start Kafka + Zookeeper + MongoDB**
```bash
docker compose up -d
```
Wait ~15-20 seconds for everything to be ready.

**3. Start a producer** (in its own terminal)
```bash
python3 aqi_producer.py --delay 0.5
```

**4. Start the consumer** (in another terminal)
```bash
python3 consumer.py
```
You should see "Stored -> city=... aqi=..." lines as messages arrive.

**5. Start the dashboard** (in another terminal)
```bash
python3 dashboard.py
```
Then open **http://localhost:5000** in a browser. All 3 charts populate
from MongoDB and refresh automatically every 10 seconds.

**6. Let it run for a minute or two** before taking your screenshot, so
the trend chart has enough points to actually show a trend line rather
than a single dot per city.

**7. Shut down when done**
```bash
docker compose down
```

## Notes for the write-up

- `consumer.py` rejects malformed records (missing fields, null AQI,
  negative PM2.5) before writing to MongoDB — this is the "cleans data"
  step referenced in the original Assignment 1 pipeline design.
- The dashboard's 3 charts were tested against the actual
  `sample_aqi_data.json` before delivery (aggregation logic verified with
  a mock MongoDB), so the numbers in `business_insight_writeup.md` are
  real outputs of this pipeline, not invented figures.
- If you swap to the live producer (`aqi_producer_live.py`), the same
  consumer and dashboard work unchanged — only the write-up's specific
  numbers would need updating to match a live run.
