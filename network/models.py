"""Small data models used to normalize collected network information."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Hop:
    """One raw hop reported by traceroute."""

    hop_number: int
    ip: str
    latency: Optional[float]
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NetworkData:
    """Raw DNS, ping, and traceroute data.

    This model intentionally does not calculate traceroute statistics. That
    analysis belongs to a later project layer.
    """

    destination: str
    resolved_ip: Optional[str]
    ping: Dict[str, Any]
    hops: List[Hop]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "destination": self.destination,
            "resolved_ip": self.resolved_ip,
            "ping": self.ping,
            "hops": [hop.to_dict() for hop in self.hops],
        }
        if self.error is not None:
            result["error"] = self.error
        return result
