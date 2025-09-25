from flask import Flask, request, jsonify
from flask_cors import CORS

from train_planner import handle_request # This is the key line

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

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
