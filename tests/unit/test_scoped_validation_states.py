import pytest
from asset_mujoco.contracts import ValidationResult


def scoped(**changes):
    fields=dict(compile='passed',physics='passed',render='passed',asset_physics_sha256='a'*64,
        contact_profile='engineering_static_v1',
        validation_scope={'case_id':'native_asset_probe_v1','required_pairs':[['asset_collision','probe']],
            'evidence_status':'verified','evidence_refs':{'physics_native.xml':'b'*64}},
        followup_ground={'status':'failed','mandatory_for_physics':False,'comparison_threshold_m':.005})
    fields.update(changes)
    return ValidationResult(**fields)


@pytest.mark.parametrize('review,status',[
    ('pending','SCOPED_PHYSICS_VALIDATED'),('approved','SCOPED_FULLY_VALIDATED'),
    ('rejected','SCOPED_PHYSICS_VALIDATED')])
def test_appearance_never_expands_scope(review,status):
    result=scoped(appearance_review=review)
    assert result.aggregate()==status
    payload=result.model_dump()
    assert payload['status']==status
    assert payload['followup_ground']['status']=='failed'
    assert payload['host_integration']=='pending'
    assert payload['robot_contact_safety']=='not_validated'
    assert payload['application_force_limit']=='not_specified'
    assert ValidationResult.model_validate_json(result.model_dump_json()).aggregate()==status


@pytest.mark.parametrize('evidence',['unknown','declared','missing','stale','contradictory'])
def test_no_scoped_or_bare_success_without_verified_scope(evidence):
    result=scoped(validation_scope={'evidence_status':evidence},appearance_review='approved')
    assert result.aggregate()=='INVALID_EVIDENCE'


def test_native_failure_and_nonphysical_levels():
    assert scoped(physics='failed').aggregate()=='FAILED'
    assert scoped(physics='not_run',validation_scope={'evidence_status':'declared'}).aggregate()=='COMPILE_VALIDATED'
    assert scoped(physics='not_applicable').aggregate()=='VISUAL_ONLY'
    assert ValidationResult(compile='passed',physics='passed',render='passed',
        asset_physics_sha256='a'*64,appearance_review='approved').aggregate()=='INVALID_EVIDENCE'
