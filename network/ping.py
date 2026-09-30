"""Windows ping collection and output parsing."""

import ipaddress
import re
import subprocess
from typing import Any, Dict, List, Optional

_REPLY_TIME = re.compile(
    r"(?:time|zeit)\s*[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE
)
_SUMMARY = re.compile(
    r"(?:Sent|Gesendet)\s*=\s*(\d+).*?"
    r"(?:Received|Empfangen)\s*=\s*(\d+).*?"
    r"(?:Lost|Verloren)\s*=\s*(\d+)\s*\(\s*(\d+(?:[.,]\d+)?)\s*%\s*",
    re.IGNORECASE | re.DOTALL,
)
_AVERAGE = re.compile(
    r"(?:Average|Mittelwert)\s*=\s*(\d+(?:[.,]\d+)?)\s*ms",
    re.IGNORECASE,
)
_MINIMUM = re.compile(
    r"(?:Minimum|Minimum)\s*=\s*(\d+(?:[.,]\d+)?)\s*ms",
    re.IGNORECASE,
)
_MAXIMUM = re.compile(
    r"(?:Maximum|Maximum)\s*=\s*(\d+(?:[.,]\d+)?)\s*ms",
    re.IGNORECASE,
)


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _first_number(pattern: re.Pattern[str], output: str) -> Optional[float]:
    match = pattern.search(output)
    return _number(match.group(1)) if match else None


def _empty_result(status: str, error: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "sent": 0,
        "received": 0,
        "packet_loss": None,
        "latencies": [],
        "average_latency": None,
        "min_latency": None,
        "max_latency": None,
        "status": status,
    }
    if error:
        result["error"] = error
    return result


def parse_ping_output(output: str, return_code: int = 0) -> Dict[str, Any]:
    """Parse English or common German Windows ping output."""

    latencies = [_number(value) for value in _REPLY_TIME.findall(output)]
    summary = _SUMMARY.search(output)
    if summary:
        sent, received, _, loss = summary.groups()
        sent_count = int(sent)
        received_count = int(received)
        packet_loss = _number(loss)
    else:
        sent_count = len(latencies)
        received_count = len(latencies)
        packet_loss = (
            round((sent_count - received_count) * 100 / sent_count, 2)
            if sent_count
            else None
        )

    result = {
        "sent": sent_count,
        "received": received_count,
        "packet_loss": packet_loss,
        "latencies": latencies,
        "average_latency": _first_number(_AVERAGE, output),
        "min_latency": _first_number(_MINIMUM, output),
        "max_latency": _first_number(_MAXIMUM, output),
        "status": "success" if return_code == 0 and received_count else "timeout",
    }
    if result["average_latency"] is None and latencies:
        result["average_latency"] = round(sum(latencies) / len(latencies), 2)
    if result["min_latency"] is None and latencies:
        result["min_latency"] = min(latencies)
    if result["max_latency"] is None and latencies:
        result["max_latency"] = max(latencies)
    return result


def ping_host(
    ip: str, count: int = 4, timeout: float = 2.0
) -> Dict[str, Any]:
    """Ping an IPv4 address and return parsed packet-level results.

    ``timeout`` is in seconds; Windows receives the equivalent timeout in
    milliseconds through the ``-w`` option.
    """

    try:
        address = ipaddress.ip_address(ip.strip())
        if address.version != 4:
            return _empty_result("error", "Only IPv4 addresses are supported.")
    except ValueError:
        return _empty_result("error", f"Invalid IPv4 address: {ip!r}.")
    if count < 1:
        return _empty_result("error", "count must be at least 1.")
    if timeout <= 0:
        return _empty_result("error", "timeout must be greater than 0.")

    command = [
        "ping",
        "-n",
        str(count),
        "-w",
        str(max(1, round(timeout * 1000))),
        str(address),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=(count * timeout) + 5,
            check=False,
        )
    except FileNotFoundError:
        return _empty_result("error", "The Windows ping command was not found.")
    except subprocess.TimeoutExpired:
        return _empty_result("timeout", "The ping command timed out.")
    except OSError as exc:
        return _empty_result("error", f"Could not run ping: {exc}.")

    result = parse_ping_output(
        (completed.stdout or "") + (completed.stderr or ""),
        completed.returncode,
    )
    if completed.returncode != 0 and result["received"] == 0:
        result["status"] = "unreachable"
    return result
