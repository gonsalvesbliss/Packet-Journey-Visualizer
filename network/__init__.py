"""Member 1 network data collection package."""

from .models import Hop, NetworkData
from .ping import parse_ping_output, ping_host
from .resolver import ResolutionError, resolve, resolve_domain
from .traceroute import TracerouteError, parse_tracert_output, traceroute


def collect_network_data(destination: str) -> dict:
    """Collect DNS, ping, and traceroute data without analysis statistics."""

    resolution = resolve_domain(destination)
    if resolution["resolved_ip"] is None:
        return {
            "destination": resolution["destination"],
            "resolved_ip": None,
            "ping": {
                "status": "not_run",
                "error": resolution["error"],
            },
            "hops": [],
            "error": resolution["error"],
        }

    resolved_ip = resolution["resolved_ip"]
    ping_result = ping_host(resolved_ip)
    try:
        hops = traceroute(resolved_ip)
        error = None
    except TracerouteError as exc:
        hops = []
        error = str(exc)

    result = NetworkData(destination, resolved_ip, ping_result, [
        Hop(**hop) for hop in hops
    ], error)
    return result.to_dict()


__all__ = [
    "Hop",
    "NetworkData",
    "ResolutionError",
    "TracerouteError",
    "collect_network_data",
    "parse_ping_output",
    "parse_tracert_output",
    "ping_host",
    "resolve",
    "resolve_domain",
    "traceroute",
]
