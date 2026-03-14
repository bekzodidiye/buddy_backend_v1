"""
api/exception_handler.py

Custom DRF exception handler that ensures all errors return a consistent
JSON structure instead of the default DRF format (which varies by error type).

Standard error response format:
    {
        "error": {
            "code": "authentication_failed",
            "message": "Token yaroqsiz qilingan.",
            "detail": { ... }   # optional extra context
        }
    }
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Call REST framework's default exception handler first so we get
    the standard HttpResponse, then we modify the response data.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Log server errors (5xx) for monitoring
        if response.status_code >= 500:
            view = context.get('view')
            logger.error(
                "Server error [%s] in %s: %s",
                response.status_code,
                view.__class__.__name__ if view else 'unknown',
                exc,
                exc_info=True
            )

        # Standardize the response structure
        original_data = response.data

        # DRF returns different shapes: sometimes {'detail': ...},
        # sometimes {'field': ['error']} for validation errors.
        if isinstance(original_data, dict) and 'detail' in original_data:
            # Authentication/permission errors
            error_message = str(original_data['detail'])
            error_code = getattr(original_data['detail'], 'code', 'error')
        elif isinstance(original_data, list):
            error_message = '; '.join(str(e) for e in original_data)
            error_code = 'invalid'
        else:
            # Validation errors — field-level
            error_message = "Kiritilgan ma'lumotlar noto'g'ri."
            error_code = 'validation_error'

        response.data = {
            'error': {
                'code': error_code,
                'message': error_message,
                'status': response.status_code,
            }
        }

        # Attach field-level validation details if present
        if isinstance(original_data, dict) and 'detail' not in original_data:
            response.data['error']['fields'] = original_data

    else:
        # Unhandled Python exceptions — return a 500 with a safe message
        logger.exception("Unhandled exception: %s", exc)
        response = Response(
            {
                'error': {
                    'code': 'server_error',
                    'message': 'Ichki server xatosi. Iltimos, keyinroq urinib ko\'ring.',
                    'status': 500,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
