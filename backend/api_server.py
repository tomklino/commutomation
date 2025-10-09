import sys
import os
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS

from train_planner import handle_request, find_all_routes_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.expanduser('.patched_modules/israel-rail-api'))
from israelrailapi.stations import STATIONS


# Create the Flask application instance
app = Flask(__name__)
CORS(app)

# Define the web server's main endpoint
@app.route('/train_route', methods=['GET'])
def find_route_api():
    """
    API endpoint to find an optimal train route.
    Expects 'source', 'dest', 'arrival_date', and 'arrival_time' as query parameters.
    """
    try:
        source = request.args.get('source')
        dest = request.args.get('dest')
        arrival_date = request.args.get('arrival_date')
        arrival_time = request.args.get('arrival_time')

        # Check for required parameters
        if not all([source, dest, arrival_date, arrival_time]):
            return jsonify({"error": "Missing required parameters"}), 400

        # Call the core logic
        result = handle_request(source, dest, arrival_date, arrival_time)

        if result:
            return jsonify(result), 200
        else:
            return jsonify({"message": "No optimal route found."}), 404

    except Exception as e:
        # A simple error handler for unexpected issues
        return jsonify({"error": str(e)}), 500

@app.route('/v1/train_route', methods=['GET'])
def find_all_routes():
    """
    API endpoint to find all routes in a standard format.
    Expects 'source', 'dest', 'arrival_date', and 'arrival_time' as query parameters.
    Returns an array of up to 10 routes with arrival time before the requested time,
    ordered from latest arrival time to earliest, with the following structure:
    {
      route: {
        route_id: <String>,
        startTime: <ISO UTC time>,
        endTime: <ISO UTC time>,
        trains: [
          {
            departure: <ISO UTC time>,
            arrival: <ISO UTC time>,
            trainNumber: <Number>,
            platformNumber: <Number>
          }
        ],
        backupRoutes: [
          {
            route_id: <String>,
            delayMinutes: <Number>
          }
        ]
      }
    }
    
    backup routes are routes departing at least <min_departure_gap> minutes after
    the first route. "delayMinutes" represents the delay in arrival time from
    the original route to the backup route.
    
    The api takes optional arguments "min_departure_gap" and "max_arrival_diff" to
    limit the lookup for backup routes.
    """
    try:
        source = request.args.get('source')
        dest = request.args.get('dest')
        arrival_date = request.args.get('arrival_date')
        arrival_time = request.args.get('arrival_time')
        
        logger.info(f"v1/train_route request: source={source}, dest={dest}, arrival_date={arrival_date}, arrival_time={arrival_time}")
        
        # Optional parameters with defaults
        min_departure_gap = int(request.args.get('min_departure_gap', 5))
        max_arrival_diff = int(request.args.get('max_arrival_diff', 10))

        # Check for required parameters
        if not all([source, dest, arrival_date, arrival_time]):
            logger.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        # Call the handler
        result = find_all_routes_handler(
            source, 
            dest, 
            arrival_date, 
            arrival_time,
            min_departure_gap=min_departure_gap,
            max_arrival_diff=max_arrival_diff
        )

        if result:
            logger.info(f"Returning {len(result)} routes")
            return jsonify(result), 200
        else:
            logger.info("No routes found")
            return jsonify({"message": "No routes found."}), 404

    except ValueError as e:
        logger.error(f"ValueError: {e}", exc_info=True)
        return jsonify({"error": f"Invalid parameter value: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/stations', methods=['GET'])
def get_stations():
    """
    Returns all the stations in english from the list in israel-rail-api module
    """
    lang = request.args.get('lang', "Eng")

    return [ STATIONS[station_id][lang] for station_id in STATIONS ]


# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
