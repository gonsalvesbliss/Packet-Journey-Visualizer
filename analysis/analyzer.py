def analyze_trace(trace_data):
    """
    Analyze network trace data and calculate network statistics.

    Input:
        trace_data: Dictionary containing destination, hops and ping data.

    Output:
        Dictionary containing calculated network statistics.
    """

    hops = trace_data.get("hops", [])

    # ---------------------------------------------------------
    # 1. Separate successful hops and timeout hops
    # ---------------------------------------------------------

    latencies = []
    timeout_hops = []
    responding_hops = []

    for hop in hops:
        latency = hop.get("latency")
        status = str(hop.get("status", "")).lower()
        hop_number = hop.get("hop_number")

        if status == "timeout":
            timeout_hops.append(hop_number)

        if (
            status == "success"
            and isinstance(latency, (int, float))
            and not isinstance(latency, bool)
            and latency >= 0
        ):
            latencies.append(latency)
            responding_hops.append(hop_number)

    # ---------------------------------------------------------
    # 2. Calculate total number of hops
    # ---------------------------------------------------------
    # IMPORTANT:
    # Timeout hops are still part of the traceroute.
    # Therefore, they are included in total_hops.

    total_hops = len(hops)

    # ---------------------------------------------------------
    # 3. Check whether the route continued after a timeout
    # ---------------------------------------------------------

    route_continued = False

    for timeout_hop in timeout_hops:
        for hop in hops:
            hop_number = hop.get("hop_number")
            status = str(hop.get("status", "")).lower()

            if (
                isinstance(hop_number, int)
                and isinstance(timeout_hop, int)
                and hop_number > timeout_hop
                and status == "success"
            ):
                route_continued = True
                break

        if route_continued:
            break

    # ---------------------------------------------------------
    # 4. Calculate average, minimum and maximum latency
    # ---------------------------------------------------------
    # Timeout hops are NOT included because their latency is None.

    if latencies:
        average_latency = round(sum(latencies) / len(latencies), 2)
        min_latency = min(latencies)
        max_latency = max(latencies)
    else:
        average_latency = None
        min_latency = None
        max_latency = None

    # ---------------------------------------------------------
    # 5. Find all fastest hops
    # ---------------------------------------------------------

    fastest_hops = []

    if latencies:
        fastest_latency = min(latencies)

        for hop in hops:
            latency = hop.get("latency")
            status = str(hop.get("status", "")).lower()

            if (
                status == "success"
                and isinstance(latency, (int, float))
                and not isinstance(latency, bool)
                and latency == fastest_latency
            ):
                fastest_hops.append({
                    "hop_number": hop.get("hop_number"),
                    "ip": hop.get("ip"),
                    "latency": latency
                })

    # ---------------------------------------------------------
    # 6. Find all slowest hops
    # ---------------------------------------------------------

    slowest_hops = []

    if latencies:
        slowest_latency = max(latencies)

        for hop in hops:
            latency = hop.get("latency")
            status = str(hop.get("status", "")).lower()

            if (
                status == "success"
                and isinstance(latency, (int, float))
                and not isinstance(latency, bool)
                and latency == slowest_latency
            ):
                slowest_hops.append({
                    "hop_number": hop.get("hop_number"),
                    "ip": hop.get("ip"),
                    "latency": latency
                })

    # ---------------------------------------------------------
    # 7. Keep the original slowest_hop field
    # ---------------------------------------------------------
    # This maintains compatibility with the existing backend.
    # If multiple hops have the same maximum latency,
    # the first one is used here.
    #
    # The complete list is available in slowest_hops.

    slowest_hop = None

    if slowest_hops:
        slowest_hop = slowest_hops[0]

    # ---------------------------------------------------------
    # 8. Calculate packet loss from Ping statistics
    # ---------------------------------------------------------
    # IMPORTANT:
    # Traceroute timeouts do NOT automatically become packet loss.

    packet_loss = None
    ping = trace_data.get("ping")

    if isinstance(ping, dict):
        sent = ping.get("sent")
        received = ping.get("received")

        if (
            isinstance(sent, int)
            and not isinstance(sent, bool)
            and isinstance(received, int)
            and not isinstance(received, bool)
            and sent > 0
            and 0 <= received <= sent
        ):
            packet_loss = round(
                ((sent - received) / sent) * 100, 2
            )

    # ---------------------------------------------------------
    # 9. Classify overall network status
    # ---------------------------------------------------------

    if packet_loss == 100:
        network_status = "UNREACHABLE"

    elif packet_loss is not None and packet_loss >= 50:
        network_status = "POOR"

    elif average_latency is None:
        network_status = "UNKNOWN"

    elif average_latency > 150:
        network_status = "POOR"

    elif (
        (packet_loss is not None and packet_loss > 0)
        or average_latency > 80
    ):
        network_status = "MODERATE"

    else:
        network_status = "GOOD"

    # ---------------------------------------------------------
    # 10. Return analysis results
    # ---------------------------------------------------------

    return {
        "total_hops": total_hops,
        "responding_hops": responding_hops,
        "timeout_hops": timeout_hops,
        "route_continued": route_continued,

        "average_latency": average_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,

        "fastest_hops": fastest_hops,
        "slowest_hops": slowest_hops,

        # Existing field kept for compatibility
        "slowest_hop": slowest_hop,

        "packet_loss": packet_loss,
        "network_status": network_status
    }