import pytest

from seed.seed_aalto_bda import (
    BASE,
    BDA3_PDF_URL,
    CHAPTER_NOTES,
    CODE,
    DESCRIPTION,
    GITHUB_BASE,
    HOME,
    HOME_MD,
    PROJECT_LEC_FROM,
    PROJECT_LEC_TO,
    PROJECT_POINTS,
    PROJECT_TITLE,
    SLIDE_DECKS,
    SYLLABUS_MD,
    TEXTBOOK,
    WEEKLY_ASSIGNMENTS,
    _assignment_url,
    _chapter_note_url,
    _modules,
    _slide_url,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch):
    """Defensive: the Aalto seed makes no network calls today, but if a
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
    assert CODE == "Aalto BDA"
    assert BASE == "https://avehtari.github.io/BDA_course_Aalto"
    assert HOME == BASE + "/"
    assert GITHUB_BASE == "https://github.com/avehtari/BDA_course_Aalto"


def test_assignment_urls():
    assert _assignment_url(1) == BASE + "/assignments/assignment1.html"
    assert _assignment_url(9) == BASE + "/assignments/assignment9.html"


def test_chapter_note_urls():
    assert _chapter_note_url(1) == BASE + "/chapter_notes/BDA_notes_ch1.pdf"
    assert _chapter_note_url(12) == BASE + "/chapter_notes/BDA_notes_ch12.pdf"


def test_slide_url_uses_github_raw():
    assert _slide_url("1a") == GITHUB_BASE + "/raw/master/slides/BDA_lecture_1a.pdf"
    assert _slide_url("11c") == GITHUB_BASE + "/raw/master/slides/BDA_lecture_11c.pdf"


def test_weekly_assignments_count_and_weights():
    """9 weeklies; points_possible scaled x10 from GSU 2023 weights."""
    assert len(WEEKLY_ASSIGNMENTS) == 9
    weights = [pts for (_n, _title, _ch, _lec_from, _lec_to, pts) in WEEKLY_ASSIGNMENTS]
    assert weights == [60, 60, 190, 120, 120, 120, 120, 120, 60]


def test_chapter_notes_skip_chapter_8():
    """BDA3 ch 8 is intentionally omitted by the course."""
    chapters = [n for (n, _title) in CHAPTER_NOTES]
    assert chapters == [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12]


def test_slide_decks_ordered_by_lecture():
    """Slides ordered by (lecture-number, sub-deck)."""
    slugs = [slug for (slug, _title) in SLIDE_DECKS]
    assert slugs == [
        "1a", "1b",
        "2", "3", "4", "5", "6", "7",
        "8a", "8b",
        "9",
        "10a", "10b", "10c",
        "11a", "11b", "11c",
    ]


# --------------------------------------------------------------------------- _modules() shape


def test_modules_shape():
    """3 modules with the expected item counts; no per-lecture units, no
    inline video items (per feedback-module-content-chapter-readings)."""
    mods = _modules()
    titles = [t for (t, _items) in mods]
    assert titles == ["Direct links", "BDA3 Chapter notes", "Lecture slides"]

    counts = {t: len(items) for (t, items) in mods}
    assert counts == {
        "Direct links": 13,
        "BDA3 Chapter notes": 11,
        "Lecture slides": 17,
    }


def test_modules_only_link_kind_items():
    """No items have kind='video'. The single Panopto-folder link in Direct
    links is kind='link', not kind='video'."""
    for (_title, items) in _modules():
        for it in items:
            assert it["kind"] == "link", f"non-link kind: {it!r}"


def test_modules_chapter_note_titles_carry_chapter_number():
    chap_items = dict(_modules())["BDA3 Chapter notes"]
    assert chap_items[0]["title"].startswith("Chapter 1 ")
    assert chap_items[-1]["title"].startswith("Chapter 12 ")
    titles = [it["title"] for it in chap_items]
    assert any("Chapter 7 " in t for t in titles)
    assert any("Chapter 9 " in t for t in titles)
    assert not any(t.startswith("Chapter 8 ") for t in titles)


# --------------------------------------------------------------------------- seed()


def test_seed_creates_course_with_expected_metadata(db):
    course = seed(db)
    assert course.code == "Aalto BDA"
    assert course.title == "Bayesian Data Analysis"
    assert course.institution == "Aalto University"
    assert course.instructor == "Prof. Aki Vehtari"
    assert course.term_label == "Spring 2030"
    assert course.status == "planned"
    assert course.color == "#0066B3"
    assert course.display_order == 5
    assert course.external_home_url == HOME
    assert course.home_page_md == HOME_MD
    assert course.syllabus_md == SYLLABUS_MD
    assert course.textbook == TEXTBOOK
    assert course.description == DESCRIPTION


def test_seed_creates_two_assignment_groups_with_70_30_weights(db):
    course = seed(db)
    by_name = {g.name: g for g in course.assignment_groups}
    assert set(by_name) == {"Weekly Assignments", "Capstone Project"}
    assert int(by_name["Weekly Assignments"].weight) == 70
    assert int(by_name["Capstone Project"].weight) == 30
    assert by_name["Weekly Assignments"].position == 0
    assert by_name["Capstone Project"].position == 1


def test_seed_creates_9_weeklies_plus_1_project(db):
    course = seed(db)
    assert len(course.assignments) == 10
    by_title = {a.title: a for a in course.assignments}

    for n, title_stem, _ch, lec_from, lec_to, pts in WEEKLY_ASSIGNMENTS:
        match = [t for t in by_title if t.startswith(f"Assignment {n} ")]
        assert len(match) == 1, f"expected exactly one Assignment {n}, got {match}"
        a = by_title[match[0]]
        assert title_stem in a.title
        assert int(a.points_possible) == pts
        assert a.requires_solution_key is True
        assert a.covers_lecture_from == lec_from
        assert a.covers_lecture_to == lec_to

    proj = [a for a in course.assignments if a.title == PROJECT_TITLE]
    assert len(proj) == 1
    p = proj[0]
    assert p.requires_solution_key is False
    assert int(p.points_possible) == PROJECT_POINTS
    assert p.covers_lecture_from == PROJECT_LEC_FROM
    assert p.covers_lecture_to == PROJECT_LEC_TO


def test_seed_creates_three_modules_with_expected_items(db):
    course = seed(db)
    mods = sorted(course.modules, key=lambda m: m.position)
    assert [m.title for m in mods] == [
        "Direct links",
        "BDA3 Chapter notes",
        "Lecture slides",
    ]
    counts = {m.title: len(m.items) for m in mods}
    assert counts == {
        "Direct links": 13,
        "BDA3 Chapter notes": 11,
        "Lecture slides": 17,
    }


def test_seed_is_idempotent(db):
    first = seed(db)
    second = seed(db)
    assert first.id == second.id
    assert len(second.assignments) == 10
    assert len(second.modules) == 3


def test_seed_force_recreates_course(db):
    first = seed(db)
    first_id = first.id
    second = seed(db, force=True)
    assert second.id != first_id
    assert len(second.assignments) == 10


# --------------------------------------------------------------------------- update_urls()


def test_update_urls_noop_on_fresh_seed(db):
    seed(db)
    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] == 0
    assert counts["assignments_updated"] == 0
    assert counts["coverage_updated"] == 0
    assert counts["items_examined"] == 13 + 11 + 17


def test_update_urls_restores_tampered_url(db):
    course = seed(db)
    bda3_link = next(
        it for m in course.modules for it in m.items
        if it.title == "BDA3 — free PDF (textbook)"
    )
    bda3_link.external_url = "https://example.com/wrong.pdf"
    db.commit()

    counts = update_urls(db)
    assert counts["items_updated"] == 1
    db.refresh(bda3_link)
    assert bda3_link.external_url == BDA3_PDF_URL


def test_update_urls_restores_tampered_coverage(db):
    course = seed(db)
    a3 = next(a for a in course.assignments if a.title.startswith("Assignment 3 "))
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
