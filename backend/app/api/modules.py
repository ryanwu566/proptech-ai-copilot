from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.assessments import (
    AegisCreditAssessment,
    LexPropAssessment,
    TaxOracleAssessment,
)
from app.schemas.assessments import (
    AegisCreditCreate,
    AssessmentResponse,
    LexPropCreate,
    TaxOracleCreate,
)
from app.services.rules_engine import (
    analyze_aegis_credit,
    analyze_lex_prop,
    analyze_tax_oracle,
)
from app.services.reports import (
    build_report_context,
    render_report_html,
    render_report_pdf,
)

router = APIRouter(tags=["modules"])

ASSESSMENT_MODELS = {
    "aegis-credit": AegisCreditAssessment,
    "tax-oracle": TaxOracleAssessment,
    "lex-prop": LexPropAssessment,
}


@router.post(
    "/aegis-credit/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_aegis_credit_assessment(
    payload: AegisCreditCreate,
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    result = analyze_aegis_credit(payload)
    assessment = AegisCreditAssessment(**payload.model_dump(), mock_result=result.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return AssessmentResponse(
        id=assessment.id,
        module="Aegis-Credit",
        created_at=assessment.created_at,
        result=result,
    )


@router.post(
    "/tax-oracle/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tax_oracle_assessment(
    payload: TaxOracleCreate,
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    result = analyze_tax_oracle(payload)
    assessment = TaxOracleAssessment(**payload.model_dump(), mock_result=result.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return AssessmentResponse(
        id=assessment.id,
        module="TaxOracle",
        created_at=assessment.created_at,
        result=result,
    )


@router.post(
    "/lex-prop/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lex_prop_assessment(
    payload: LexPropCreate,
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    result = analyze_lex_prop(payload)
    assessment = LexPropAssessment(**payload.model_dump(), mock_result=result.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return AssessmentResponse(
        id=assessment.id,
        module="LexProp",
        created_at=assessment.created_at,
        result=result,
    )


@router.get(
    "/{module_slug}/assessments/{assessment_id}/report",
    response_class=HTMLResponse,
)
def get_assessment_report_html(
    module_slug: str,
    assessment_id: int,
    db: Session = Depends(get_db),
) -> str:
    assessment = _get_assessment(db, module_slug, assessment_id)
    context = build_report_context(module_slug, assessment)
    return render_report_html(context)


@router.get("/{module_slug}/assessments/{assessment_id}/report.pdf")
def get_assessment_report_pdf(
    module_slug: str,
    assessment_id: int,
    db: Session = Depends(get_db),
) -> Response:
    assessment = _get_assessment(db, module_slug, assessment_id)
    context = build_report_context(module_slug, assessment)
    html = render_report_html(context)
    pdf = render_report_pdf(html)
    filename = f"{module_slug}-assessment-{assessment_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_assessment(db: Session, module_slug: str, assessment_id: int):
    model = ASSESSMENT_MODELS.get(module_slug)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    assessment = db.get(model, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment
