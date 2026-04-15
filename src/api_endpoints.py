import logging
import base64
import binascii

from flask import Blueprint, Response, request
from sbsys_client import SbsysClient
from delta_client import DeltaClient
from utils.config import SBSYS_URL, SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD, \
                         DELTA_URL, DELTA_AUTH_URL, DELTA_REALM, DELTA_CLIENT_ID, DELTA_CLIENT_SECRET, \
                         TEST_DQ_NUMBER

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')
sbsys_client = SbsysClient(SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET,
                           SBSYS_USERNAME, SBSYS_PASSWORD, SBSYS_URL)
delta_client =  DeltaClient(DELTA_URL, DELTA_AUTH_URL, DELTA_REALM,
                            DELTA_CLIENT_ID, DELTA_CLIENT_SECRET)


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

            # Prepare for journalization
            logger.info(f"Simulating journalizing document for user: {user.split(' - ')[-1]}")
            user_dq = user.split(" - ")[-1]  # Extract DQ number from user string

            search_dict = delta_client.get_dq_number_search(user_dq)
            search_result = delta_client.search(search_dict)
            user_cpr = search_result[0].get('CPR', None) if search_result and len(search_result) > 0 else None

            logger.info(f"Search returned CPR: {user_cpr}")
            sag_ids = sbsys_client.get_personalesag(cpr=user_cpr)
            logger.info(f"SBSYS search for CPR {user_cpr} returned sag_ids: {[sag['Id'] for sag in sag_ids]}")

            # Journalize the document for each sag_id 
            # for sag_id in sag_ids:
            #     logger.info(f"Simulating journalization for sag_id: {sag_id['SagId']}")

            #     # Simulate journalization process (replace with actual logic)
            #     time.sleep(2)  # Simulate processing time
            #     return Response(f"Document journalized successfully for user: {user}", status=200)

        except Exception as e:
            logger.error(f"Error during journalization: {str(e)}")
            return Response("An error occurred during journalization.", status=500)

    else:
        return Response("Method not allowed. Use POST to journalize a document.", status=405)


@api_endpoints.route('/test-delta', methods=['GET'])
def test_delta():
    """
    Test endpoint to verify connectivity with the Delta API.
    """
    search_dict = delta_client.get_dq_number_search(TEST_DQ_NUMBER)
    result = delta_client.search(search_dict)

    if result is not None:
        count = len(result)
        return Response(f"Delta API connectivity test successful. Found {count} objects of type 'Person': {result}", status=200)
    else:
        return Response("Failed to connect to Delta API or no results found.", status=500)
