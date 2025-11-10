# main.py with CORS support покажи статус интерфейсов на хосте 10.27.214.28
import logging
import argparse
from flask import Flask, request, Response, jsonify
from flask_cors import CORS  # New import for CORS
from orchestrator import CoopetitionSystem
from config import SystemConfig
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes; you can customize if needed, e.g., CORS(app, origins=["http://your-web-interface-origin"])

@app.route('/process', methods=['POST'])
def process_query_endpoint():
    """
    Endpoint to process a user query received from a web interface.
    Expects a JSON payload with a 'query' field, e.g., {"query": "просканируй порты на хосте 10.27.192.116"}
    Streams the response in OpenAI-compatible format to match JS expectations.
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in JSON payload"}), 400
        
        query = data['query']
        logger.info(f"Received query: {query}")
        
        def generate():
            # Initialize config and system for each request
            config = SystemConfig()
            system = CoopetitionSystem(config)
            
            # Use a streaming version of process_query
            for chunk in system.process_query_stream(query):
                # Format as OpenAI stream chunk
                stream_data = {
                    "choices": [
                        {
                            "delta": {
                                "content": chunk
                            }
                        }
                    ]
                }
                yield f"data: {json.dumps(stream_data)}\n\n"
            
            # End of stream
            yield "data: [DONE]\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        logger.error(f"Failed to process query: {str(e)}")
        return jsonify({"error": str(e)}), 500

def main() -> None:
    """
    Main entry point for the application.
    Runs a Flask server that supports streaming responses.
    """
    parser = argparse.ArgumentParser(description="Run the CoopetitionSystem as a server.")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)"
    )
    args = parser.parse_args()

    try:
        logger.info(f"Starting server on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)
    
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

if __name__ == "__main__":
    main()