from pathlib import Path
from packaging.requirements import Requirement

def test_lock_contains_only_pinned_requirements():
    path=Path(__file__).parents[2]/"requirements.lock.txt"
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement=Requirement(line)
        assert any(s.operator=="==" for s in requirement.specifier)
