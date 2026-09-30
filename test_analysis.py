from analysis.analyzer import analyze_trace

trace_data = {
    "destination": "google.com",
    "resolved_ip": "142.250.183.14",
    "hops": [
        {"hop_number": 1, "ip": "192.168.1.1", "latency": 5, "status": "success"},
        {"hop_number": 2, "ip": "10.0.0.1", "latency": 15, "status": "success"},
        {"hop_number": 3, "ip": "142.250.183.14", "latency": 25, "status": "success"}
    ],
    "ping": {"sent": 4, "received": 3}
}

results = analyze_trace(trace_data)

print("===== PACKET JOURNEY ANALYSIS =====")
print("Destination:", trace_data["destination"])

for metric, value in results.items():
    print(f"{metric}: {value}")