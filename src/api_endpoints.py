import logging
import base64
import binascii

from flask import Blueprint, Response, request
from sbsys_client import SbsysClient
from delta_client import DeltaClient
from utils.config import SBSYS_URL, SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD, \
    DELTA_URL, DELTA_AUTH_URL, DELTA_REALM, DELTA_CLIENT_ID, DELTA_CLIENT_SECRET, \
    TEST_CPR_NUMBER, TESTING

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')
sbsys_client = SbsysClient(SBSIP_CLIENT_ID, SBSIP_CLIENT_SECRET, SBSYS_USERNAME, SBSYS_PASSWORD, SBSYS_URL)
delta_client = DeltaClient(DELTA_URL, DELTA_AUTH_URL, DELTA_REALM, DELTA_CLIENT_ID, DELTA_CLIENT_SECRET)

SBSYS_SAG_STATUS_ACTIVE = 6  # '6' represents the active status in SBSYS
DELFORLOEB_TARGET_TITLE = "07 Øvrige"  # The title to match for delforloeb


@api_endpoints.route('/journaliser', methods=['POST'])
def journaliser():
    """
    Journalize a PDF document in SBSYS based on the provided JSON payload. The payload should contain the following fields:
    - user: The user performing the journalization formatted as "<full name> - <dqnumber>"
    - data: Base64-encoded PDF document to be journalized (string)
    """
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
        if TESTING:
            user_cpr = TEST_CPR_NUMBER
        else:
            user_dq = user.split(" - ")[-1]  # Extract DQ number from user string
            search_dict = delta_client.get_dq_number_search(user_dq)
            search_result = delta_client.search(search_dict)
            user_cpr = search_result[0].get('CPR', None) if search_result and len(search_result) > 0 else None

        # Fetch active personalesager from SBSYS
        sag_result = sbsys_client.get_personalesag(cpr=user_cpr)
        active_sag_result = [sag for sag in sag_result if sag.get('SagsStatus', {}).get('Id') == SBSYS_SAG_STATUS_ACTIVE]
        if len(active_sag_result) == 0:
            logger.warning(f"No active sag found for user {user}")
            return Response(f"No active sag found for user {user}", status=404)

        # Journalize the document for each sag
        for sag in active_sag_result:
            # Fetch delforloeb for each sag
            delforloeb_result = sbsys_client.get_delforloeb(sag_id=sag['Id']) if sag else None
            delforloeb_to_use = None
            if delforloeb_result and isinstance(delforloeb_result, list):
                delforloeb_to_use = next(
                    (item for item in (delforloeb_result or []) if item.get("Titel") == DELFORLOEB_TARGET_TITLE),
                    None,
                )

            # Upload the document to sag
            journalize_result = sbsys_client.journalize(file=pdf_bytes, sag_id=sag['Id'], delforloeb_id=delforloeb_to_use['ID'] if delforloeb_to_use else None)
            if journalize_result:
                logger.info(f"Journalization successful for sag: {sag['Nummer']}")
            else:
                logger.error(f"Journalization failed for sag: {sag['Nummer']}")

        return Response(f"Document journalized successfully for user: {user}", status=200)

    except Exception as e:
        logger.error(f"Error during journalization: {str(e)}")
        return Response("An error occurred during journalization.", status=500)
