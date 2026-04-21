from flask import Flask
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration, is_ready_gauge, last_updated_gauge
from utils.config import DEBUG, PORT, POD_NAME, DRY_RUN, TESTING
from api_endpoints import api_endpoints


set_logging_configuration()


def create_app():
    app = Flask(__name__)
    health = HealthCheck()
    app.add_url_rule('/healthz', 'healthcheck', view_func=lambda: health.run())
    app.add_url_rule('/metrics', 'metrics', view_func=generate_latest)

    app.register_blueprint(api_endpoints)

    @app.before_request
    def set_ready():
        is_ready_gauge.labels(job_name=POD_NAME, error_type=None).set(1)
        last_updated_gauge.set_to_current_time()

    return app


app = create_app()


if __name__ == '__main__':  # pragma: no cover
    if DRY_RUN:
        print("DRY_RUN enabled - the application will start but journalization will be skipped")
    if TESTING:
        print("TESTING enabled - using test CPR number and SBSYS status for testing environment")
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
