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
    _video_url,
)


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
