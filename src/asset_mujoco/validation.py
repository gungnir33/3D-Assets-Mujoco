"""原始碰撞配置是验收；强制 contact pair 只属于独立 benchmark。"""
import xml.etree.ElementTree as ET
import json
import mujoco
import numpy as np
from .manifest import record_layer,compile_resources,write_evidence,EvidenceIOError,refresh_report
from .contact_profiles import ENGINEERING_SOLREF,ENGINEERING_SOLIMP
from .contact_statistics import ContactStatistics

def check_state(model,data,step,expected_time):
    arrays=(data.qpos,data.qvel,data.qacc,data.energy)
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError("NONFINITE_STATE first_step="+str(step))
    if not np.isclose(data.time,expected_time,rtol=1e-8,atol=1e-10):
        raise ValueError("TIME_RESET_OR_DRIFT first_step="+str(step))
    if np.any(data.warning.number):
        raise ValueError("SIMULATION_WARNING first_step="+str(step)+" counters="+str(data.warning.number))

def run_contact_case(package,request,size,*,benchmark=False,initial_position=None):
    from .collision_scope import resolve_collision_case
    case=resolve_collision_case(json.loads((package/'conversion_manifest.json').read_text()))
    if not case['required_pairs']:
        raise ValueError('COLLISION_SCOPE_TARGET_REQUIRED')
    pair=tuple(case['required_pairs'][0])
    supplied=request.collision_mode=='supplied'
    engineering=request.contact_profile!='preserve'
    root=ET.parse(package/('contact_scene.xml' if engineering else 'scene.xml')).getroot()
    world=root.find("worldbody")
    if engineering:
        if initial_position is not None:
            raise ValueError('candidate native validation must use delivered probe conditions')
        initial_position=np.fromstring(world.find("body[@name='probe_body']").get('pos'),sep=' ').tolist()
    elif request.body_mode=="static":
        radius=max(size)*.025
        initial_position=list(initial_position) if initial_position is not None else [0,0,size[2]+max(size)*.2+radius]
        body=ET.SubElement(world,"body",name="probe_body",pos=" ".join(map(str,initial_position)))
        ET.SubElement(body,"freejoint")
        inertia=.4*.1*radius**2
        ET.SubElement(body,"inertial",pos="0 0 0",mass=".1",diaginertia=f"{inertia} {inertia} {inertia}")
        ET.SubElement(body,"geom",name="probe",type="sphere",size=str(radius),mass=".1")
    else:
        body=world.find("body")
        initial_position=list(initial_position) if initial_position is not None else [0,0,max(size)*.1]
        body.set("pos"," ".join(map(str,initial_position)))
    if root.find(".//pair") is not None:
        raise ValueError("原始配置验收不接受已有强制接触 pair")
    if benchmark:
        contact=ET.SubElement(root,"contact")
        ET.SubElement(contact,"pair",geom1=pair[0],geom2=pair[1],solref=".004 1",solimp=".99 .99 .001")
    kind="benchmark" if benchmark else "native"
    testfile=package/("physics_"+kind+".xml")
    ET.ElementTree(root).write(testfile)
    model=mujoco.MjModel.from_xml_path(str(testfile))
    if not model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ENERGY):
        raise ValueError("能量计算未启用")
    if not model.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_AUTORESET):
        raise ValueError("autoreset 未禁用")
    if model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_OVERRIDE):
        raise ValueError("不接受全局接触参数 override")
    data=mujoco.MjData(model)
    check_state(model,data,0,0)
    mujoco.mj_forward(model,data)
    check_state(model,data,0,0)
    ids={model.geom(name).id for name in pair}
    count=0
    first_contact=None
    last_contact=None
    resolved_contact=None
    worst=0.
    abnormal=None
    error=None
    step=0
    limit=min(.005,.02*size[2])
    statistics=ContactStatistics(collision_geoms=case['collision_geoms'] if supplied else None,
                                 target_geom=case['target_geom'])
    for step in range(1,1001):
        try:
            qvel_before=data.qvel.copy()
            sample_time=float(data.time)
            mujoco.mj_step(model,data)
            statistics.sample(model,data,qvel_before,step,sample_time,float(model.opt.timestep))
            check_state(model,data,step,step*model.opt.timestep)
        except ValueError as exc:
            abnormal=abnormal or step
            error=str(exc)
            break
        for contact in data.contact:
            if {int(contact.geom1),int(contact.geom2)}==ids:
                if first_contact is None:
                    first_contact=step
                    resolved_contact={k:getattr(contact,k).tolist() for k in ("solref","solimp","friction")}
                last_contact=step
                count+=1
                worst=min(worst,float(contact.dist))
                if (step<=1 or -float(contact.dist)>limit) and abnormal is None:
                    abnormal=step
    if count==0 or first_contact<=1:
        error=error or "ASSET_CONTACT_FAILED: 预期接触未发生或初始已穿透"
        abnormal=abnormal or step
    if -worst>limit:
        error=error or "ASSET_CONTACT_FAILED: penetration="+str(-worst)
    geoms={}
    for name in set(pair)|set(case['collision_geoms'])|({'ground'} if engineering else set()):
        i=model.geom(name).id
        geoms[name]={k:np.asarray(getattr(model,"geom_"+k)[i]).tolist() for k in ("contype","conaffinity","friction","solref","solimp","pos","priority","solmix")}
    contract={'id':request.contact_profile,'matched':None,'application_force_limit':'not_specified'}
    if engineering:
        contract['matched']=all(np.allclose(g['solref'],ENGINEERING_SOLREF,atol=1e-12,rtol=0) and
            np.allclose(g['solimp'],ENGINEERING_SOLIMP,atol=1e-12,rtol=0) and g['priority']==0 and g['solmix']==1 for g in geoms.values())
        if not contract['matched'] and not benchmark:
            error=error or 'CONTACT_PROFILE_MISMATCH: delivered counterpart parameters do not match'
    ground=statistics.results['ground_probe']
    ground_status=('not_tested' if not ground['contact_records'] else
                   ('passed' if ground['max_penetration_m']<=limit and not np.any(data.warning.number) and
                    all(np.isfinite(a).all() for a in (data.qpos,data.qvel,data.qacc,data.energy)) else 'failed'))
    return {"kind":kind,"status":"failed" if error else "passed","error":error,
            **({'collision_case':case,'body_mode':request.body_mode,
                'target_index':request.validation_collision_part} if supplied else {}),
            'acceptance_scope':':'.join(pair)+'; unchanged baseline conditions',
            'followup_ground':{'status':ground_status,'mandatory_for_physics':False,
                'scope':'additional observation, not the baseline asset contact gate',
                'comparison_threshold_m':limit,'application_force_limit':'not_specified'},
            'profile_contract':contract,
            'contact_statistics':statistics.results,'application_force_limit':'not_specified',
            "steps":step,"dt":model.opt.timestep,"time":data.time,"expected_pair":list(pair),
            "initial_position":initial_position,"resolved_geoms":geoms,"first_resolved_contact":resolved_contact,
            "contact_count":count,"first_contact_step":first_contact,"last_contact_step":last_contact,"max_penetration_m":-worst,
            "penetration_limit_m":limit,"warning_counts":data.warning.number.tolist(),"first_abnormal_step":abnormal,
            "final_qpos":data.qpos.tolist(),"final_qvel":data.qvel.tolist(),"final_energy":data.energy.tolist(),
            "fixture":testfile.name,"mujoco":mujoco.__version__,
            "fixture_contact":{"solref":[.004,1],"solimp":[.99,.99,.001]} if benchmark else None}

def validate_physics(package,request,size):
    from .contracts import ValidationResult

    def run(kind):
        try:
            return run_contact_case(package,request,size,benchmark=(kind=='benchmark'))
        except OSError as error:
            # 包括fixture写入故障；不是接触精度失败，不能发布成功包。
            raise EvidenceIOError(f'EVIDENCE_IO_ERROR: {kind}: {error}') from error
        except Exception as error:
            return {'kind':kind,'status':'failed','error':str(error),
                    'exception':{'stage':kind+'.run_contact_case','type':type(error).__name__,'message':str(error)},
                    'diagnostic_files':[p.name for p in package.glob('physics_'+kind+'*') if p.is_file()]}

    native=run('native')
    write_evidence(package,'contact_result_manifest.json',{'contact_profile':request.contact_profile,
        'source':'actual_native_MuJoCo_run','objects':native.get('resolved_geoms',{}),
        'resolved_contact':native.get('first_resolved_contact'),'contract':native.get('profile_contract'),
        'contact_statistics':native.get('contact_statistics',{}),
        'acceptance_scope':native.get('acceptance_scope'),'followup_ground':native.get('followup_ground'),
        'application_force_limit':'not_specified',
        **({key:native.get(key) for key in ('collision_case','body_mode','target_index')}
           if request.collision_mode=='supplied' else {})})
    write_evidence(package,'physics_native_evidence.json',{'status':native['status'],'native':native})
    paths=compile_resources(package)+['physics_native_evidence.json','contact_result_manifest.json']
    if (package/'physics_native.xml').is_file():
        paths.append('physics_native.xml')
    entry=record_layer(package,'physics',native['status'],paths,
                       {'mujoco':mujoco.__version__,'required_case':'native','native_evidence':'physics_native_evidence.json'})
    state=ValidationResult.model_validate_json((package/'validation_report.json').read_text())
    state.physics=native['status']
    state.asset_physics_sha256=entry['sha256'] if native['status']=='passed' else None
    write_evidence(package,'validation_report.json',state.model_dump())
    refresh_report(package)
    # 此处native及其hash已经持久化，benchmark不是physics层的依赖。
    benchmark=run('benchmark')
    write_evidence(package,'benchmark_evidence.json',benchmark)
    combined={'status':native['status'],'native':native,'benchmark':benchmark,'asset_sha256':entry['sha256']}
    write_evidence(package,'physics_evidence.json',combined)
    return combined
