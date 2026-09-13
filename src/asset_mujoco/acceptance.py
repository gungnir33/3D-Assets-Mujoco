"""显式真实资产验收；与已知失败处理的pytest回归分开。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import mujoco
from .contracts import ConversionRequest
from .pipeline import convert,ValidationFailed
from .manifest import checked_report,fingerprint,write_evidence

DEFAULT_INPUT=Path('/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb')

def run_acceptance(source,output,contact_profile='preserve'):
    source=Path(source)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='acceptance-',dir=output))
    report={'run_directory':str(root),'automatic_validation':'not_executed','exit_code':2,
            'contact_profile':contact_profile,'application_force_limit':'not_specified',
            'appearance_review':'pending','host_integration':'pending'}
    if not source.is_file():
        report['reason']='REAL_INPUT_UNAVAILABLE'
        write_evidence(root,'acceptance.json',report)
        return report
    if source.suffix.lower()!='.glb':
        report['reason']='REAL_ACCEPTANCE_REQUIRES_ORIGINAL_GLB'
        write_evidence(root,'acceptance.json',report)
        return report
    source=source.resolve()
    report['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    started=time.monotonic()
    try:
        try:
            package=convert(ConversionRequest(input=source,output=root/'packages',name='penguin',
                source_up='y',yaw_deg=180,scale=.5,body_mode='static',collision_mode='hull',validation_level='full',
                contact_profile=contact_profile))
        except ValidationFailed as error:
            # 仅为保留路径和继续迁移诊断；下方仍非零失败，绝不改算成功。
            package=error.package
            report['conversion_error']=str(error)
        state=checked_report(package)
        report.update(state.model_dump())
        report['package']=str(package)
        evidence=json.loads((package/'physics_evidence.json').read_text())
        report['benchmark']=evidence['benchmark']
        report['native']=evidence['native']
        relocated=root/'relocated_package'
        shutil.copytree(package,relocated)
        rows=[]
        for location in (package,relocated):
            for name in ('model.xml','scene.xml')+(('contact_scene.xml',) if (package/'contact_scene.xml').is_file() else ()):
                model=mujoco.MjModel.from_xml_path(str(location/name))
                mujoco.mj_forward(model,mujoco.MjData(model))
                rows.append({'path':str(location/name),'compile':'passed','forward':'passed'})
        equal=fingerprint(package)==fingerprint(relocated) and checked_report(relocated)==state
        report['migration']={'status':'passed' if equal else 'failed','xml':rows}
        report['package_sha256']=fingerprint(package)
        report['source_unchanged']=report['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
        passed=all(getattr(state,k)=='passed' for k in ('compile','physics','render'))
        passed=passed and evidence['native']['status']=='passed' and equal and report['source_unchanged'] and not state.evidence_issues
        report['automatic_validation']='passed' if passed else 'failed'
        report['exit_code']=0 if passed else 5
    except Exception as error:
        report.update(automatic_validation='failed',exit_code=5,error={'type':type(error).__name__,'message':str(error)})
    report['duration_s']=time.monotonic()-started
    write_evidence(root,'acceptance.json',report)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=DEFAULT_INPUT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contact-profile',choices=['preserve','engineering_static_v1'],default='preserve')
    args=parser.parse_args()
    report=run_acceptance(args.input,args.output,args.contact_profile)
    print(json.dumps(report,ensure_ascii=False))
    return report['exit_code']

if __name__=='__main__':
    raise SystemExit(main())
