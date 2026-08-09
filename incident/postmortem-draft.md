# Postmortem (Draft) — Checkout Timeouts, 2026-07-14

**Status:** Draft — root cause still being confirmed
**Author:** on-call engineer
**Severity:** SEV-2

## Summary

Starting at approximately 03:14 UTC on 2026-07-14, checkout requests began
timing out for a subset of users. Elevated error rates continued for roughly
40 minutes before recovering on their own around 03:55 UTC. No manual
intervention was performed during the window; traffic and error rates
returned to normal without a restart or rollback.

## Timeline

- 03:14 UTC — First alerts fire for elevated `/orders/checkout` latency (p99 > 15s).
- 03:18 UTC — On-call engineer paged, begins investigation.
- 03:25 UTC — Checkout error rate climbs to ~22%, mostly `409` and request
  timeouts.
- 03:40 UTC — Database connection count checked; no signs of pool exhaustion,
  active connections stayed within normal range.
- 03:55 UTC — Error rate returns to baseline. No changes were deployed during
  this window.

## What we checked

- **Recent deploys:** The most recent deploy to `main` was 14 hours prior to
  the incident and only touched the order confirmation email template. Ruled
  out as unrelated to checkout latency.
- **Database load:** Postgres CPU and active connection count were both
  within normal operating range throughout the incident window.
- **Application logs:** Checkout requests were seen hanging while waiting on
  the idempotency lock step, not on the database write itself.

## Leading hypothesis

Our current working theory is application-level thread starvation under the
ASGI worker pool — specifically, that a burst of concurrent checkout requests
exhausted available async workers, causing requests to queue and eventually
time out. This would explain why requests were seen hanging before reaching
the database, and why the issue self-resolved once the request burst
subsided.

We have not yet been able to reproduce this under synthetic load, and worker
pool metrics from the incident window do not show workers at capacity, so
this remains unconfirmed.

## Open questions

- Why did worker pool metrics not show saturation if this is a worker
  starvation issue?
- Could something upstream of the application (cache layer, network) have
  caused requests to hang before they reached application code?

## Status

Root cause **not yet confirmed**. Filing this draft to unblock the SEV
retro; will update once we have a confirmed root cause.
