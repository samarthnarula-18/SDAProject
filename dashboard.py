"""
dashboard.py
-------------
Live dashboard for Assignment 3.

Serves a single page with 3 auto-refreshing charts built from the data
consumer.py has written into MongoDB:

  1. AQI trend over time, one line per city
  2. Average AQI by city (bar)
  3. AQI category distribution across all readings (donut)

This is the "another tool" option (a lightweight custom dashboard) rather
than MongoDB Atlas Charts or Grafana, since both of those require a cloud
account only you can create. If your course wants a specific one of those
tools instead, see the README for how to point them at the same MongoDB
collection this script reads from.

Usage:
    python3 dashboard.py
    Then open http://localhost:5000 in a browser.
"""

import argparse

from flask import Flask, jsonify, render_template_string
from pymongo import MongoClient

app = Flask(__name__)

DB_NAME = "aqi_pipeline"
COLLECTION_NAME = "readings"

CATEGORY_ORDER = [
    "Good",
    "Moderate",
    "Unhealthy for Sensitive Groups",
    "Unhealthy",
    "Very Unhealthy",
    "Hazardous",
]

mongo_client = None
collection = None


def get_trend_data(limit_per_city: int = 30):
    """Latest N readings per city, for the AQI-over-time line chart."""
    pipeline = [
        {"$sort": {"timestamp": 1}},
        {
            "$group": {
                "_id": "$city",
                "points": {
                    "$push": {"timestamp": "$timestamp", "aqi": "$aqi"}
                },
            }
        },
    ]
    results = list(collection.aggregate(pipeline))
    series = {}
    for r in results:
        series[r["_id"]] = r["points"][-limit_per_city:]
    return series


def get_avg_aqi_by_city():
    pipeline = [
        {"$group": {"_id": "$city", "avg_aqi": {"$avg": "$aqi"}}},
        {"$sort": {"avg_aqi": -1}},
    ]
    results = list(collection.aggregate(pipeline))
    return {r["_id"]: round(r["avg_aqi"], 1) for r in results}


def get_category_distribution():
    pipeline = [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
    results = list(collection.aggregate(pipeline))
    counts = {r["_id"]: r["count"] for r in results}
    # Return in a fixed, meaningful order (Good -> Hazardous) rather than
    # whatever order Mongo happens to return
    return {cat: counts.get(cat, 0) for cat in CATEGORY_ORDER if counts.get(cat, 0) > 0}


@app.route("/api/summary")
def api_summary():
    return jsonify({
        "trend": get_trend_data(),
        "avg_by_city": get_avg_aqi_by_city(),
        "category_distribution": get_category_distribution(),
        "total_readings": collection.count_documents({}),
    })


PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AQI Streaming Dashboard</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    body { font-family: Arial, sans-serif; background: #0f1117; color: #e6e6e6; margin: 0; padding: 24px; }
    h1 { font-size: 22px; margin-bottom: 4px; }
    .subtitle { color: #9aa0ab; margin-bottom: 24px; font-size: 13px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .card { background: #171a21; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.4); }
    .card.full { grid-column: 1 / -1; }
    .card h2 { font-size: 15px; margin: 0 0 12px 0; color: #d6d9de; }
    canvas { max-height: 320px; }
    .stat { font-size: 13px; color: #9aa0ab; margin-top: 24px; }
  </style>
</head>
<body>
  <h1>AQI Streaming Pipeline — Live Dashboard</h1>
  <div class="subtitle">Auto-refreshes every 10s from MongoDB (populated by consumer.py)</div>

  <div class="grid">
    <div class="card full">
      <h2>AQI Trend Over Time (per city)</h2>
      <canvas id="trendChart"></canvas>
    </div>
    <div class="card">
      <h2>Average AQI by City</h2>
      <canvas id="cityChart"></canvas>
    </div>
    <div class="card">
      <h2>AQI Category Distribution</h2>
      <canvas id="categoryChart"></canvas>
    </div>
  </div>

  <div class="stat" id="statLine">Loading...</div>

  <script>
    const palette = ["#4dabf7", "#ff8787", "#69db7c", "#ffd43b", "#b197fc", "#63e6be"];

    const trendChart = new Chart(document.getElementById('trendChart'), {
      type: 'line',
      data: { datasets: [] },
      options: {
        responsive: true,
        scales: {
          x: { type: 'category', ticks: { color: '#9aa0ab' } },
          y: { ticks: { color: '#9aa0ab' }, title: { display: true, text: 'AQI', color: '#9aa0ab' } }
        },
        plugins: { legend: { labels: { color: '#e6e6e6' } } }
      }
    });

    const cityChart = new Chart(document.getElementById('cityChart'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Avg AQI', data: [], backgroundColor: '#4dabf7' }] },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: '#9aa0ab' } },
          y: { ticks: { color: '#9aa0ab' } }
        },
        plugins: { legend: { display: false } }
      }
    });

    const categoryChart = new Chart(document.getElementById('categoryChart'), {
      type: 'doughnut',
      data: { labels: [], datasets: [{ data: [], backgroundColor: palette }] },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { color: '#e6e6e6' } } }
      }
    });

    async function refresh() {
      const res = await fetch('/api/summary');
      const data = await res.json();

      // Trend chart
      const cities = Object.keys(data.trend);
      const allTimestamps = [...new Set(cities.flatMap(c => data.trend[c].map(p => p.timestamp)))].sort();
      trendChart.data.labels = allTimestamps.map(t => t.slice(11, 19));
      trendChart.data.datasets = cities.map((city, i) => {
        const byTs = Object.fromEntries(data.trend[city].map(p => [p.timestamp, p.aqi]));
        return {
          label: city,
          data: allTimestamps.map(t => byTs[t] ?? null),
          borderColor: palette[i % palette.length],
          backgroundColor: palette[i % palette.length],
          spanGaps: true,
          tension: 0.25,
        };
      });
      trendChart.update();

      // City bar chart
      cityChart.data.labels = Object.keys(data.avg_by_city);
      cityChart.data.datasets[0].data = Object.values(data.avg_by_city);
      cityChart.update();

      // Category donut
      categoryChart.data.labels = Object.keys(data.category_distribution);
      categoryChart.data.datasets[0].data = Object.values(data.category_distribution);
      categoryChart.update();

      document.getElementById('statLine').textContent =
        `Total readings stored: ${data.total_readings} | Last refreshed: ${new Date().toLocaleTimeString()}`;
    }

    refresh();
    setInterval(refresh, 10000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE_TEMPLATE)


def main():
    global mongo_client, collection

    parser = argparse.ArgumentParser(description="AQI live dashboard.")
    parser.add_argument(
        "--mongo-uri", default="mongodb://localhost:27017", help="MongoDB connection URI"
    )
    parser.add_argument("--port", type=int, default=5000, help="Port to serve the dashboard on")
    args = parser.parse_args()

    mongo_client = MongoClient(args.mongo_uri)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]

    print(f"Dashboard running at http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
