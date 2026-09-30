"""IPv4 DNS resolution helpers."""

import ipaddress
import socket
from typing import Any, Dict


class ResolutionError(OSError):
    """Raised when a destination cannot be resolved to IPv4."""


def resolve_domain(destination: str) -> Dict[str, Any]:
    """Resolve a hostname or accept an IPv4 address.

    Errors are returned as structured data so callers can display them
    without allowing a failed DNS lookup to terminate the application.
    """

    target = destination.strip()
    if not target:
        return {
            "destination": target,
            "resolved_ip": None,
            "status": "error",
            "error": "Destination cannot be empty.",
        }

    try:
        address = ipaddress.ip_address(target)
        if address.version != 4:
            raise ResolutionError("Only IPv4 destinations are supported.")
        return {
            "destination": target,
            "resolved_ip": str(address),
            "status": "success",
        }
    except ValueError:
        pass
    except ResolutionError as exc:
        return {
            "destination": target,
            "resolved_ip": None,
            "status": "error",
            "error": str(exc),
        }

    try:
        addresses = socket.getaddrinfo(
            target, None, socket.AF_INET, socket.SOCK_STREAM
        )
        resolved_ip = addresses[0][4][0] if addresses else None
    except socket.gaierror as exc:
        return {
            "destination": target,
            "resolved_ip": None,
            "status": "error",
            "error": f"Could not resolve '{target}': {exc.strerror or exc}.",
        }

    if resolved_ip is None:
        return {
            "destination": target,
            "resolved_ip": None,
            "status": "error",
            "error": f"Could not resolve '{target}'.",
        }
    return {
        "destination": target,
        "resolved_ip": resolved_ip,
        "status": "success",
    }


def resolve(destination: str) -> str:
    """Compatibility helper that returns only the resolved IPv4 address."""

    result = resolve_domain(destination)
    if result["resolved_ip"] is None:
        raise ResolutionError(result["error"])
    return result["resolved_ip"]
