"""Windows ``tracert`` collection and parsing."""

import ipaddress
import re
import subprocess
from typing import List

from .models import Hop
from .resolver import resolve_domain

_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_LATENCY_PATTERN = re.compile(
    r"(?<!\d)(?:<\s*)?(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE
)


class TracerouteError(RuntimeError):
    """Raised when a traceroute command cannot be started or prepared."""


def _valid_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).version == 4
    except ValueError:
        return False


def parse_tracert_output(output: str) -> List[Hop]:
    """Parse Windows tracert lines, including ``* * *`` timeout hops."""

    hops: List[Hop] = []
    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not match:
            continue
        hop_number = int(match.group(1))
        body = match.group(2)
        ip_match = next(
            (candidate for candidate in _IP_PATTERN.findall(body) if _valid_ip(candidate)),
            None,
        )
        latency_values = [
            float(value.replace(",", "."))
            for value in _LATENCY_PATTERN.findall(body)
        ]
        if ip_match and latency_values:
            hops.append(Hop(hop_number, ip_match, min(latency_values), "success"))
        else:
            hops.append(Hop(hop_number, "*", None, "timeout"))
    return hops


def traceroute(
    destination: str, max_hops: int = 30, timeout: float = 5.0
) -> List[dict]:
    """Run Windows tracert and return raw hop dictionaries."""

    if max_hops < 1:
        raise TracerouteError("max_hops must be at least 1.")
    if timeout <= 0:
        raise TracerouteError("timeout must be greater than 0.")

    try:
        address = ipaddress.ip_address(destination.strip())
        if address.version != 4:
            raise TracerouteError("Only IPv4 destinations are supported.")
        target = str(address)
    except ValueError:
        resolution = resolve_domain(destination)
        if resolution["resolved_ip"] is None:
            raise TracerouteError(resolution["error"]) from None
        target = resolution["resolved_ip"]

    command = ["tracert", "-d", "-h", str(max_hops), target]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=(max_hops * timeout) + 5,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TracerouteError("The Windows tracert command was not found.") from exc
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return [hop.to_dict() for hop in parse_tracert_output(output)]
    except OSError as exc:
        raise TracerouteError(f"Could not run tracert: {exc}.") from exc

    output = (completed.stdout or "") + (completed.stderr or "")
    return [hop.to_dict() for hop in parse_tracert_output(output)]
