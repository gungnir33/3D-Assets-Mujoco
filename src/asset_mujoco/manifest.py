"""内容寻址的人工审查；不信任缓存的 approved。"""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
import math

class EvidenceIOError(OSError):
    """证据未可靠保存；不能以物理通过发布包。"""

def write_evidence(root,name,value):
    try:
        (Path(root)/name).write_text(json.dumps(value,indent=2,allow_nan=False))
    except OSError as error:
        raise EvidenceIOError(f"EVIDENCE_IO_ERROR: {name}: {error}") from error

def content_manifest(root,paths):
    """稳定的包相对路径→内容哈希；不允许越界、链接或缺失文件。"""
    root=Path(root).resolve()
    files={}
    for relative in sorted(set(paths)):
        path=root/relative
        resolved=path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved!=path or not resolved.is_file():
            raise ValueError("无效包内资源: "+relative)
        files[relative]=hashlib.sha256(resolved.read_bytes()).hexdigest()
    return files

def compile_resources(root):
    paths={"model.xml","scene.xml","conversion_manifest.json"}
    documents=['model.xml','scene.xml']
    if (Path(root)/'contact_scene.xml').is_file():
        documents.append('contact_scene.xml')
        paths.add('contact_scene.xml')
    for name in documents:
        tree=ET.parse(Path(root)/name)
        compiler=tree.getroot().find("compiler")
        for node in tree.iter():
            if "file" in node.attrib:
                directory=""
                if compiler is not None:
                    directory=compiler.get("meshdir" if node.tag=="mesh" else "texturedir","")
                paths.add((Path(directory)/node.get("file")).as_posix())
    return sorted(paths)

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def record_layer(root,layer,status,paths,context):
    """只在真正完成相应引擎检查后调用；report 绝不调用。"""
    root=Path(root)
    target=root/"evidence_manifest.json"
    document=json.loads(target.read_text()) if target.exists() else {"schema_version":2,"layers":{}}
    entry={"status":status,"files":content_manifest(root,paths),"context":context}
    entry["sha256"]=_digest(entry)
    document["layers"][layer]=entry
    write_evidence(root,target.name,document)
    return entry

SCOPE_FIELDS=('contact_profile','validation_scope','followup_ground','application_force_limit',
              'host_integration','robot_contact_safety','physics_error','limitations')

def _scope_projection(root,result,verified,document):
    """只从已核对的层取事实；无引擎调用、无写入、无按名称补签。"""
    from .contracts import ValidationScope,GroundObservation
    result.contact_profile=None
    result.validation_scope=ValidationScope()
    result.followup_ground=GroundObservation()
    result.physics_error=None
    result.application_force_limit='not_specified'
    result.host_integration='pending'
    result.robot_contact_safety='not_validated'
    result.limitations=['SCOPED_TO_DECLARED_CONTACT_CASE','WHOLE_SCENE_NOT_VALIDATED',
        'HOST_INTEGRATION_PENDING','ROBOT_CONTACT_SAFETY_NOT_VALIDATED','APPLICATION_FORCE_LIMIT_NOT_SPECIFIED']

    def insufficient(status,reason):
        result.validation_scope.evidence_status=status
        result.evidence_issues.append('scope: '+reason)
        result.limitations.append('SCOPE_EVIDENCE_INSUFFICIENT')

    if 'compile' not in verified:
        insufficient('stale' if document.get('layers') else 'missing','compile_basis_unavailable')
        return
    meta=json.loads((root/'conversion_manifest.json').read_text())
    request=meta.get('request',{})
    profile=request.get('contact_profile')
    declared=meta.get('contact_profile',{}).get('id')
    result.contact_profile=profile if profile is not None else declared
    body=request.get('body_mode')
    from .collision_scope import resolve_collision_case,validate_collision_mapping
    try:
        case=resolve_collision_case(meta)
        validate_collision_mapping(root,meta,('model.xml','scene.xml'))
    except (ValueError,KeyError,TypeError) as error:
        insufficient('contradictory','collision_case_conflict: '+str(error))
        return
    pair=case['required_pairs'][0] if case['required_pairs'] else []
    result.limitations.extend(case['limitations'])
    result.validation_scope=ValidationScope(
        case_id=case['case_id'],required_pairs=case['required_pairs'],
        evidence_status='declared',evidence_refs={'conversion_manifest.json':verified['compile']['files']['conversion_manifest.json']})
    if 'physics' not in verified:
        if any(s.startswith('physics:') for s in result.evidence_issues):
            insufficient('stale','native_layer_unavailable')
        return
    entry=verified['physics']
    primary=entry['context'].get('native_evidence','physics_evidence.json')
    native=json.loads((root/primary).read_text()).get('native',{})
    result.physics_error=native.get('error')
    needed={primary,'physics_native.xml','contact_result_manifest.json','conversion_manifest.json'}
    if result.contact_profile=='engineering_static_v1':
        needed.add('contact_scene.xml')
    if not needed.issubset(entry['files']):
        insufficient('missing','required_scope_files_not_bound')
        return
    contact=json.loads((root/'contact_result_manifest.json').read_text())
    result.validation_scope.evidence_refs={p:entry['files'][p] for p in sorted(needed)}
    try:
        if not pair or not result.contact_profile or (profile is not None and declared is not None and profile!=declared):
            raise ValueError('missing_or_conflicting_declaration')
        if native.get('kind')!='native' or native.get('status')!=entry['status'] or native['expected_pair']!=pair:
            raise ValueError('native_case_conflict')
        if native['profile_contract']['id']!=result.contact_profile or contact['contact_profile']!=result.contact_profile:
            raise ValueError('profile_conflict')
        mirror={'acceptance_scope':'acceptance_scope','followup_ground':'followup_ground',
                'contact_statistics':'contact_statistics','resolved_geoms':'objects',
                'first_resolved_contact':'resolved_contact','profile_contract':'contract'}
        if any(native[a]!=contact[b] for a,b in mirror.items()):
            raise ValueError('native_contact_manifest_conflict')
        if request.get('collision_mode')=='supplied':
            validate_collision_mapping(root,meta,('physics_native.xml',))
            for key, expected in (('collision_case',case),('body_mode',body),
                                  ('target_index',request['validation_collision_part'])):
                if native.get(key)!=expected or contact.get(key)!=expected:
                    raise ValueError('supplied_case_manifest_conflict')
            observations=native['contact_statistics']['per_collision_part']
            if set(observations)!=set(case['collision_geoms']):
                raise ValueError('supplied_observation_set_conflict')
            if not set(case['collision_geoms']).issubset(native['resolved_geoms']):
                raise ValueError('supplied_resolved_geoms_conflict')
            for name, observation in observations.items():
                if observation.get('force_object')!=name or observation.get('mandatory')!=(name==case['target_geom']):
                    raise ValueError('supplied_observation_target_conflict')
            selected=observations[case['target_geom']]
            if selected['contact_records']!=native['contact_count'] or not math.isclose(
                    selected['max_penetration_m'],native['max_penetration_m'],rel_tol=1e-9,abs_tol=1e-12):
                raise ValueError('supplied_observation_native_conflict')
        if not native['acceptance_scope'].startswith(':'.join(pair)+';'):
            raise ValueError('scope_pair_conflict')
        for key in ('dt','steps','time','penetration_limit_m'):
            if not isinstance(native[key],(int,float)) or not math.isfinite(native[key]) or native[key]<=0:
                raise ValueError('invalid_native_condition_'+key)
        if not math.isclose(native['time'],native['steps']*native['dt'],rel_tol=1e-8,abs_tol=1e-10):
            raise ValueError('native_duration_conflict')
        ground=native['followup_ground']
        if ground['mandatory_for_physics'] is not False or ground['comparison_threshold_m']!=native['penetration_limit_m']:
            raise ValueError('ground_contract_conflict')
        if contact.get('application_force_limit')!='not_specified':
            raise ValueError('unsupported_force_limit_claim')
        fixture=ET.parse(root/'physics_native.xml').getroot()
        option=fixture.find('option')
        probe=fixture.find(".//body[@name='probe_body']")
        if any(len(fixture.findall(".//geom[@name='"+name+"']"))!=1 for name in pair):
            raise ValueError('fixture_required_pair_conflict')
        if option is None or not math.isclose(float(option.get('timestep','nan')),native['dt'],rel_tol=1e-12):
            raise ValueError('fixture_timestep_conflict')
        if fixture.find('.//pair') is not None:
            raise ValueError('fixture_forced_pair_conflict')
        flags=option.find('flag')
        if flags is None or flags.get('energy')!='enable' or flags.get('autoreset')!='disable' or flags.get('override')=='enable':
            raise ValueError('fixture_solver_flags_conflict')
        if body=='static':
            position=[float(v) for v in probe.get('pos','').split()] if probe is not None else []
            if position!=native['initial_position']:
                raise ValueError('fixture_initial_position_conflict')
        if result.contact_profile=='engineering_static_v1':
            delivered=ET.parse(root/'contact_scene.xml').getroot()
            if ET.tostring(fixture)!=ET.tostring(delivered):
                raise ValueError('fixture_delivered_contact_scene_conflict')
        result.validation_scope.conditions={
            key:native[key] for key in ('dt','steps','time','initial_position','penetration_limit_m','mujoco',
                                      'resolved_geoms','first_resolved_contact')}
        result.validation_scope.conditions.update(
            fixture='physics_native.xml',acceptance_scope=native['acceptance_scope'],
            option=dict(option.attrib) if option is not None else {},
            option_flags=dict(option.find('flag').attrib) if option is not None and option.find('flag') is not None else {},
            probe_fixture=ET.tostring(probe,encoding='unicode') if probe is not None else None)
        result.followup_ground=GroundObservation(status=ground['status'],mandatory_for_physics=False,
            comparison_threshold_m=ground['comparison_threshold_m'],
            evidence_refs={p:entry['files'][p] for p in (primary,'contact_result_manifest.json')})
        result.validation_scope.evidence_status='verified'
        if ground['status']=='failed':
            result.limitations.append('FOLLOWUP_GROUND_FAILED')
    except (KeyError,TypeError,ValueError,ET.ParseError) as error:
        insufficient('contradictory',str(error))

def checked_report(root):
    return _build_report(Path(root),check_projection=True)

def refresh_report(root):
    """仅供新包引擎写路径；派生投影不重签层证据。历史report禁止调用。"""
    result=_build_report(Path(root),check_projection=False)
    write_evidence(root,'validation_report.json',result.model_dump())
    return result

def _build_report(root,*,check_projection):
    from .contracts import ValidationResult
    raw=json.loads((root/'validation_report.json').read_text())
    result=ValidationResult.model_validate(raw)
    result.evidence_issues=[]
    result.render_error=None
    target=root/"evidence_manifest.json"
    try:
        document=json.loads(target.read_text())
        if document.get("schema_version")!=2:
            raise ValueError("不支持的证据格式")
    except (OSError,ValueError):
        document={"layers":{}}
    verified={}
    layer_conflicts=[]
    for layer in ("compile","physics","render"):
        cached_state=getattr(result,layer)
        entry=document.get("layers",{}).get(layer)
        state=entry.get('status') if entry else cached_state
        if state not in (("passed","failed","unavailable") if layer=='render' else ("passed","failed")):
            if entry:
                # 非终态/未知状态的绑定层不能跳过核对后沿用缓存passed。
                setattr(result,layer,'not_run')
                result.evidence_issues.append(layer+': invalid_bound_layer_status')
            continue
        valid=False
        if entry and entry.get("files"):
            try:
                body={key:entry[key] for key in ("status","files","context")}
                valid=entry.get("sha256")==_digest(body) and content_manifest(root,entry["files"])==entry["files"]
                required={"model.xml","scene.xml","conversion_manifest.json"}
                if layer=="physics":
                    primary=entry['context'].get('native_evidence','physics_evidence.json')
                    required.add(primary)
                    if state=='passed' or primary=='physics_evidence.json':
                        required.add('physics_native.xml')
                if layer=="render":
                    failure=entry['context'].get('failure_evidence')
                    if state in ('failed','unavailable') and failure=='render_failure.json':
                        required.add(failure)
                        diagnostic=json.loads((root/failure).read_text())
                        valid=valid and diagnostic.get('status')==state and isinstance(diagnostic.get('error'),dict)
                        if valid:
                            result.render_error=diagnostic['error']['message']
                    else:
                        required|={"render_config.json","render_evidence.json","previews/front.png","previews/side.png","previews/iso.png","previews/collision.png"}
                valid=valid and required.issubset(entry["files"])
                if layer=="physics":
                    evidence=json.loads((root/primary).read_text())
                    valid=valid and evidence.get("native",{}).get("status")==state
                    if state=='passed':
                        valid=valid and result.asset_physics_sha256==entry['sha256']
            except (OSError,ValueError,KeyError):
                valid=False
        if not valid:
            setattr(result,layer,"not_run")
            result.evidence_issues.append(layer+": missing_or_stale_evidence")
        else:
            verified[layer]=entry
            setattr(result,layer,state)
            if check_projection and cached_state!=state:
                layer_conflicts.append(layer)
                result.evidence_issues.append(layer+': cached_state_conflicts_with_bound_evidence')
    if result.compile!="passed":
        for layer in ("physics","render"):
            if getattr(result,layer)=="passed":
                setattr(result,layer,"not_run")
    _scope_projection(root,result,verified,document)
    if 'physics' in layer_conflicts:
        result.validation_scope.evidence_status='contradictory'
        result.limitations.append('SCOPE_EVIDENCE_INSUFFICIENT')
    bound_scope_version=None
    if 'compile' in verified:
        bound_scope_version=json.loads((root/'conversion_manifest.json').read_text()).get('scope_reporting_version')
    if check_projection and (raw.get('scope_report_version')==1 or bound_scope_version==1) and not result.evidence_issues:
        derived=result.model_dump()
        if any(raw.get(key)!=derived[key] for key in SCOPE_FIELDS):
            result.validation_scope.evidence_status='contradictory'
            result.evidence_issues.append('scope: cached_projection_conflicts_with_bound_evidence')
            result.limitations.append('SCOPE_EVIDENCE_INSUFFICIENT')
    result.scope_report_version=1
    review=root/"appearance_review.json"
    result.appearance_review=review_status(root,json.loads(review.read_text())) if review.exists() else "pending"
    if result.evidence_issues:
        result.appearance_review="pending"
    return result

def asset_signature(root):
    root=Path(root)
    digest=hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative=path.relative_to(root)
        if path.is_file() and relative.parts[0]!="previews" and path.suffix in (".xml",".obj",".png"):
            digest.update(relative.as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()

def fingerprint(root):
    root=Path(root)
    entries=[]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("包内禁止符号链接")
        if path.is_file() and path.relative_to(root).as_posix() not in ("appearance_review.json","aggregate_status.json"):
            entries.append((path.relative_to(root).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(entries,separators=(",",":")).encode()).hexdigest()

def review_status(root, review):
    if not review.get("reviewer") or not review.get("timestamp") or not review.get("images"):
        return "pending"
    if review.get("package_content_sha256") != fingerprint(root):
        return "pending"
    return review.get("decision") if review.get("decision") in ("approved","rejected") else "pending"

def save_review(root,reviewer,decision,images):
    root=Path(root)
    if not reviewer.strip() or decision not in ("approved","rejected") or not images:
        raise ValueError("人工审核必须有审核人、结论和查看图片")
    hashes={}
    for relative in images:
        path=(root/relative).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("审核图片越界")
        hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    file=root/"appearance_review.json"
    previous=json.loads(file.read_text()) if file.exists() else None
    history=[]
    if previous:
        history=previous.pop("history",[])+[previous]
    record={"schema_version":1,"reviewer":reviewer,"timestamp":datetime.now(timezone.utc).isoformat(),
            "decision":decision,"images":hashes,"package_content_sha256":fingerprint(root),"history":history}
    file.write_text(json.dumps(record,indent=2))
    return record
