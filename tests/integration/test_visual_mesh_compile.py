import importlib.util
from pathlib import Path

def test_real_compile_matrix():
    spec=importlib.util.spec_from_file_location("probe",Path(__file__).parents[2]/"scripts/probe_mesh_compile.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report=mod.run()
    assert report["mujoco"]=="3.4.0"
    rows={(r["case"],r["strategy"]):r for r in report["rows"]}
    assert rows["box","default"]["forward"]=="passed"
    assert rows["plane_with_collision","shell"]["forward"]=="passed"
    assert rows["six_material_faces","shell"]["forward"]=="passed"
    assert rows["triangle","shell"]["compile"]=="failed"
    for row in report["rows"]:
        if row["compile"]=="passed":
            assert row["explicit_mass"]==2
            assert row["explicit_inertia"]==[1,1,1]
