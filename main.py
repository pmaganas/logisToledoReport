import logging

# Configure logging to suppress urllib3 debug logs
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)

from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
