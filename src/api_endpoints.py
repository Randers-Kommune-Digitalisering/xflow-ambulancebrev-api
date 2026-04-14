import logging
import time

from flask import Blueprint, Response, request

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')


@api_endpoints.route('/journaliser', methods=['GET', 'POST'])
def journaliser():
    """
    Journalize a PDF document in SBSYS based on the provided JSON payload. The payload should contain the following fields:
    - user: The user performing the journalization formatted as "<full name> - <dqnumber>"
    - data: The PDF document to be journalized
    """

    if request.method == 'POST':
        try:
            payload = request.get_json()
            user = payload.get('user')
            data = payload.get('data')

            # Validate the payload
            if not user or not data:
                return Response("Invalid payload: 'user' and 'data' fields are required.", status=400)
            
            # Validate PDF file            
            if not data.startswith('%PDF'):
                logger.warning(f"Invalid PDF data received: {data}")
                return Response("Invalid PDF data.", status=400)

            # Simulate journalization process (replace with actual logic)
            logger.info(f"Simulating journalizing document for user: {user}")
            time.sleep(2)  # Simulate processing time

            return Response(f"Document journalized successfully for user: {user}", status=200)
        except Exception as e:
            logger.error(f"Error during journalization: {str(e)}")
            return Response("An error occurred during journalization.", status=500)
    else:
        return Response("Method not allowed. Use POST to journalize a document.", status=405)
