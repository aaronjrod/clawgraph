"""Tests for clawgraph.bag.skills — SkillsContextManager."""

from pathlib import Path

from clawgraph.bag.node import ClawNodeMetadata
from clawgraph.bag.skills import SkillsContextManager

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_skill_dir(tmp_path: Path) -> Path:
    """Create a temp skills directory with sample .md files."""
    skills = tmp_path / "skills"
    skills.mkdir()

    # Create subdirectory with a skill file.
    ops = skills / "clinical_ops"
    ops.mkdir()
    (ops / "patient_tracking.md").write_text("# Patient Tracking\nTrack patients daily.\n")
    (ops / "deviation_report.md").write_text("# Deviation Reporting\nLog deviations.\n")
    return skills


# ── Load Skill ────────────────────────────────────────────────────────────────


class TestLoadSkill:
    def test_load_existing_skill(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        content = scm.load_skill("clinical_ops/patient_tracking.md")
        assert "Patient Tracking" in content
        assert "Track patients daily." in content

    def test_load_nonexistent_skill(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        content = scm.load_skill("nonexistent.md")
        assert "<skill not found:" in content

    def test_load_caches_result(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        content1 = scm.load_skill("clinical_ops/patient_tracking.md")
        content2 = scm.load_skill("clinical_ops/patient_tracking.md")
        assert content1 == content2
        assert len(scm._cache) == 1

    def test_no_skills_dir_raises(self) -> None:
        scm = SkillsContextManager()
        try:
            scm.load_skill("anything.md")
            assert False, "Should have raised ValueError"  # noqa: B011
        except ValueError as exc:
            assert "No skills_dir" in str(exc)


# ── Load Skills for Node ──────────────────────────────────────────────────────


class TestLoadSkillsForNode:
    def test_load_multiple_skills(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        meta = ClawNodeMetadata(
            id="test_node",
            description="Test",
            bag="test",
            skills=[
                "clinical_ops/patient_tracking.md",
                "clinical_ops/deviation_report.md",
            ],
        )
        result = scm.load_skills_for_node(meta)
        assert "Patient Tracking" in result
        assert "Deviation Reporting" in result
        assert "--- Skill:" in result

    def test_no_skills_returns_empty(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        meta = ClawNodeMetadata(
            id="test_node",
            description="Test",
            bag="test",
            skills=[],
        )
        assert scm.load_skills_for_node(meta) == ""

    def test_dict_metadata(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        meta_dict = {"skills": ["clinical_ops/patient_tracking.md"]}
        result = scm.load_skills_for_node(meta_dict)
        assert "Patient Tracking" in result


# ── Set Skills Dir ────────────────────────────────────────────────────────────


class TestSetSkillsDir:
    def test_set_clears_cache(self, tmp_path: Path) -> None:
        skills_dir = _make_skill_dir(tmp_path)
        scm = SkillsContextManager(skills_dir=skills_dir)
        scm.load_skill("clinical_ops/patient_tracking.md")
        assert len(scm._cache) == 1

        scm.set_skills_dir(tmp_path / "other")
        assert len(scm._cache) == 0


class TestRepr:
    def test_repr_with_dir(self, tmp_path: Path) -> None:
        scm = SkillsContextManager(skills_dir=tmp_path)
        r = repr(scm)
        assert "SkillsContextManager" in r
        assert str(tmp_path) in r

    def test_repr_no_dir(self) -> None:
        scm = SkillsContextManager()
        assert "<not set>" in repr(scm)
