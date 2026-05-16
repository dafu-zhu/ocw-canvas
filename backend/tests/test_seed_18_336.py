import httpx
import pytest

import seed.seed_18_336 as seed_mod
from app.models import Course
from seed.seed_18_336 import (
    BASE,
    CODE,
    DESCRIPTION,
    HOME,
    HOME_MD,
    LECTURE_HAS_PDF,
    LECTURE_TOPICS,
    PROBLEM_SETS,
    PROJECT_COVERS_FROM,
    PROJECT_COVERS_TO,
    SYLLABUS_MD,
    TEXTBOOK,
    UNITS,
    _hw_url,
    _lec_url,
    _modules,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """The 18.336 seed must never touch the network — no PDFs to download.
    This fixture turns any accidental httpx.get into a loud failure so we
    catch regressions if someone wires network calls into the seed."""
    def _boom(*a, **kw):
        raise AssertionError(
            "seed_18_336 must not make network calls; got "
            f"args={a}, kwargs={kw}"
        )

    monkeypatch.setattr(httpx, "get", _boom)
    yield


def test_code_and_base():
    assert CODE == "MIT 18.336"
    assert BASE == (
        "https://ocw.mit.edu/courses/"
        "18-336-numerical-methods-for-partial-differential-equations-spring-2009"
    )
    assert HOME == BASE + "/"


def test_lec_url_not_zero_padded():
    # Verified on OCW 2026-05-16: slug stem is `lec1`, not `lec01`.
    assert _lec_url(1) == BASE + "/resources/mit18_336s09_lec1/"
    assert _lec_url(9) == BASE + "/resources/mit18_336s09_lec9/"
    assert _lec_url(25) == BASE + "/resources/mit18_336s09_lec25/"


def test_hw_url_zero_padded():
    # Verified on OCW 2026-05-16: slug stem is `hw01`, not `hw1`.
    assert _hw_url(1) == BASE + "/resources/mit18_336s09_hw01/"
    assert _hw_url(5) == BASE + "/resources/mit18_336s09_hw05/"


def test_lecture_topics_cover_1_to_25():
    # 25 content lectures (Lec 26 = project presentations, not included).
    assert set(LECTURE_TOPICS.keys()) == set(range(1, 26))
    for _n, (topic, _readings) in LECTURE_TOPICS.items():
        assert topic, "lecture must have a topic string"


def test_lecture_has_pdf_excludes_lec8():
    # Lec 8 (FFT guest by Steven Johnson) has no published PDF on OCW; every
    # other lecture 1–25 does. Lec 26 is excluded from LECTURE_TOPICS entirely.
    assert 8 not in LECTURE_HAS_PDF
    assert LECTURE_HAS_PDF == set(range(1, 26)) - {8}


def test_problem_sets_shape():
    assert len(PROBLEM_SETS) == 5
    nums = [k for (k, _t, _f, _to) in PROBLEM_SETS]
    assert nums == [1, 2, 3, 4, 5]
    # Coverage must monotonically advance and end at lec 22 (Lec 23-25
    # is applications, covered by the project).
    last_to = 0
    for k, _topic, lec_from, lec_to in PROBLEM_SETS:
        assert lec_from > last_to, f"PS{k} from must follow previous to"
        assert lec_to >= lec_from
        last_to = lec_to
    assert last_to == 22


def test_project_coverage_span():
    assert PROJECT_COVERS_FROM == 1
    assert PROJECT_COVERS_TO == 25


def test_units_shape():
    # 4 unit modules with their lecture-number splits: 4 + 8 + 10 + 3 = 25
    assert len(UNITS) == 4
    counts = [len(nums) for _t, nums in UNITS]
    assert counts == [4, 8, 10, 3]
    # Union covers every content lecture 1-25 exactly once.
    seen: list[int] = []
    for _t, nums in UNITS:
        seen.extend(nums)
    assert seen == list(range(1, 26))


def test_modules_shape():
    mods = _modules()
    titles = [m[0] for m in mods]
    assert titles == [
        "Direct links",
        "Unit I — Foundations (Lec 1–4)",
        "Unit II — Elliptic problems & solvers (Lec 5–12)",
        "Unit III — Time-dependent problems (Lec 13–22)",
        "Unit IV — Applications (Lec 23–25)",
        "Course Project",
    ]


def test_modules_per_unit_counts():
    mods = dict(_modules())
    assert len(mods["Direct links"]) == 8
    assert len(mods["Unit I — Foundations (Lec 1–4)"]) == 4
    assert len(mods["Unit II — Elliptic problems & solvers (Lec 5–12)"]) == 8
    assert len(mods["Unit III — Time-dependent problems (Lec 13–22)"]) == 10
    assert len(mods["Unit IV — Applications (Lec 23–25)"]) == 3
    assert len(mods["Course Project"]) == 2


def test_modules_no_video_items():
    """Per feedback-module-content-chapter-readings Rule 1: no video items
    anywhere in Modules. This offering has no recorded videos at all."""
    for _title, items in _modules():
        for it in items:
            assert it["kind"] != "video"
            text_md = it.get("text_md", "") or ""
            assert "[Watch video" not in text_md
            url = it.get("url", "") or ""
            assert "/resources/lecture-" not in url


def test_lec8_note_omits_pdf_link():
    mods = dict(_modules())
    items = mods["Unit II — Elliptic problems & solvers (Lec 5–12)"]
    lec8 = next(it for it in items if it["title"].startswith("Lec 8 "))
    assert "Lecture notes PDF" not in lec8["text_md"]
    # And there's no Readings line either (OCW lists none for Lec 8).
    assert "Readings:" not in lec8["text_md"]


def test_lec1_note_has_readings_and_pdf():
    mods = dict(_modules())
    items = mods["Unit I — Foundations (Lec 1–4)"]
    lec1 = next(it for it in items if it["title"].startswith("Lec 1 "))
    assert "Readings: Evans" in lec1["text_md"]
    assert "Lecture notes PDF" in lec1["text_md"]
    assert "mit18_336s09_lec1/" in lec1["text_md"]


def test_syllabus_contains_grading_split_and_no_exams():
    assert "50%" in SYLLABUS_MD
    assert "Homework" in SYLLABUS_MD
    assert "Course Project" in SYLLABUS_MD
    assert "no exams" in SYLLABUS_MD.lower()


def test_syllabus_lists_seven_textbooks():
    # Sanity: the bibliography mentions each textbook author.
    for needle in ("LeVeque", "Trefethen", "Evans", "Strang", "Fletcher", "Canuto"):
        assert needle in SYLLABUS_MD, f"syllabus must mention {needle}"


def test_home_md_mentions_seibold_and_self_study():
    assert "Seibold" in HOME_MD
    # term_label is the user's self-study term, not the OCW recording year.
    assert "self-study" in HOME_MD


def test_description_and_textbook_nonempty():
    assert "PDE" in DESCRIPTION or "differential" in DESCRIPTION.lower()
    assert "LeVeque" in TEXTBOOK
    assert "Trefethen" in TEXTBOOK


def test_seed_creates_18_336_basic_shape(db):
    c = seed(db)
    assert c.code == "MIT 18.336"
    assert c.title == "Numerical Methods for Partial Differential Equations"
    assert c.instructor == "Dr. Benjamin Seibold"
    assert c.institution == "Massachusetts Institute of Technology"
    assert c.term_label == "Summer 2029"
    assert c.color == "#1E5A6F"
    assert c.display_order == 5
    assert c.status == "planned"
    assert c.external_home_url == HOME


def test_seed_groups_and_weights(db):
    c = seed(db)
    weights = {g.name: (float(g.weight), g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Homework"] == (50.0, 0)
    assert weights["Course Project"] == (50.0, 0)
    assert sum(w for w, _ in weights.values()) == 100.0


def test_seed_assignment_counts(db):
    c = seed(db)
    n_modules = len(c.modules)
    n_items = sum(len(m.items) for m in c.modules)
    n_assign = len(c.assignments)
    # 6 modules (Direct links + 4 units + Course Project).
    # 6 assignments (5 PSets + 1 Course Project).
    # 8 direct links + 4 + 8 + 10 + 3 lecture notes + 2 project items = 35.
    assert n_modules == 6
    assert n_assign == 6
    assert n_items == 35


def test_seed_problem_set_coverage(db):
    c = seed(db)
    psets = sorted(
        (a for a in c.assignments if a.title.startswith("Problem Set")),
        key=lambda a: a.position,
    )
    assert len(psets) == 5
    # All PSets keep the default requires_solution_key=True (AI key flow).
    assert all(p.requires_solution_key for p in psets)
    assert psets[0].covers_lecture_from == 1
    assert psets[0].covers_lecture_to == 6
    assert psets[-1].covers_lecture_from == 17
    assert psets[-1].covers_lecture_to == 22


def test_seed_project_is_project_style(db):
    c = seed(db)
    proj = next(a for a in c.assignments if a.title == "Course Project")
    # Project-style: AI grades without generating a reference key.
    assert proj.requires_solution_key is False
    assert proj.covers_lecture_from == PROJECT_COVERS_FROM
    assert proj.covers_lecture_to == PROJECT_COVERS_TO
    # Description must surface the 'project mode' AI grading note.
    assert "project mode" in proj.description_md.lower()


def test_seed_is_idempotent(db):
    c1 = seed(db)
    n1 = (len(c1.modules), len(c1.assignments))
    c2 = seed(db)
    assert c2.id == c1.id
    assert (len(c2.modules), len(c2.assignments)) == n1
    assert db.query(Course).filter(Course.code == "MIT 18.336").count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == "MIT 18.336").count() == 1
    assert len(c.assignments) == 6


def test_update_urls_refreshes_module_items(db):
    c = seed(db)
    # Corrupt a fixed-title item URL to simulate drift.
    for m in c.modules:
        for it in m.items:
            if it.title == "Syllabus":
                it.external_url = "https://example.com/STALE"
    db.commit()

    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] >= 1

    # Syllabus URL is now correct again.
    found = False
    for m in c.modules:
        for it in m.items:
            if it.title == "Syllabus":
                assert it.external_url == seed_mod.SYLLABUS_URL
                found = True
    assert found


def test_update_urls_refreshes_lecture_note_bodies(db):
    c = seed(db)
    # Corrupt the Lec 5 note text and re-run update_urls.
    target = None
    for m in c.modules:
        for it in m.items:
            if (it.title or "").startswith("Lec 5 "):
                it.text_md = "STALE"
                target = it
    assert target is not None
    db.commit()

    counts = update_urls(db)
    assert counts["course_found"] is True
    db.refresh(target)
    assert "LeVeque 2007" in target.text_md
    assert "mit18_336s09_lec5/" in target.text_md


def test_update_urls_refreshes_assignment_fields(db):
    c = seed(db)
    ps1 = next(a for a in c.assignments if a.title.startswith("Problem Set 1 "))
    proj = next(a for a in c.assignments if a.title == "Course Project")
    ps1.description_md = "STALE"
    ps1.covers_lecture_from = 999
    ps1.covers_lecture_to = 999
    proj.description_md = "STALE-PROJ"
    db.commit()

    counts = update_urls(db)
    assert counts["assignments_updated"] >= 2
    assert counts["coverage_updated"] >= 1
    db.refresh(ps1)
    db.refresh(proj)
    assert ps1.description_md != "STALE"
    assert ps1.covers_lecture_from == 1
    assert ps1.covers_lecture_to == 6
    assert proj.description_md != "STALE-PROJ"
    assert "project mode" in proj.description_md.lower()


def test_update_urls_returns_false_for_missing_course(db):
    counts = update_urls(db)
    assert counts == {"course_found": False}
