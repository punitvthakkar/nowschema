"""
Observability service using Grafana Cloud.
Handles metrics collection, logging, and alerting.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import time

try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class Metric:
    """A metric data point."""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime


class ObservabilityService:
    """Service for observability using Grafana Cloud."""

    def __init__(
        self,
        grafana_api_key: str,
        grafana_endpoint: str,
        service_name: str = "uniclass-api",
    ):
        """
        Initialize observability service.

        Args:
            grafana_api_key: Grafana Cloud API key
            grafana_endpoint: Grafana Cloud endpoint URL
            service_name: Name of the service for labeling
        """
        if httpx is None:
            raise RuntimeError("httpx not available")

        self.api_key = grafana_api_key
        self.endpoint = grafana_endpoint.rstrip("/")
        self.service_name = service_name
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {grafana_api_key}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        self._metrics_buffer: list = []
        self._buffer_size = 100

    # ==================== METRICS ====================

    async def record_metric(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None,
    ) -> None:
        """
        Record a metric data point.

        Args:
            name: Metric name (e.g., "api_requests_total")
            value: Metric value
            labels: Additional labels for the metric
        """
        metric = Metric(
            name=f"{self.service_name}_{name}",
            value=value,
            labels={
                "service": self.service_name,
                **(labels or {}),
            },
            timestamp=datetime.now(timezone.utc),
        )
        self._metrics_buffer.append(metric)

        # Flush if buffer is full
        if len(self._metrics_buffer) >= self._buffer_size:
            await self.flush_metrics()

    async def flush_metrics(self) -> None:
        """Flush buffered metrics to Grafana Cloud."""
        if not self._metrics_buffer:
            return

        try:
            # Convert to Prometheus format
            lines = []
            for metric in self._metrics_buffer:
                labels_str = ",".join(
                    f'{k}="{v}"' for k, v in metric.labels.items()
                )
                timestamp_ms = int(metric.timestamp.timestamp() * 1000)
                lines.append(f"{metric.name}{{{labels_str}}} {metric.value} {timestamp_ms}")

            payload = "\n".join(lines)

            await self._client.post(
                f"{self.endpoint}/api/v1/push",
                content=payload,
                headers={"Content-Type": "text/plain"},
            )
            self._metrics_buffer.clear()
        except Exception as e:
            print(f"Failed to flush metrics: {e}")

    # ==================== COMMON METRICS ====================

    async def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        tenant_id: str = None,
    ) -> None:
        """Record an API request metric."""
        labels = {
            "endpoint": endpoint,
            "method": method,
            "status": str(status_code),
        }
        if tenant_id:
            labels["tenant_id"] = tenant_id

        await self.record_metric("requests_total", 1, labels)
        await self.record_metric("request_duration_ms", latency_ms, labels)

    async def record_cache_operation(
        self,
        operation: str,  # "hit" or "miss"
        endpoint: str,
    ) -> None:
        """Record a cache operation metric."""
        await self.record_metric(
            "cache_operations_total",
            1,
            {"operation": operation, "endpoint": endpoint},
        )

    async def record_rate_limit(
        self,
        tenant_id: str,
        allowed: bool,
    ) -> None:
        """Record a rate limit check."""
        await self.record_metric(
            "rate_limit_checks_total",
            1,
            {"tenant_id": tenant_id, "allowed": str(allowed).lower()},
        )

    async def record_quota_usage(
        self,
        tenant_id: str,
        used: int,
        limit: int,
    ) -> None:
        """Record quota usage."""
        await self.record_metric(
            "quota_used",
            used,
            {"tenant_id": tenant_id},
        )
        await self.record_metric(
            "quota_limit",
            limit,
            {"tenant_id": tenant_id},
        )

    async def record_search_latency(
        self,
        latency_ms: float,
        cache_hit: bool,
    ) -> None:
        """Record search latency."""
        await self.record_metric(
            "search_latency_ms",
            latency_ms,
            {"cache_hit": str(cache_hit).lower()},
        )

    # ==================== LOGGING ====================

    async def log(
        self,
        level: str,
        message: str,
        extra: Dict[str, Any] = None,
    ) -> None:
        """
        Send a log entry to Grafana Loki.

        Args:
            level: Log level (info, warn, error)
            message: Log message
            extra: Additional structured data
        """
        try:
            timestamp_ns = int(time.time() * 1e9)
            log_entry = {
                "streams": [
                    {
                        "stream": {
                            "service": self.service_name,
                            "level": level,
                        },
                        "values": [
                            [
                                str(timestamp_ns),
                                json.dumps({
                                    "message": message,
                                    "level": level,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    **(extra or {}),
                                }),
                            ]
                        ],
                    }
                ]
            }

            await self._client.post(
                f"{self.endpoint}/loki/api/v1/push",
                json=log_entry,
            )
        except Exception as e:
            print(f"Failed to send log: {e}")

    async def log_info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        await self.log("info", message, kwargs)

    async def log_warn(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        await self.log("warn", message, kwargs)

    async def log_error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        await self.log("error", message, kwargs)

    # ==================== ALERTING ====================

    async def send_alert(
        self,
        alert_name: str,
        message: str,
        severity: str = "warning",
        labels: Dict[str, str] = None,
    ) -> None:
        """
        Send an alert to Grafana Alerting.

        Args:
            alert_name: Name of the alert
            message: Alert message
            severity: Alert severity (info, warning, critical)
            labels: Additional labels
        """
        try:
            alert = {
                "alertname": alert_name,
                "service": self.service_name,
                "severity": severity,
                "message": message,
                **(labels or {}),
            }

            # This would integrate with Grafana Alerting API
            await self.log_warn(f"Alert: {alert_name}", alert=alert, severity=severity)

        except Exception as e:
            print(f"Failed to send alert: {e}")

    # ==================== CLEANUP ====================

    async def close(self) -> None:
        """Close the HTTP client and flush remaining metrics."""
        await self.flush_metrics()
        await self._client.aclose()


class NoOpObservabilityService:
    """No-op implementation when Grafana is not configured."""

    async def record_metric(self, *args, **kwargs) -> None:
        pass

    async def flush_metrics(self) -> None:
        pass

    async def record_request(self, *args, **kwargs) -> None:
        pass

    async def record_cache_operation(self, *args, **kwargs) -> None:
        pass

    async def record_rate_limit(self, *args, **kwargs) -> None:
        pass

    async def record_quota_usage(self, *args, **kwargs) -> None:
        pass

    async def record_search_latency(self, *args, **kwargs) -> None:
        pass

    async def log(self, *args, **kwargs) -> None:
        pass

    async def log_info(self, *args, **kwargs) -> None:
        pass

    async def log_warn(self, *args, **kwargs) -> None:
        pass

    async def log_error(self, *args, **kwargs) -> None:
        pass

    async def send_alert(self, *args, **kwargs) -> None:
        pass

    async def close(self) -> None:
        pass
