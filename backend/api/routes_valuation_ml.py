"""Explicit observational ML capability, separate from deterministic valuation."""
from typing import Literal
from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse

from services.valuation_ml.contract import Subject
from services.valuation_ml.inference import get_service
from services.plvr_ml_admissibility import public_scope


class MLValuationRequest(Subject):
    """API purpose restriction; this constant is not a fitted model feature."""
    requested_value_basis: Literal['reported_transfer'] = 'reported_transfer'

class MLRoute(APIRoute):
    """Sanitize rejected values before JSON encoding, including NaN/Infinity.

    Keeping this on the route makes the boundary identical in both entrypoints
    and when the router is included in another FastAPI application.
    """
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def validated(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                detail=[{'type':str(item['type'])[:64],
                         'loc':[str(x)[:64] if isinstance(x,str) else x for x in item['loc'][:4]],
                         'msg':str(item['msg'])[:256]} for item in error.errors()[:20]]
                return JSONResponse({'detail':detail},status_code=422,headers={'Cache-Control':'no-store'})
        return validated


router=APIRouter(prefix='/valuation/ml/v1',tags=['valuation-ml'],route_class=MLRoute)


def _response(result):
    status={'available':200,'unsupported':422,'unavailable':503,'busy':429}[result['status']]
    return JSONResponse({**result,'scope':public_scope()},status_code=status,headers={'Cache-Control':'no-store',
        **({'Retry-After':'1'} if status in (429,503) else {})})


@router.get('/status')
def model_status():
    return _response(get_service().status())


@router.post('/estimate')
def estimate(subject: MLValuationRequest):
    return _response(get_service().estimate(subject))
