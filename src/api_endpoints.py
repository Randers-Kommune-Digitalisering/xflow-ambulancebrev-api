import logging
import time
import base64
import binascii

from flask import Blueprint, Response, request

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')


@api_endpoints.route('/journaliser', methods=['GET', 'POST'])
def journaliser():
    """
    Journalize a PDF document in SBSYS based on the provided JSON payload. The payload should contain the following fields:
    - user: The user performing the journalization formatted as "<full name> - <dqnumber>"
    - data: Base64-encoded PDF document to be journalized (string)
    """

    if request.method == 'POST':
        try:
            payload = request.get_json(silent=True) or {}
            user = payload.get('user')
            data = payload.get('data')

            # Validate the payload
            if not user or not data:
                return Response("Invalid payload: 'user' and 'data' fields are required.", status=400)
            if not isinstance(data, str):
                return Response("Invalid payload: 'data' must be a base64-encoded string.", status=400)

            # Only accept base64-encoded PDFs
            try:
                pdf_bytes = base64.b64decode(data.strip(), validate=True)

            except (binascii.Error, ValueError):
                logger.warning(
                    "Invalid base64 PDF data received (len=%s, prefix=%r)",
                    len(data),
                    data[:12],
                )
                return Response("Invalid PDF data: expected base64-encoded PDF.", status=400)

            if not pdf_bytes.startswith(b'%PDF'):
                logger.warning(
                    "Base64 decoded data is not a PDF (len=%s, prefix=%r)",
                    len(pdf_bytes),
                    pdf_bytes[:8],
                )
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
