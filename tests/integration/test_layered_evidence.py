import json
import shutil
from pathlib import Path
import pytest
import trimesh
import numpy as np
from PIL import Image
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert
from asset_mujoco.cli import main

def compiled_package(tmp_path,textured=False):
    mesh=trimesh.creation.box()
    if textured:
        mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),
          material=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new("RGB",(4,4),"white"),baseColorFactor=[1,1,1,1]))
    source=tmp_path/"box.glb"
    mesh.export(source)
    return convert(ConversionRequest(input=source,output=tmp_path/"out",validation_level="compile"))

def report(package,capsys):
    assert main(["report",str(package)])==0
    return json.loads(capsys.readouterr().out)

@pytest.mark.parametrize("mutation",["xml","mesh","texture"])
def test_compile_only_content_change_invalidates(tmp_path,capsys,mutation):
    package=compiled_package(tmp_path,textured=True)
    assert report(package,capsys)["status"]=="COMPILE_VALIDATED"
    if mutation=="xml":
        (package/"model.xml").write_text("<broken>")
    elif mutation=="mesh":
        with (package/"meshes/visual_000.obj").open("a") as file:
            file.write("\nv 9 9 9\n")
    else:
        (package/"textures/visual_000.png").unlink()
    current=report(package,capsys)
    assert current["status"]!="COMPILE_VALIDATED"
    assert current["compile"]!="passed"

def test_move_preserves_compile_evidence(tmp_path,capsys):
    package=compiled_package(tmp_path)
    moved=tmp_path/"moved"
    shutil.copytree(package,moved)
    assert report(moved,capsys)["status"]=="COMPILE_VALIDATED"

def test_legacy_evidence_is_insufficient(tmp_path,capsys):
    package=tmp_path/"legacy"
    package.mkdir()
    (package/"validation_report.json").write_text('{"compile":"passed"}')
    assert report(package,capsys)["compile"]!="passed"

def test_render_and_review_bound_to_previews(tmp_path,capsys):
    from asset_mujoco.rendering import render_package
    from asset_mujoco.manifest import record_layer,compile_resources,save_review
    from asset_mujoco.contracts import ValidationResult
    package=compiled_package(tmp_path)
    rendered=render_package(package,[1,1,1])
    record_layer(package,"render","passed",compile_resources(package)+["render_config.json","render_evidence.json"]+rendered["images"],{"backend":rendered["backend"]})
    state=ValidationResult(compile="passed",render="passed")
    (package/"validation_report.json").write_text(state.model_dump_json())
    save_review(package,"synthetic-test-reviewer","approved",["previews/iso.png"])
    before=report(package,capsys)
    assert before["appearance_review"]=="approved"
    assert before["render"]=="passed"
    Image.new("RGB",(512,512),"red").save(package/"previews/iso.png")
    after=report(package,capsys)
    assert after["render"]=="not_run"
    assert after["appearance_review"]=="pending"
    assert after["compile"]=="passed"

def test_summary_and_log_do_not_invalidate_compile(tmp_path,capsys):
    package=compiled_package(tmp_path)
    (package/"conversion.log").write_text("additional diagnostic")
    (package/"aggregate_status.json").write_text("{}")
    assert report(package,capsys)["compile"]=="passed"
