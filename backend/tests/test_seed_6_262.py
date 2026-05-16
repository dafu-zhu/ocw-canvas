from seed.seed_6_262 import (
    BASE,
    CODE,
    FINAL_SPEC,
    HOME,
    LECTURE_TOPICS,
    LECTURE_VIDEO_SLUGS,
    MIDTERM_SPEC,
    PROBLEM_SETS,
    _exam_sol_url,
    _exam_url,
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
