import pytest

from seed.seed_aalto_applied_sde import (
    BASE,
    BOOKLET_URL,
    CHAPTERS,
    CODE,
    DESCRIPTION,
    EXERCISE_ROUNDS,
    HANDOUTS,
    HOME,
    HOME_MD,
    SYLLABUS_MD,
    TEXTBOOK,
    _exercise_url,
    _handout_url,
    _modules,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch):
    """Defensive: the Aalto SDE seed makes no network calls today, but if a
    future change adds httpx usage we want tests to fail loudly rather than
    silently hit the live Aalto site."""
    import httpx

    def _boom(*a, **kw):
        raise AssertionError("seed must not perform network I/O during tests")

    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)
    yield


# ---------------------------------------------------------- constants / URL helpers


def test_code_and_base():
    assert CODE == "Aalto MS-E1602"
    assert BASE == "https://users.aalto.fi/~ssarkka/course_s2014"
    assert HOME == BASE + "/"


def test_booklet_url():
    assert BOOKLET_URL == BASE + "/sde_course_booklet.pdf"


def test_exercise_urls():
    assert _exercise_url(1) == BASE + "/ex1.pdf"
    assert _exercise_url(6) == BASE + "/ex6.pdf"


def test_handout_urls():
    assert _handout_url(1) == BASE + "/handout1.pdf"
    assert _handout_url(6) == BASE + "/handout6.pdf"


def test_exercise_rounds_count_and_uniform_points():
    """6 exercise rounds, all worth 100 points (uniform), all project-mode."""
    assert len(EXERCISE_ROUNDS) == 6
    for _n, _title, _ch, _lec_from, _lec_to, pts in EXERCISE_ROUNDS:
        assert pts == 100


def test_exercise_rounds_cover_chapters_2_through_7():
    """Round k covers booklet Ch k+1 (Ch 1 is ODE refresher, Ch 8 is bonus)."""
    pairs = [(n, ch) for (n, _t, ch, _lf, _lt, _p) in EXERCISE_ROUNDS]
    assert pairs == [
        (1, "Booklet Ch 2"),
        (2, "Booklet Ch 3"),
        (3, "Booklet Ch 4"),
        (4, "Booklet Ch 5"),
        (5, "Booklet Ch 6"),
        (6, "Booklet Ch 7"),
    ]


def test_chapters_count_and_order():
    """Booklet has 8 chapters; all 8 present in order."""
    assert len(CHAPTERS) == 8
    nums = [n for (n, _title) in CHAPTERS]
    assert nums == [1, 2, 3, 4, 5, 6, 7, 8]


def test_handouts_count():
    """6 handout PDFs — 1 per session."""
    assert len(HANDOUTS) == 6


# ---------------------------------------------------------- _modules()


def test_modules_shape():
    """3 modules with the expected item counts."""
    mods = _modules()
    titles = [t for (t, _items) in mods]
    assert titles == ["Direct links", "Booklet chapters", "Lecture handouts"]

    counts = {t: len(items) for (t, items) in mods}
    assert counts == {
        "Direct links": 6,
        "Booklet chapters": 8,
        "Lecture handouts": 6,
    }


def test_modules_only_link_kinds():
    """Every module item is kind='link' (no video, no inline text)."""
    for (_title, items) in _modules():
        for it in items:
            assert it["kind"] == "link", f"non-link kind: {it!r}"


def test_modules_chapter_titles():
    """Booklet chapter items carry the chapter number and topic."""
    by_module = dict(_modules())
    chap_items = by_module["Booklet chapters"]
    assert chap_items[0]["title"].startswith("Chapter 1 —")
    assert chap_items[-1]["title"].startswith("Chapter 8 —")
    # All 8 chapters point at the booklet PDF (no per-chapter PDF exists).
    for it in chap_items:
        assert it["url"] == BOOKLET_URL


def test_modules_handout_urls():
    """Lecture-handout items use _handout_url(N)."""
    by_module = dict(_modules())
    handout_items = by_module["Lecture handouts"]
    assert handout_items[0]["url"] == _handout_url(1)
    assert handout_items[-1]["url"] == _handout_url(6)


# ---------------------------------------------------------- seed()


def test_seed_creates_course_with_expected_metadata(db):
    course = seed(db)
    assert course.code == "Aalto MS-E1602"
    assert course.title == "Applied Stochastic Differential Equations"
    assert course.institution == "Aalto University"
    assert course.instructor == "Profs. Simo Särkkä & Arno Solin"
    assert course.term_label == "Spring 2029"
    assert course.status == "planned"
    assert course.color == "#2D7A47"
    assert course.external_home_url == HOME
    assert course.home_page_md == HOME_MD
    assert course.syllabus_md == SYLLABUS_MD
    assert course.textbook == TEXTBOOK
    assert course.description == DESCRIPTION


def test_seed_creates_one_assignment_group_weight_100(db):
    course = seed(db)
    assert len(course.assignment_groups) == 1
    g = course.assignment_groups[0]
    assert g.name == "Exercise Rounds"
    assert g.weight == 100
    assert g.drop_lowest_n == 0
    assert g.position == 0


def test_seed_creates_six_project_mode_assignments(db):
    course = seed(db)
    assert len(course.assignments) == 6
    by_title = {a.title: a for a in course.assignments}

    for n, _title_stem, _ch, lec_from, lec_to, pts in EXERCISE_ROUNDS:
        match = [t for t in by_title if t.startswith(f"Exercise Round {n} —")]
        assert len(match) == 1, f"expected exactly one Round {n}, got {match}"
        a = by_title[match[0]]
        assert int(a.points_possible) == pts == 100
        # All 6 rounds are project-mode (no reference solution to compare).
        assert a.requires_solution_key is False, (
            f"Round {n} must be project-mode (Aalto publishes no solutions)"
        )
        assert a.covers_lecture_from == lec_from
        assert a.covers_lecture_to == lec_to
        # description_md should reference the source PDF and project-mode.
        assert _exercise_url(n) in a.description_md
        assert "project mode" in a.description_md.lower()


def test_seed_creates_three_modules_with_expected_items(db):
    course = seed(db)
    mods = sorted(course.modules, key=lambda m: m.position)
    assert [m.title for m in mods] == [
        "Direct links",
        "Booklet chapters",
        "Lecture handouts",
    ]
    counts = {m.title: len(m.items) for m in mods}
    assert counts == {
        "Direct links": 6,
        "Booklet chapters": 8,
        "Lecture handouts": 6,
    }


def test_seed_is_idempotent(db):
    first = seed(db)
    second = seed(db)
    assert first.id == second.id
    # No duplicate assignments / modules created.
    assert len(second.assignments) == 6
    assert len(second.modules) == 3


def test_seed_force_recreates_course(db):
    first = seed(db)
    first_id = first.id
    second = seed(db, force=True)
    assert second.id != first_id
    assert len(second.assignments) == 6


# ---------------------------------------------------------- update_urls


def test_update_urls_noop_on_fresh_seed(db):
    seed(db)
    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] == 0
    assert counts["assignments_updated"] == 0
    assert counts["coverage_updated"] == 0
    assert counts["items_examined"] == 6 + 8 + 6  # 20


def test_update_urls_restores_tampered_url(db):
    course = seed(db)
    # Tamper with the booklet link.
    booklet_link = next(
        it
        for m in course.modules
        for it in m.items
        if it.title == "Lecture notes booklet (119 pp PDF)"
    )
    booklet_link.external_url = "https://example.com/wrong.pdf"
    db.commit()

    counts = update_urls(db)
    assert counts["items_updated"] == 1
    db.refresh(booklet_link)
    assert booklet_link.external_url == BOOKLET_URL


def test_update_urls_restores_tampered_description(db):
    course = seed(db)
    a1 = next(a for a in course.assignments if a.title.startswith("Exercise Round 1 "))
    a1.description_md = "tampered description"
    db.commit()

    counts = update_urls(db)
    assert counts["assignments_updated"] == 1
    db.refresh(a1)
    assert _exercise_url(1) in a1.description_md


def test_update_urls_restores_tampered_coverage(db):
    course = seed(db)
    a3 = next(a for a in course.assignments if a.title.startswith("Exercise Round 3 "))
    a3.covers_lecture_from = 99
    a3.covers_lecture_to = 99
    db.commit()

    counts = update_urls(db)
    assert counts["coverage_updated"] == 1
    db.refresh(a3)
    assert a3.covers_lecture_from == 3
    assert a3.covers_lecture_to == 3


def test_update_urls_on_missing_course(db):
    """No course present → returns course_found=False without raising."""
    out = update_urls(db)
    assert out == {"course_found": False}
