"""OTel tracer setup + a thin span helper that stamps per-span CPU time.

Why a helper instead of importing OTel directly: ``span()`` records the
``cpu_time_s`` attribute that OTel SDK won't compute on its own.
Everything else is plain OTel.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"


def setup_tracer(otlp_endpoint: str | None = None):
    """Configure the global OTel TracerProvider.

    Endpoint precedence: argument > $OTEL_EXPORTER_OTLP_ENDPOINT > localhost:4317.
    Returns the TracerProvider so the caller can flush/shutdown on exit.

    Note: we deliberately do NOT install HTTPXClientInstrumentor — that would
    create a duplicate POST span next to every llm_request. workflow.py uses
    ``inject_traceparent_headers()`` instead to propagate trace context across
    to sglang without the extra span.
    """
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    endpoint = (
        otlp_endpoint
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or DEFAULT_OTLP_ENDPOINT
    )
    provider = TracerProvider(resource=Resource.create({"service.name": "bank-agent"}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)
    return provider


def inject_traceparent_headers() -> dict:
    """Build HTTP headers carrying the W3C trace context of the current span.

    Pass to OpenAI client as ``extra_headers=...`` so sglang server can read
    the ``traceparent`` and parent its own spans under our ``llm_request``.
    """
    from opentelemetry.propagate import inject
    headers: dict = {}
    inject(headers)
    return headers


@contextmanager
def span(name: str, kind: str, **attrs):
    """Open an OTel span and stamp ``cpu_time_s`` on close.

    ``kind`` is stored as ``tiny_gym.kind`` so the dashboard can group by it.
    Wall time is already on the span as OTel's native ``Duration`` field.
    """
    from opentelemetry import trace
    cpu_start = os.times()
    tracer = trace.get_tracer("tiny_gym")
    with tracer.start_as_current_span(
        name, attributes={"tiny_gym.kind": kind, **attrs}
    ) as s:
        try:
            yield s
        finally:
            cpu = (os.times().user + os.times().system) - (cpu_start.user + cpu_start.system)
            s.set_attribute("cpu_time_s", round(cpu, 6))
