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

## Stakeholder View

The dashboard is organized around five questions:

- Traffic: how many logo generation requests the system is handling
- Latency: how long generations and R2 uploads take
- Reliability: how often jobs fail, retry, or hit the DLQ
- Readiness: whether Redis, Postgres, and the API are healthy
- Capacity: whether workers are overloaded or near limits

## Suggested Use

- Exec view: show reliability and throughput
- Ops view: show errors, queue depth, latency, and health
- Product view: show request volume and successful completions

