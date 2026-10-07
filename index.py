"""GA0 Q25 telemetry API. Deploy this directory to Vercel."""
import math
import os
from statistics import fmean
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from data import TELEMETRY

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'],
                   allow_methods=['POST', 'GET', 'OPTIONS'],
                   allow_headers=['*'],
                   expose_headers=['Access-Control-Allow-Origin'])


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile95(values):
    ordered = sorted(values)
    if os.getenv('P95_METHOD', 'nearest-rank') == 'linear':
        position = .95 * (len(ordered) - 1)
        lo, hi = math.floor(position), math.ceil(position)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)
    return ordered[math.ceil(.95 * len(ordered)) - 1]


@app.post('/api/latency')
def analytics(request: AnalyticsRequest):
    regions = {}
    for region in request.regions:
        rows = [r for r in TELEMETRY if r['region'] == region]
        if not rows:
            regions[region] = {'avg_latency': 0, 'p95_latency': 0,
                               'avg_uptime': 0, 'breaches': 0}
            continue
        latency = [r['latency_ms'] for r in rows]
        regions[region] = {
            'avg_latency': fmean(latency),
            'p95_latency': percentile95(latency),
            'avg_uptime': fmean(r['uptime_pct'] for r in rows),
            'breaches': sum(value > request.threshold_ms for value in latency),
        }
    return {'regions': regions}


@app.get('/')
def health():
    return {'status': 'ok', 'endpoint': '/api/latency'}
