def analyze_trace(trace_data):
    """
    Analyze network trace data and calculate network statistics.

    Supports both:
    - Ping mode
    - Traceroute mode

    Input:
        trace_data: Dictionary containing destination, hops and ping data.

    Output:
        Dictionary containing calculated network statistics.
    """

    hops = trace_data.get("hops", [])
    ping = trace_data.get("ping", {})

    # --------------------------------------------------
    # 1. COLLECT TRACEROUTE LATENCIES
    # --------------------------------------------------

    latencies = []

    for hop in hops:

        latency = hop.get("latency")

        if (
            hop.get("status", "").lower() == "success"
            and isinstance(latency, (int, float))
            and not isinstance(latency, bool)
            and latency >= 0
        ):
            latencies.append(latency)

    # --------------------------------------------------
    # 2. TOTAL NUMBER OF HOPS
    # --------------------------------------------------

    total_hops = len(hops)

    # --------------------------------------------------
    # 3. CALCULATE LATENCY STATISTICS
    # --------------------------------------------------
    # If traceroute has valid hop latencies, use them.
    # Otherwise, use Ping latency data.

    if latencies:

        average_latency = round(
            sum(latencies) / len(latencies), 2
        )

        min_latency = min(latencies)
        max_latency = max(latencies)

    else:

        # Ping latency values
        ping_latencies = []

        if isinstance(ping, dict):

            values = ping.get("latencies", [])

            if isinstance(values, list):

                for latency in values:

                    if (
                        isinstance(latency, (int, float))
                        and not isinstance(latency, bool)
                        and latency >= 0
                    ):
                        ping_latencies.append(latency)

        # Use Ping statistics when available
        if ping_latencies:

            average_latency = round(
                sum(ping_latencies) / len(ping_latencies), 2
            )

            min_latency = min(ping_latencies)
            max_latency = max(ping_latencies)

        elif isinstance(ping, dict):

            average_latency = ping.get("average_latency")
            min_latency = ping.get("min_latency")
            max_latency = ping.get("max_latency")

        else:

            average_latency = None
            min_latency = None
            max_latency = None

    # --------------------------------------------------
    # 4. FIND SLOWEST SUCCESSFUL TRACEROUTE HOP
    # --------------------------------------------------

    slowest_hop = None

    for hop in hops:

        latency = hop.get("latency")

        if (
            hop.get("status", "").lower() == "success"
            and isinstance(latency, (int, float))
            and not isinstance(latency, bool)
            and latency >= 0
        ):

            if (
                slowest_hop is None
                or latency > slowest_hop["latency"]
            ):

                slowest_hop = {
                    "hop_number": hop.get("hop_number"),
                    "ip": hop.get("ip"),
                    "latency": latency
                }

    # --------------------------------------------------
    # 5. CALCULATE PACKET LOSS FROM PING
    # --------------------------------------------------

    packet_loss = None

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
                ((sent - received) / sent) * 100,
                2
            )

    # --------------------------------------------------
    # 6. CLASSIFY NETWORK STATUS
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 7. RETURN RESULTS
    # --------------------------------------------------

    return {
        "total_hops": total_hops,
        "average_latency": average_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "packet_loss": packet_loss,
        "slowest_hop": slowest_hop,
        "network_status": network_status
    }