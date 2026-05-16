import pytest

from app.models import Course
from seed.seed_6_262 import (
    BASE,
    CODE,
    DESCRIPTION,
    FINAL_SPEC,
    HOME,
    HOME_MD,
    LECTURE_TOPICS,
    LECTURE_VIDEO_SLUGS,
    MIDTERM_SPEC,
    PROBLEM_SETS,
    SYLLABUS_MD,
    TEXTBOOK,
    _exam_sol_url,
    _exam_url,
    _modules,
    _ps_sol_url,
    _ps_url,
    _resolve_pdf_url,
    _video_url,
    seed,
)

_SAMPLE_OCW_HTML = (
    '<html><body>\n'
    '<h1>Problem Set 1 Solutions</h1>\n'
    '<a class="download" href="/courses/6-262-discrete-stochastic-processes-spring-2011/'
    'c12643e48449ee92da0cba905e0ba5ca_MIT6_262S11_assn01_sol.pdf">\n'
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

    import httpx
    monkeypatch.setattr(httpx, "get", _fake_get)

    result = _resolve_pdf_url("mit6_262s11_assn01_sol")
    assert result == (
        "https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/"
        "c12643e48449ee92da0cba905e0ba5ca_MIT6_262S11_assn01_sol.pdf"
    )
    assert captured["url"].endswith("/resources/mit6_262s11_assn01_sol/")


def test_resolve_pdf_url_raises_on_no_pdf(monkeypatch):
    class _Resp:
        text = "<html><body>No PDF here.</body></html>"
        def raise_for_status(self): pass

    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    with pytest.raises(RuntimeError, match="no PDF link"):
        _resolve_pdf_url("mit6_262s11_assn01_sol")


def test_code_and_base():
    assert CODE == "MIT 6.262"
    assert BASE == (
        "https://ocw.mit.edu/courses/"
        "6-262-discrete-stochastic-processes-spring-2011"
    )
    assert HOME == BASE + "/"


def test_ps_urls_zero_pad():
    assert _ps_url(1) == BASE + "/resources/mit6_262s11_assn01/"
    assert _ps_url(12) == BASE + "/resources/mit6_262s11_assn12/"
    assert _ps_sol_url(1) == BASE + "/resources/mit6_262s11_assn01_sol/"
    assert _ps_sol_url(12) == BASE + "/resources/mit6_262s11_assn12_sol/"


def test_exam_urls():
    assert _exam_url("mid", 2011) == BASE + "/resources/mit6_262s11_mid11/"
    assert _exam_url("mid", 2010) == BASE + "/resources/mit6_262s11_mid10/"
    assert _exam_url("mid", 2009) == BASE + "/resources/mit6_262s11_mid09/"
    assert _exam_url("final", 2011) == BASE + "/resources/mit6_262s11_final11/"
    assert _exam_url("final", 2009) == BASE + "/resources/mit6_262s11_final09/"
    assert _exam_sol_url("mid", 2011) == BASE + "/resources/mit6_262s11_mid11_sol/"
    assert _exam_sol_url("final", 2011) == BASE + "/resources/mit6_262s11_final11_sol/"


def test_lecture_topics_cover_1_to_25():
    assert set(LECTURE_TOPICS.keys()) == set(range(1, 26))
    for _n, (topic, ref) in LECTURE_TOPICS.items():
        assert topic
        assert ref.startswith("Gallager Ch")


def test_lecture_video_slugs_cover_1_to_25():
    # All 25 lectures are recorded for 6.262 (no gaps like 18.065's lab days).
    assert set(LECTURE_VIDEO_SLUGS.keys()) == set(range(1, 26))


def test_video_url_resolves():
    url = _video_url(1)
    assert url.startswith(
        "https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/resources/"
    )
    assert url.endswith("/")


def test_problem_sets_shape():
    assert len(PROBLEM_SETS) == 12
    nums = [k for (k, _t, _f, _to) in PROBLEM_SETS]
    assert nums == list(range(1, 13))
    # coverage must monotonically advance and end at lecture 25
    last_to = 0
    for k, _topic, lec_from, lec_to in PROBLEM_SETS:
        assert lec_from > last_to, f"PS{k} from must follow previous to"
        assert lec_to >= lec_from
        last_to = lec_to
    assert last_to == 25


def test_exam_specs():
    # Each spec is (paper_year, covers_from, covers_to, practice_years).
    py, cf, ct, practice = MIDTERM_SPEC
    assert py == 2011
    assert (cf, ct) == (1, 14)
    assert set(practice) == {2009, 2010}
    py, cf, ct, practice = FINAL_SPEC
    assert py == 2011
    assert (cf, ct) == (15, 25)
    assert set(practice) == {2009}


def test_modules_shape():
    mods = _modules()
    assert [m[0] for m in mods] == [
        "Direct links",
        "Unit 1 — Probability review & Bernoulli",
        "Unit 2 — Poisson processes",
        "Unit 3 — Finite-state Markov chains",
        "Unit 4 — Renewal processes",
        "Unit 5 — Countable-state Markov chains & processes",
        "Unit 6 — Random walks & martingales",
        "Gallager course notes",
        "Practice exams",
    ]


def test_modules_per_lecture_note_pattern():
    mods = _modules()
    # Each Unit module has 2*N + 1 items per its lecture count:
    # for each lecture, a 'note' item + a 'link' "Watch video →" child item;
    # closed by a unit-level 'note' "Readings".
    expected_lecture_counts = {
        "Unit 1 — Probability review & Bernoulli":              3,   # lec 1-3
        "Unit 2 — Poisson processes":                           2,   # lec 4-5
        "Unit 3 — Finite-state Markov chains":                  4,   # lec 6-9
        "Unit 4 — Renewal processes":                           6,   # lec 10-15
        "Unit 5 — Countable-state Markov chains & processes":   5,   # lec 16-20
        "Unit 6 — Random walks & martingales":                  5,   # lec 21-25
    }
    by_title = dict(mods)
    for title, count in expected_lecture_counts.items():
        items = by_title[title]
        assert len(items) == 2 * count + 1, f"unit {title!r}: got {len(items)} items"
        # First item per lecture must be a note; the [Watch video →] link follows.
        for i in range(count):
            assert items[2 * i]["kind"] == "note"
            assert items[2 * i + 1]["kind"] == "link"
            assert items[2 * i + 1]["title"] == "Watch video →"
        # Trailing readings note.
        assert items[-1]["kind"] == "note"
        assert items[-1]["title"] == "Readings"


def test_modules_practice_exams_links():
    mods = dict(_modules())
    items = mods["Practice exams"]
    # 5 papers + 5 solutions = 10 link items.
    assert len(items) == 10
    titles = [i["title"] for i in items]
    assert "Midterm 2011 — paper" in titles
    assert "Midterm 2010 — paper" in titles
    assert "Midterm 2009 — paper" in titles
    assert "Final 2011 — paper" in titles
    assert "Final 2009 — paper" in titles
    assert "Midterm 2011 — solution" in titles
    assert "Final 2009 — solution" in titles
    for it in items:
        assert it["kind"] == "link"
        assert "ocw.mit.edu" in it["url"]


def test_modules_gallager_notes_links_chapter_pdfs():
    mods = dict(_modules())
    items = mods["Gallager course notes"]
    # Front matter + 7 chapters + back matter = 9 link items.
    assert len(items) == 9
    titles = [i["title"] for i in items]
    assert "Front matter" in titles
    assert "Chapter 1" in titles
    assert "Chapter 7" in titles
    assert "Back matter" in titles
    for it in items:
        assert it["kind"] == "link"
        assert "mit6_262s11_" in it["url"]


def test_syllabus_contains_grading_split():
    assert "20%" in SYLLABUS_MD
    assert "35%" in SYLLABUS_MD
    assert "45%" in SYLLABUS_MD
    assert "Quiz" in SYLLABUS_MD or "Midterm" in SYLLABUS_MD
    # USP of this seed: OCW publishes Gallager's official solutions, so the
    # AI grader compares against the real reference rather than a regenerated key.
    assert "official solutions" in SYLLABUS_MD.lower()


def test_home_md_mentions_gallager_and_term_label_is_user_set():
    assert "Gallager" in HOME_MD
    # The HOME_MD must remind the user that term_label is *their* self-study
    # term, not the OCW recording year — see term_label memory.
    assert "self-study" in HOME_MD


def test_description_and_textbook_nonempty():
    assert "Markov" in DESCRIPTION
    assert "Gallager" in TEXTBOOK
    assert "Stochastic Processes" in TEXTBOOK


def test_seed_creates_6_262_basic_shape(db):
    c = seed(db)
    assert c.code == "MIT 6.262"
    assert c.title == "Discrete Stochastic Processes"
    assert c.instructor == "Prof. Robert Gallager"
    assert c.institution == "Massachusetts Institute of Technology"
    assert c.term_label == "Summer 2028"
    assert c.color == "#4A2C82"
    assert c.display_order == 4
    assert c.status == "planned"
    assert c.external_home_url.startswith(
        "https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011"
    )


def test_seed_groups_and_weights(db):
    c = seed(db)
    weights = {g.name: (float(g.weight), g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Problem Sets"] == (20.0, 0)
    assert weights["Midterm Quiz"] == (35.0, 0)
    assert weights["Final Exam"] == (45.0, 0)
    assert sum(w for w, _ in weights.values()) == 100.0


def test_seed_assignment_counts(db):
    c = seed(db)
    n_modules = len(c.modules)
    n_items = sum(len(m.items) for m in c.modules)
    n_assign = len(c.assignments)
    # 9 modules. 14 assignments = 12 PSets + 1 midterm + 1 final.
    assert n_modules == 9
    assert n_assign == 14
    assert n_items > 50  # 9 + (2*lec + 1) per unit + 9 + 10 — sanity floor


def test_seed_problem_set_coverage(db):
    c = seed(db)
    psets = sorted(
        (a for a in c.assignments if a.title.startswith("Problem Set")),
        key=lambda a: a.position,
    )
    assert len(psets) == 12
    assert all(p.requires_solution_key for p in psets)
    assert psets[0].covers_lecture_from == 1
    assert psets[0].covers_lecture_to == 3
    assert psets[-1].covers_lecture_from == 24
    assert psets[-1].covers_lecture_to == 25


def test_seed_midterm_and_final(db):
    c = seed(db)
    mid = next(a for a in c.assignments if a.title.startswith("Midterm Exam"))
    fin = next(a for a in c.assignments if a.title.startswith("Final Exam"))
    assert mid.covers_lecture_from == 1
    assert mid.covers_lecture_to == 14
    assert fin.covers_lecture_from == 15
    assert fin.covers_lecture_to == 25
    # Description references the 2011 paper and lists practice years.
    assert "2010" in mid.description_md and "2009" in mid.description_md
    assert "2009" in fin.description_md


def test_seed_is_idempotent(db):
    c1 = seed(db)
    n1 = (len(c1.modules), len(c1.assignments))
    c2 = seed(db)
    assert c2.id == c1.id
    assert (len(c2.modules), len(c2.assignments)) == n1
    assert db.query(Course).filter(Course.code == "MIT 6.262").count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == "MIT 6.262").count() == 1
    assert len(c.assignments) == 14
