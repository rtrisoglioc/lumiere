# LUMIÈRE — Grafana Cloud dashboard

Import `lumiere_dashboard.json` into Grafana Cloud:

1. Grafana Cloud → **Dashboards → New → Import**.
2. Upload `lumiere_dashboard.json` (or paste its contents).
3. When prompted, select your **Prometheus (Grafana Cloud)** data source.
4. Save.

## Panels
- **p95 agent duration (ms) by agent** — `histogram_quantile(0.95, sum by (agent, le) (rate(lumiere_agent_duration_ms_bucket[$__rate_interval])))`
- **Agent failure rate (failed / total)** — `sum by (agent) (rate(lumiere_agent_calls_total{status="failed"}[$__rate_interval])) / clamp_min(sum by (agent) (rate(lumiere_agent_calls_total[$__rate_interval])), 1e-9)`
- **Total agent calls (by status)** — `sum by (agent, status) (increase(lumiere_agent_calls_total[$__range]))`
- **Story completeness by experience** — `lumiere_story_completeness` (0-100, per experience_id)

Variables: `datasource` (Prometheus) and `agent` (multi-select, from `label_values(lumiere_agent_calls_total, agent)`).

## Metrics reference (emitted by backend/services/grafana_metrics.py)
| Metric | Type | Labels |
|---|---|---|
| `lumiere_agent_duration_ms` | histogram | `agent` |
| `lumiere_agent_calls_total` | counter | `agent`, `status` |
| `lumiere_agent_confidence` | gauge | `agent` |
| `lumiere_story_completeness` | gauge | `experience_id` |

Agents: `director`, `cinematographer`, `vision`, `evaluator`, `editor`, `render_worker`.

> Note: the token in `backend/.env` is a **write** token (`metrics:write`). To browse/query these metrics
> in Grafana Explore you need a token with **`metrics:read`** scope (or use the Grafana Cloud UI, which
> is already authorized for your stack).
