from asset_mujoco.manifest import fingerprint, review_status

def test_approval_invalidated(tmp_path):
    (tmp_path/"model.xml").write_text("original")
    review = {"decision":"approved","package_content_sha256":fingerprint(tmp_path)}
    assert review_status(tmp_path,review)=="approved"
    (tmp_path/"model.xml").write_text("changed")
    assert review_status(tmp_path,review)=="pending"

def test_review_does_not_hash_itself(tmp_path):
    before = fingerprint(tmp_path)
    (tmp_path/"appearance_review.json").write_text("{}")
    assert fingerprint(tmp_path)==before
