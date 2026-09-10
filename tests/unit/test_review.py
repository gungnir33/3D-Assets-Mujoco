from asset_mujoco.manifest import fingerprint, review_status, save_review

def test_approval_invalidated(tmp_path):
    (tmp_path/"model.xml").write_text("original")
    (tmp_path/"preview.png").write_bytes(b"reviewed image")
    review = save_review(tmp_path,"human","approved",["preview.png"])
    assert review_status(tmp_path,review)=="approved"
    (tmp_path/"model.xml").write_text("changed")
    assert review_status(tmp_path,review)=="pending"

def test_review_does_not_hash_itself(tmp_path):
    before = fingerprint(tmp_path)
    (tmp_path/"appearance_review.json").write_text("{}")
    assert fingerprint(tmp_path)==before

def test_review_history_preserved(tmp_path):
    (tmp_path/"preview.png").write_bytes(b"image")
    save_review(tmp_path,"first","rejected",["preview.png"])
    review=save_review(tmp_path,"second","approved",["preview.png"])
    assert review["history"][0]["reviewer"]=="first"
