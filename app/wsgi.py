from app import app
import logging

if __name__ == "__main__":
    # Development environment: run the Flask app directly
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Running Flask app in development mode.")
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # Production environment: Loaded by WSGI server
    logging.basicConfig(level=logging.INFO)
    logging.info("WSGI script initialized. App is ready for production.")
