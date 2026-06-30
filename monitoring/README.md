# LogoForge AI Monitoring

This folder contains the stakeholder-facing Grafana dashboard for the current Prometheus metrics exposed by the app and workers.

## Dashboard

- Import [monitoring/grafana/dashboards/logoforge-stakeholder-dashboard.json](./grafana/dashboards/logoforge-stakeholder-dashboard.json) into Grafana.
- Map the `DS_PROMETHEUS` datasource variable to your Prometheus instance during import.
- The dashboard uses the metrics exposed by the backend and workers:
  - `logoforge_generation_requests_total`
  - `logoforge_generation_latency_seconds`
  - `logoforge_r2_upload_latency_seconds`
  - `logoforge_errors_total`
  - `logoforge_job_retries_total`
  - `logoforge_dlq_jobs_total`
  - `logoforge_queue_depth`
  - `logoforge_worker_max_jobs`
  - `logoforge_component_ready`
  - `logoforge_generation_cost_usd_total` *(Phase 3 / P3.2 — cost tracking)*
  - `logoforge_moderation_blocked_total` *(Phase 3 / P3.1 — content safety)*

## Stakeholder View

The dashboard is organised around seven panels covering six operational questions:

- **Traffic** — how many logo generation requests the system is handling
- **Readiness** — whether Redis, Postgres, OpenAI, Gemini, and the API are healthy
- **Latency** — how long generations and R2 uploads take (p50 and p95)
- **Capacity** — whether workers are overloaded or near their concurrency limits
- **Reliability** — how often jobs fail, retry, or hit the dead-letter queue
- **Cost** — cumulative and hourly estimated spend by generator (currencyUSD)
- **Safety** — content moderation blocks per hour, broken down by category

## Suggested Use

| Audience | Focus panels |
|---|---|
| Executive / Stakeholder | Traffic, Reliability, Cost |
| Operations / On-call | Latency, Readiness, Capacity, Reliability |
| Product / Growth | Traffic, Cost, Safety |
| Compliance / Legal | Safety (moderation blocks), Cost |

## Alert Recommendations

The following Prometheus recording rules / alert thresholds are worth configuring once Grafana Alerting is enabled:

```yaml
# Hourly generation cost exceeds $5 — possible runaway load or abuse
- alert: HighGenerationCost
  expr: sum(rate(logoforge_generation_cost_usd_total[1h])) * 3600 > 5
  for: 10m

# Moderation block rate exceeds 10/hour — possible coordinated abuse attempt
- alert: ModerationSpikeDetected
  expr: sum(rate(logoforge_moderation_blocked_total[1h])) * 3600 > 10
  for: 5m

# Error rate exceeds 5% of requests
- alert: HighErrorRate
  expr: |
    rate(logoforge_errors_total[5m])
    / rate(logoforge_generation_requests_total[5m]) > 0.05
  for: 10m

# Any core component not ready for more than 2 minutes
- alert: ComponentDown
  expr: logoforge_component_ready == 0
  for: 2m
```
