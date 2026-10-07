from network import collect_network_data
from analysis.analyzer import analyze_trace

destination = input("Enter destination (e.g. google.com): ")

print("\nCollecting network data... Please wait.")

trace_data = collect_network_data(destination)
results = analyze_trace(trace_data)

print("\n===== PACKET JOURNEY ANALYSIS =====")
print("Destination:", trace_data["destination"])
print("Resolved IP:", trace_data["resolved_ip"])

print("\n===== ANALYSIS RESULTS =====")

for metric, value in results.items():
    print(f"{metric}: {value}")

print("\n===== TRACEROUTE DETAILS =====")
print("Total hops:", results["total_hops"])
print("Responding hops:", results["responding_hops"])
print("Timeout hops:", results["timeout_hops"])
print("Route continued after timeout:", results["route_continued"])

print("\n===== LATENCY DETAILS =====")
print("Average latency:", results["average_latency"], "ms")
print("Minimum latency:", results["min_latency"], "ms")
print("Maximum latency:", results["max_latency"], "ms")
print("Fastest hop(s):", results["fastest_hops"])
print("Slowest hop(s):", results["slowest_hops"])

print("\n===== PING DETAILS =====")
print("Packet loss:", results["packet_loss"], "%")