"""Local interactive demo for Member 1's network data module."""

import json
import sys
import unittest

from network import collect_network_data, parse_ping_output
from network.traceroute import parse_tracert_output


class ParserTests(unittest.TestCase):
    def test_ping_parser_collects_summary_and_reply_times(self):
        output = """
Reply from 8.8.8.8: bytes=32 time=12ms TTL=117
Reply from 8.8.8.8: bytes=32 time=14ms TTL=117
Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 2, Lost = 2 (50% loss),
Approximate round trip times in milli-seconds:
    Minimum = 12ms, Maximum = 14ms, Average = 13ms
"""
        result = parse_ping_output(output)
        self.assertEqual(result["sent"], 4)
        self.assertEqual(result["received"], 2)
        self.assertEqual(result["latencies"], [12.0, 14.0])
        self.assertEqual(result["packet_loss"], 50.0)

    def test_tracert_parser_keeps_timeout_hops(self):
        output = """
  1    <1 ms    <1 ms    <1 ms  192.168.1.1
  2     *        *        *     Request timed out.
  3    20 ms    18 ms    19 ms  8.8.8.8
"""
        hops = parse_tracert_output(output)
        self.assertEqual(hops[0].to_dict(), {
            "hop_number": 1, "ip": "192.168.1.1",
            "latency": 1.0, "status": "success",
        })
        self.assertEqual(hops[1].status, "timeout")
        self.assertIsNone(hops[1].latency)


def run_demo() -> None:
    print("=" * 40)
    print("PACKET JOURNEY NETWORK TEST")
    print("=" * 40)
    destination = input("\nEnter destination: ").strip()
    if not destination:
        print("No destination entered.")
        return

    data = collect_network_data(destination)
    print("\nDNS Resolution")
    print(f"Destination: {data['destination']}")
    print(f"Resolved IP: {data['resolved_ip'] or 'unresolved'}")

    print("\nPING")
    ping = data["ping"]
    if ping.get("status") == "not_run":
        print(f"Ping not run: {ping.get('error', 'DNS resolution failed.')}")
    else:
        print(f"Packets sent: {ping.get('sent', 0)}")
        print(f"Packets received: {ping.get('received', 0)}")
        print(f"Packet loss: {ping.get('packet_loss', 'unknown')}%")
        print(f"Average latency: {ping.get('average_latency', 'unknown')} ms")
        print(f"Latencies: {ping.get('latencies', [])}")
        print(f"Status: {ping.get('status', 'unknown')}")

    print("\nTRACEROUTE")
    if data.get("error") and not data["hops"]:
        print(f"Traceroute unavailable: {data['error']}")
    else:
        for hop in data["hops"]:
            latency = (
                f"{hop['latency']} ms"
                if hop["latency"] is not None
                else "timeout"
            )
            print(f"Hop {hop['hop_number']} -> {hop['ip']} -> {latency}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        run_demo()
