import httpx
import pytest

import seed.seed_mit_6_231 as seed_mod
from app.models import Assignment, Course
from app.services import storage as storage_mod
from seed.seed_mit_6_231 import (
    BASE,
    CODE,
    DESCRIPTION,
    HOME,
    HOME_MD,
    LECTURE_TOPICS,
    MIDTERM_COVERS_FROM,
    MIDTERM_COVERS_TO,
    MIDTERM_GRADED_YEAR,
    PROBLEM_SETS,
    PROJECT_COVERS_FROM,
    PROJECT_COVERS_TO,
    SYLLABUS_MD,
    TEXTBOOK,
    _hw8_url,
    _lec_url,
    _midterm_sol_url,
    _midterm_url,
    _modules,
    _project_topics_url,
    _ps_sol_url,
    _resolve_pdf_url,
    refresh_solutions,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch, tmp_path):
    """Default mocks so any test that calls seed(db) doesn't hit the network.

    Tests that need specific network/storage behaviour set their own
    monkeypatches; pytest stacks them on top of these defaults.
    """
    def _fake_resolve(slug):
        return f"https://ocw.mit.edu/fake/{slug}.pdf"

    class _FakePdfResp:
        content = b"%PDF-fake"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _fake_resolve)
    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _FakePdfResp())
    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)
    yield


# ---------------------------------------------------------- constants / URL helpers


def test_code_and_base():
    assert CODE == "MIT 6.231"
    assert BASE == (
        "https://ocw.mit.edu/courses/"
        "6-231-dynamic-programming-and-stochastic-control-fall-2015"
    )
    assert HOME == BASE + "/"


def test_lec_url_not_zero_padded():
    assert _lec_url(1) == BASE + "/resources/mit6_231f15_lec1/"
    assert _lec_url(23) == BASE + "/resources/mit6_231f15_lec23/"


def test_ps_sol_url():
    assert _ps_sol_url(1) == BASE + "/resources/mit6_231f15_solution1/"
    assert _ps_sol_url(8) == BASE + "/resources/mit6_231f15_solution8/"


def test_hw8_url():
    assert _hw8_url() == BASE + "/resources/mit6_231f15_homework8/"


def test_midterm_urls():
    assert _midterm_url(2015) == BASE + "/resources/mit6_231f15_mid_2015/"
    assert _midterm_url(2008) == BASE + "/resources/mit6_231f15_mid_2008/"
    assert _midterm_sol_url(2011) == BASE + "/resources/mit6_231f15_mid_2011_sol/"
    assert _midterm_sol_url(2015) == BASE + "/resources/mit6_231f15_mid_2015_sol/"


def test_project_topics_url():
    assert _project_topics_url() == BASE + "/resources/mit6_231f15_references/"


# ---------------------------------------------------------- _resolve_pdf_url


_SAMPLE_OCW_HTML = (
    '<html><body>\n'
    '<h1>Problem Set 1 Solutions</h1>\n'
    '<a class="download" href="/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/'
    'def456abc1234567890ef0123456789ab_MIT6_231F15_solution1.pdf">\n'
    '  Download File\n'
    '</a>\n'
    '</body></html>\n'
)


def test_resolve_pdf_url_finds_hash_prefixed_pdf(monkeypatch):
    captured: dict = {}

    class _Resp:
        text = _SAMPLE_OCW_HTML
        def raise_for_status(self): pass

    def _fake_get(url, **kw):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = _resolve_pdf_url("mit6_231f15_solution1")
    assert result == (
        "https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/"
        "def456abc1234567890ef0123456789ab_MIT6_231F15_solution1.pdf"
    )
    assert captured["url"].endswith("/resources/mit6_231f15_solution1/")


_MULTI_PDF_HTML = (
    '<html><body>'
    '<a href="/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/'
    'aaaa_MIT6_231F15_other_pdf.pdf">Other PDF</a>'
    '<a href="/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/'
    'bbbb_MIT6_231F15_solution1.pdf">Solution PDF</a>'
    '</body></html>'
)


def test_resolve_pdf_url_picks_slug_matching_pdf(monkeypatch):
    class _Resp:
        text = _MULTI_PDF_HTML
        def raise_for_status(self): pass

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    result = _resolve_pdf_url("mit6_231f15_solution1")
    assert "MIT6_231F15_solution1.pdf" in result
    assert "other_pdf" not in result


def test_resolve_pdf_url_raises_on_no_pdf(monkeypatch):
    class _Resp:
        text = "<html><body>No PDF here.</body></html>"
        def raise_for_status(self): pass

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    with pytest.raises(RuntimeError, match="no PDF link matching slug"):
        _resolve_pdf_url("mit6_231f15_solution1")


# ---------------------------------------------------------- data tables


def test_lecture_topics_cover_1_to_23():
    assert set(LECTURE_TOPICS.keys()) == set(range(1, 24))
    for _n, (topic, ref) in LECTURE_TOPICS.items():
        assert topic
        assert ref.startswith("Vol I") or ref.startswith("Vol II")


def test_problem_sets_shape():
    assert len(PROBLEM_SETS) == 9
    nums = [k for (k, *_) in PROBLEM_SETS]
    assert nums == list(range(1, 10))


def test_problem_set_solutions_pset9_has_none():
    by_n = {k: (sol_slug, hw_slug) for (k, _t, _pmd, _f, _to, hw_slug, sol_slug) in PROBLEM_SETS}
    # PSet 9 (Vol II 4.12, 4.17) has no published OCW solution.
    assert by_n[9] == (None, None)
    # PSet 8 has both a custom homework PDF and a solution.
    assert by_n[8] == ("mit6_231f15_solution8", "mit6_231f15_homework8")
    # PSets 1-7 have solutions but no custom homework.
    for k in range(1, 8):
        sol_slug, hw_slug = by_n[k]
        assert sol_slug == f"mit6_231f15_solution{k}"
        assert hw_slug is None


def test_problem_set_coverage_ranges_sensible():
    for k, _topic, _pmd, lec_from, lec_to in [
        (row[0], row[1], row[2], row[3], row[4]) for row in PROBLEM_SETS
    ]:
        assert 1 <= lec_from <= lec_to <= 23, (
            f"PS{k} covers ({lec_from}, {lec_to}) — outside 1..23"
        )


def test_midterm_constants():
    assert MIDTERM_GRADED_YEAR == 2015
    assert MIDTERM_COVERS_FROM == 1
    assert MIDTERM_COVERS_TO == 9


def test_project_constants():
    assert PROJECT_COVERS_FROM == 1
    assert PROJECT_COVERS_TO == 23


# ---------------------------------------------------------- _modules() shape


def test_modules_shape():
    mods = _modules()
    assert [m[0] for m in mods] == [
        "Direct links",
        "Lecture Slides",
        "Project Resources",
        "Practice Midterms",
    ]


def test_modules_direct_links_count():
    mods = dict(_modules())
    items = mods["Direct links"]
    assert len(items) == 7  # home + syllabus + 4 page links + related-video-lectures
    for it in items:
        assert it["kind"] == "link"
        assert it["url"].startswith(BASE)


def test_modules_lecture_slides_count():
    mods = dict(_modules())
    items = mods["Lecture Slides"]
    assert len(items) == 23
    titles = [it["title"] for it in items]
    assert titles[0].startswith("Lecture 1: ")
    assert titles[-1].startswith("Lecture 23: ")
    for it in items:
        assert it["kind"] == "link"
        assert "/resources/mit6_231f15_lec" in it["url"]


def test_modules_project_resources_count():
    mods = dict(_modules())
    items = mods["Project Resources"]
    assert len(items) == 1
    assert items[0]["url"] == _project_topics_url()


def test_modules_practice_midterms_links():
    mods = dict(_modules())
    items = mods["Practice Midterms"]
    # 3 practice years × 2 (paper + indented solution) = 6 items.
    assert len(items) == 6
    titles = [it["title"] for it in items]
    assert "Midterm 2008 — paper" in titles
    assert "Midterm 2009 — paper" in titles
    assert "Midterm 2011 — paper" in titles
    assert "Midterm 2008 — solution" in titles
    # The graded 2015 paper MUST NOT appear in Modules (it's the Assignment).
    assert "Midterm 2015 — paper" not in titles
    assert "Midterm 2015 — solution" not in titles
    # Solutions are indented under their paper.
    for it in items:
        if it["title"].endswith("— solution"):
            assert it.get("indent", 0) == 1


def test_modules_only_link_kind_items():
    """Per feedback-module-content-chapter-readings Rule 1: no video items."""
    for _title, items in _modules():
        for it in items:
            assert it["kind"] == "link", f"non-link kind: {it!r}"


# ---------------------------------------------------------- copy / metadata


def test_syllabus_contains_grading_split():
    assert "30%" in SYLLABUS_MD
    assert "40%" in SYLLABUS_MD
    assert "Project" in SYLLABUS_MD
    assert "Midterm" in SYLLABUS_MD


def test_home_md_mentions_bertsekas_and_self_study():
    assert "Bertsekas" in HOME_MD
    # term_label is *user's* self-study term.
    assert "self-study" in HOME_MD


def test_description_and_textbook_nonempty():
    assert "dynamic programming" in DESCRIPTION.lower()
    assert "Bertsekas" in TEXTBOOK
    assert "Vol I" in TEXTBOOK
    assert "Vol II" in TEXTBOOK


# ---------------------------------------------------------- seed()


def test_seed_creates_course_with_expected_metadata(db):
    c = seed(db)
    assert c.code == "MIT 6.231"
    assert c.title == "Dynamic Programming and Stochastic Control"
    assert c.instructor == "Prof. Dimitri P. Bertsekas"
    assert c.institution == "Massachusetts Institute of Technology"
    assert c.term_label == "Fall 2030"
    assert c.color == "#1F7A4D"
    assert c.display_order == 6
    assert c.status == "planned"
    assert c.external_home_url == HOME
    assert c.home_page_md == HOME_MD
    assert c.syllabus_md == SYLLABUS_MD
    assert c.textbook == TEXTBOOK
    assert c.description == DESCRIPTION


def test_seed_groups_and_weights(db):
    c = seed(db)
    weights = {g.name: (float(g.weight), g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Problem Sets"] == (30.0, 0)
    assert weights["Midterm"] == (30.0, 0)
    assert weights["Course Project"] == (40.0, 0)
    assert sum(w for w, _ in weights.values()) == 100.0


def test_seed_assignment_counts(db):
    c = seed(db)
    n_modules = len(c.modules)
    n_items = sum(len(m.items) for m in c.modules)
    n_assign = len(c.assignments)
    # 4 modules: Direct links (7) + Lecture Slides (23) + Project Resources (1) +
    # Practice Midterms (6) = 37 module items.
    assert n_modules == 4
    assert n_items == 37
    # 11 assignments: 9 PSets + 1 midterm + 1 project.
    assert n_assign == 11


def test_seed_problem_set_coverage(db):
    c = seed(db)
    psets = sorted(
        (a for a in c.assignments if a.title.startswith("Problem Set")),
        key=lambda a: a.position,
    )
    assert len(psets) == 9
    assert all(p.requires_solution_key for p in psets)
    # PS1 covers Lec 1-2; PS9 covers Lec 19-22.
    assert psets[0].covers_lecture_from == 1
    assert psets[0].covers_lecture_to == 2
    assert psets[-1].covers_lecture_from == 19
    assert psets[-1].covers_lecture_to == 22


def test_seed_pset9_has_no_official_solution(db):
    c = seed(db)
    ps9 = next(a for a in c.assignments if a.title.startswith("Problem Set 9"))
    assert ps9.requires_solution_key is True
    # PSet 9 has no published solution → both URL and file_path empty.
    assert ps9.official_solution_url == ""
    assert ps9.official_solution_file_path == ""


def test_seed_pset8_homework_link_in_description(db):
    c = seed(db)
    ps8 = next(a for a in c.assignments if a.title.startswith("Problem Set 8"))
    assert "mit6_231f15_homework8" in ps8.description_md


def test_seed_midterm(db):
    c = seed(db)
    mid = next(a for a in c.assignments if a.title.startswith("Midterm Exam"))
    assert mid.covers_lecture_from == 1
    assert mid.covers_lecture_to == 9
    assert mid.requires_solution_key is True
    assert "2015" in mid.title
    # Description references the 2015 paper and lists practice years.
    assert "2015" in mid.description_md
    assert "2008" in mid.description_md
    assert "2009" in mid.description_md
    assert "2011" in mid.description_md


def test_seed_project_is_project_mode(db):
    c = seed(db)
    proj = next(a for a in c.assignments if a.title.startswith("Course Project"))
    assert proj.requires_solution_key is False
    assert proj.covers_lecture_from == 1
    assert proj.covers_lecture_to == 23
    assert proj.official_solution_url == ""
    assert proj.official_solution_file_path == ""
    assert "theoretical" in proj.description_md.lower()
    assert "applied" in proj.description_md.lower()


def test_seed_is_idempotent(db):
    c1 = seed(db)
    n1 = (len(c1.modules), len(c1.assignments))
    c2 = seed(db)
    assert c2.id == c1.id
    assert (len(c2.modules), len(c2.assignments)) == n1
    assert db.query(Course).filter(Course.code == "MIT 6.231").count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == "MIT 6.231").count() == 1
    assert len(c.assignments) == 11


# ---------------------------------------------------------- _attach_official_solution


def _make_assignment(db) -> Assignment:
    c = Course(code="TMP_6231", title="t", institution="i", term_label="x")
    db.add(c)
    db.flush()
    a = Assignment(
        course_id=c.id,
        title="x",
        description_md="",
        points_possible=100,
        position=0,
        published=True,
        requires_solution_key=True,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_attach_official_solution_happy_path(db, monkeypatch, tmp_path):
    a = _make_assignment(db)

    captured = {}

    def _fake_resolve(slug):
        captured["resolved_slug"] = slug
        return f"https://ocw.mit.edu/fake/{slug}.pdf"

    class _Resp:
        content = b"%PDF-1.4\nfakebytes"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _fake_resolve)
    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _Resp())

    seed_mod._attach_official_solution(db, a, "mit6_231f15_solution1")
    db.commit()
    db.refresh(a)

    assert a.official_solution_file_path == "official/6_231/mit6_231f15_solution1.pdf"
    assert a.official_solution_url == ""
    assert captured["resolved_slug"] == "mit6_231f15_solution1"


def test_attach_official_solution_falls_back_to_url_on_failure(db, monkeypatch):
    a = _make_assignment(db)

    def _boom_resolve(slug):
        raise RuntimeError("OCW restructured the page")

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _boom_resolve)

    seed_mod._attach_official_solution(db, a, "mit6_231f15_solution1")
    db.commit()
    db.refresh(a)

    assert a.official_solution_file_path == ""
    assert a.official_solution_url == (
        BASE + "/resources/mit6_231f15_solution1/"
    )


def test_storage_key_namespace():
    assert seed_mod._storage_key_for("mit6_231f15_solution1") == (
        "official/6_231/mit6_231f15_solution1.pdf"
    )


def test_seed_uploads_solutions_for_psets_1_through_8_and_midterm(db):
    c = seed(db)
    # PSets 1-8: official_solution_file_path set under official/6_231/.
    psets = sorted(
        (a for a in c.assignments if a.title.startswith("Problem Set")),
        key=lambda a: a.position,
    )
    for k, p in enumerate(psets, start=1):
        if k == 9:
            assert p.official_solution_file_path == ""
        else:
            assert p.official_solution_file_path == (
                f"official/6_231/mit6_231f15_solution{k}.pdf"
            )
    mid = next(a for a in c.assignments if a.title.startswith("Midterm Exam"))
    assert mid.official_solution_file_path == (
        "official/6_231/mit6_231f15_mid_2015_sol.pdf"
    )


# ---------------------------------------------------------- update_urls()


def test_update_urls_noop_on_fresh_seed(db):
    seed(db)
    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] == 0
    assert counts["assignments_updated"] == 0
    assert counts["coverage_updated"] == 0
    assert counts["items_examined"] == 7 + 23 + 1 + 6


def test_update_urls_restores_tampered_lecture_url(db):
    course = seed(db)
    lec1 = next(
        it for m in course.modules for it in m.items
        if it.title.startswith("Lecture 1: ")
    )
    lec1.external_url = "https://example.com/wrong.pdf"
    db.commit()

    counts = update_urls(db)
    assert counts["items_updated"] == 1
    db.refresh(lec1)
    assert lec1.external_url == _lec_url(1)


def test_update_urls_restores_tampered_pset_coverage(db):
    course = seed(db)
    ps3 = next(a for a in course.assignments if a.title.startswith("Problem Set 3 "))
    ps3.covers_lecture_from = 99
    ps3.covers_lecture_to = 99
    db.commit()

    counts = update_urls(db)
    assert counts["coverage_updated"] == 1
    db.refresh(ps3)
    assert ps3.covers_lecture_from == 5
    assert ps3.covers_lecture_to == 6


def test_update_urls_on_missing_course(db):
    out = update_urls(db)
    assert out == {"course_found": False}


# ---------------------------------------------------------- refresh_solutions()


def test_refresh_solutions_clears_paths_and_re_uploads(db):
    seed(db)
    counts = refresh_solutions(db)
    # 8 PSets with solutions + 1 midterm = 9.
    assert counts == {"course_found": True, "refreshed": 9}


def test_refresh_solutions_on_missing_course(db):
    out = refresh_solutions(db)
    assert out == {"course_found": False, "refreshed": 0}
