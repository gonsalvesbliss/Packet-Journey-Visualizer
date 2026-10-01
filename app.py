
from flask import Flask, request, jsonify

from database import initialize_database, save_trace, get_history
from network.resolver import resolve_domain, ResolutionError
from network.traceroute import traceroute, TracerouteError
from network.ping import ping_host
from analysis.analyzer import analyze_trace


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
    # MEMBER 1 - NETWORK DATA COLLECTION
    # --------------------------------------------------

    try:

        # Resolve destination to IPv4 address
        resolution = resolve_domain(destination)

        if resolution["resolved_ip"] is None:
            return jsonify({
                "error": resolution["error"]
            }), 400

        resolved_ip = resolution["resolved_ip"]

        # Run traceroute and collect hops
        # Run ping to collect packet-level statistics
        ping = ping_host(resolved_ip)

        # Run traceroute and collect hops
        hops = traceroute(resolved_ip)

        network_data = {
            "destination": destination,
            "resolved_ip": resolved_ip,
            "ping": ping,
            "hops": hops
        }

    except (ResolutionError, TracerouteError) as exc:

        return jsonify({
            "error": str(exc)
        }), 500


    # --------------------------------------------------
    # MEMBER 2 - NETWORK ANALYSIS
    # --------------------------------------------------

    statistics = analyze_trace(network_data)


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
