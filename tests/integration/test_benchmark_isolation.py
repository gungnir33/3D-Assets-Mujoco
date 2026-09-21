import json
from pathlib import Path
import pytest
import trimesh
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert, ValidationFailed
from asset_mujoco.manifest import checked_report
import asset_mujoco.validation as validation

def request(tmp_path):
    source=tmp_path/'box.glb'
    trimesh.creation.box().export(source)
    return ConversionRequest(input=source,output=tmp_path/'out',source_up='z',validation_level='full')

@pytest.mark.parametrize('native_passes',[True,False])
def test_benchmark_exception_keeps_native_and_render(tmp_path,monkeypatch,native_passes):
    original=validation.run_contact_case
    snapshots=[]
    def injected(package,req,size,**kwargs):
        if kwargs.get('benchmark'):
            # 进入benchmark之前必须已持久化并可校验，不只是内存里的返回值。
            state=checked_report(package)
            assert state.physics==('passed' if native_passes else 'failed')
            snapshots.append((package/'physics_native_evidence.json').read_bytes())
            raise RuntimeError('injected benchmark failure')
        return original(package,req,size,initial_position=[0,0,1.026] if native_passes else None)
    monkeypatch.setattr(validation,'run_contact_case',injected)
    if native_passes:
        package=convert(request(tmp_path))
    else:
        with pytest.raises(ValidationFailed) as caught:
            convert(request(tmp_path))
        package=caught.value.package
    assert (package/'physics_native_evidence.json').read_bytes()==snapshots[0]
    state=checked_report(package)
    assert state.physics==('passed' if native_passes else 'failed')
    assert state.render=='passed' and not state.evidence_issues
    evidence=json.loads((package/'physics_evidence.json').read_text())
    assert evidence['benchmark']['exception']['type']=='RuntimeError'
    assert evidence['benchmark']['exception']['stage']=='benchmark.run_contact_case'
    assert 'injected' in evidence['benchmark']['exception']['message']
    if not native_passes:
        assert 'penetration=' in evidence['native']['error']
    # benchmark后续追加/损坏不使native证据失效。
    (package/'physics_benchmark.xml').write_text('later incomplete benchmark')
    assert checked_report(package).physics==state.physics

def test_native_exception_keeps_compile_never_passes(tmp_path,monkeypatch):
    original=validation.run_contact_case
    def injected(package,req,size,**kwargs):
        if not kwargs.get('benchmark'):
            raise ValueError('native initialization failed')
        return original(package,req,size,**kwargs)
    monkeypatch.setattr(validation,'run_contact_case',injected)
    with pytest.raises(ValidationFailed) as caught:
        convert(request(tmp_path))
    package=caught.value.package
    state=checked_report(package)
    assert state.compile==state.render=='passed'
    assert state.physics=='failed'
    assert state.validation_scope.evidence_status=='missing'
    assert state.evidence_issues==['scope: required_scope_files_not_bound']
    native=json.loads((package/'physics_native_evidence.json').read_text())['native']
    assert native['exception']['type']=='ValueError'
    assert native['status']=='failed'

def test_normal_benchmark_does_not_cover_native_failure(tmp_path):
    with pytest.raises(ValidationFailed) as caught:
        convert(request(tmp_path))
    package=caught.value.package
    evidence=json.loads((package/'physics_evidence.json').read_text())
    assert evidence['benchmark']['status']=='passed'
    assert evidence['status']=='failed'
    assert checked_report(package).physics=='failed'
    assert (package/'physics_native_evidence.json').is_file()

def test_evidence_io_failure_is_not_physics_failure(tmp_path,monkeypatch):
    original=Path.write_text
    def fail(path,*args,**kwargs):
        if 'physics_native_evidence' in path.name:
            raise OSError('injected disk full')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(Exception,match='EVIDENCE_IO_ERROR'):
        convert(request(tmp_path))
    assert not list((tmp_path/'out').glob('asset_*'))
    package=next((tmp_path/'out').glob('.staging-*'))
    assert checked_report(package).compile=='passed'
    assert checked_report(package).physics!='passed'

def test_benchmark_persistence_failure_keeps_native_but_blocks_publish(tmp_path,monkeypatch):
    run=validation.run_contact_case
    def gentle(package,req,size,**kwargs):
        return run(package,req,size,**kwargs,initial_position=[0,0,1.026])
    monkeypatch.setattr(validation,'run_contact_case',gentle)
    original=Path.write_text
    def fail(path,*args,**kwargs):
        if path.name=='benchmark_evidence.json':
            raise OSError('injected disk full')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(Exception,match='EVIDENCE_IO_ERROR'):
        convert(request(tmp_path))
    assert not list((tmp_path/'out').glob('asset_*'))
    package=next((tmp_path/'out').glob('.staging-*'))
    assert checked_report(package).physics=='passed'
    assert checked_report(package).compile=='passed'

def test_hash_persistence_io_error_does_not_relabel_physics(tmp_path,monkeypatch):
    def fail(*args,**kwargs):
        raise OSError('injected hash read error')
    monkeypatch.setattr(validation,'record_layer',fail)
    with pytest.raises(Exception,match='EVIDENCE_IO_ERROR'):
        convert(request(tmp_path))
    package=next((tmp_path/'out').glob('.staging-*'))
    assert checked_report(package).compile=='passed'
    assert checked_report(package).physics=='not_run'
