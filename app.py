from flask import Flask, request, jsonify

from database import initialize_database, save_trace, get_history


app = Flask(__name__)


# Initialize SQLite database
initialize_database()


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy"
    })


# --------------------------------------------------
# TRACE
# --------------------------------------------------

@app.route("/trace", methods=["POST"])
def trace():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    destination = data.get("destination")

    if not destination:
        return jsonify({
            "error": "Destination is required"
        }), 400


    # --------------------------------------------------
    # TEMPORARY MOCK DATA
    # This will later be replaced by Member 1
    # --------------------------------------------------

    network_data = {

        "destination": destination,

        "resolved_ip": "142.250.195.14",

        "hops": [

            {
                "hop_number": 1,
                "ip": "192.168.1.1",
                "latency": 2,
                "status": "success"
            },

            {
                "hop_number": 2,
                "ip": "10.20.0.1",
                "latency": 8,
                "status": "success"
            },

            {
                "hop_number": 3,
                "ip": "172.16.2.1",
                "latency": 15,
                "status": "success"
            },

            {
                "hop_number": 4,
                "ip": "142.250.195.14",
                "latency": 21,
                "status": "success"
            }
        ]
    }


    # --------------------------------------------------
    # TEMPORARY ANALYSIS
    # This will later be replaced by Member 2
    # --------------------------------------------------

    latencies = [
        hop["latency"]
        for hop in network_data["hops"]
        if hop["latency"] is not None
    ]

    total_hops = len(network_data["hops"])

    if latencies:

        average_latency = sum(latencies) / len(latencies)

        min_latency = min(latencies)

        max_latency = max(latencies)

    else:

        average_latency = 0
        min_latency = 0
        max_latency = 0


    timeout_count = sum(
        1
        for hop in network_data["hops"]
        if hop["status"] == "timeout"
    )

    packet_loss = (
        timeout_count / total_hops * 100
        if total_hops > 0
        else 0
    )


    statistics = {

        "total_hops": total_hops,

        "average_latency": round(average_latency, 2),

        "packet_loss": round(packet_loss, 2),

        "min_latency": min_latency,

        "max_latency": max_latency
    }


    # --------------------------------------------------
    # COMBINE NETWORK + ANALYSIS DATA
    # --------------------------------------------------

    result = {

        "destination": network_data["destination"],

        "resolved_ip": network_data["resolved_ip"],

        "hops": network_data["hops"],

        "statistics": statistics
    }


    # --------------------------------------------------
    # SAVE TO SQLITE
    # --------------------------------------------------

    save_trace(result)


    # --------------------------------------------------
    # SEND RESULT TO FRONTEND
    # --------------------------------------------------

    return jsonify(result)


# --------------------------------------------------
# HISTORY
# --------------------------------------------------

@app.route("/history", methods=["GET"])
def history():

    traces = get_history()

    return jsonify(traces)


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )