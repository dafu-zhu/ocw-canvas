import httpx
import pytest

import seed.seed_6_262 as seed_mod
from app.models import Assignment, Course
from app.services import storage as storage_mod
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


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch, tmp_path):
    """Default mocks so any test that calls seed(db) doesn't hit the network.

    Tests that need specific network/storage behaviour (see the four
    _attach_official_solution tests + test_seed_uploads_official_solutions)
    set their own monkeypatches; pytest stacks them on top of these defaults.
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

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = _resolve_pdf_url("mit6_262s11_assn01_sol")
    assert result == (
        "https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/"
        "c12643e48449ee92da0cba905e0ba5ca_MIT6_262S11_assn01_sol.pdf"
    )
    assert captured["url"].endswith("/resources/mit6_262s11_assn01_sol/")


_MULTI_PDF_HTML = (
    '<html><body>'
    '<a href="/courses/6-262-discrete-stochastic-processes-spring-2011/'
    'aaaa_MIT6_262S11_other_pdf.pdf">Other PDF</a>'
    '<a href="/courses/6-262-discrete-stochastic-processes-spring-2011/'
    'bbbb_MIT6_262S11_assn01_sol.pdf">Solution PDF</a>'
    '</body></html>'
)


def test_resolve_pdf_url_picks_slug_matching_pdf(monkeypatch):
    class _Resp:
        text = _MULTI_PDF_HTML
        def raise_for_status(self): pass

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    result = _resolve_pdf_url("mit6_262s11_assn01_sol")
    assert "MIT6_262S11_assn01_sol.pdf" in result
    assert "other_pdf" not in result


def test_resolve_pdf_url_raises_on_no_pdf(monkeypatch):
    class _Resp:
        text = "<html><body>No PDF here.</body></html>"
        def raise_for_status(self): pass

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    with pytest.raises(RuntimeError, match="no PDF link matching slug"):
        _resolve_pdf_url("mit6_262s11_assn01_sol")


def test_resolve_pdf_url_propagates_http_errors(monkeypatch):
    class _Resp:
        text = ""
        def raise_for_status(self):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("404 Not Found", request=request, response=response)

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp())

    with pytest.raises(httpx.HTTPStatusError):
        _resolve_pdf_url("mit6_262s11_missing")


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
    # Three modules mirror OCW's natural structure — no per-lecture units, no
    # inline video links. See feedback memory feedback-module-content-chapter-readings.
    assert [m[0] for m in mods] == ["Direct links", "Course Notes", "Practice exams"]


def test_modules_practice_exams_links():
    mods = dict(_modules())
    items = mods["Practice exams"]
    # Only practice years — graded 2011 papers live in the Assignments tree,
    # not here. 2 midterm years + 1 final year = 3 papers + 3 solutions = 6 items.
    assert len(items) == 6
    titles = [i["title"] for i in items]
    assert "Midterm 2010 — paper" in titles
    assert "Midterm 2009 — paper" in titles
    assert "Final 2009 — paper" in titles
    assert "Midterm 2010 — solution" in titles
    assert "Midterm 2009 — solution" in titles
    assert "Final 2009 — solution" in titles
    # 2011 papers MUST NOT appear anywhere in Modules — they're graded
    # Assignments, not browseable.
    assert "Midterm 2011 — paper" not in titles
    assert "Midterm 2011 — solution" not in titles
    assert "Final 2011 — paper" not in titles
    assert "Final 2011 — solution" not in titles
    for it in items:
        assert it["kind"] == "link"
        assert "ocw.mit.edu" in it["url"]


def test_modules_course_notes_links_chapter_pdfs():
    mods = dict(_modules())
    items = mods["Course Notes"]
    # Front matter + 7 chapters + back matter = 9 link items, mirroring OCW's
    # /pages/course-notes/ index.
    assert len(items) == 9
    titles = [i["title"] for i in items]
    assert "Front matter" in titles
    assert "Chapter 1" in titles
    assert "Chapter 7" in titles
    assert "Back matter" in titles
    for it in items:
        assert it["kind"] == "link"
        assert "mit6_262s11_" in it["url"]


def test_modules_no_video_items():
    """Per feedback-module-content-chapter-readings Rule 1: video links never
    appear in Modules. No item should be `kind="video"` or have a video URL."""
    for _title, items in _modules():
        for it in items:
            assert it["kind"] != "video"
            url = it.get("url", "") or ""
            # The video-gallery landing URL is allowed in Direct links; per-lecture
            # video resource URLs (slug pattern "/resources/lecture-N-...") are not.
            assert "/resources/lecture-" not in url


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
    # 3 modules (Direct links + Course Notes + Practice exams).
    # 14 assignments = 12 PSets + 1 midterm + 1 final.
    # 8 direct-links + 9 Course Notes + 6 practice exams = 23 module items.
    assert n_modules == 3
    assert n_assign == 14
    assert n_items == 23


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


def _make_assignment(db) -> Assignment:
    c = Course(code="TMP", title="t", institution="i", term_label="x")
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

    # Fake the network: HTML page → fake PDF bytes.
    captured = {}

    def _fake_resolve(slug):
        captured["resolved_slug"] = slug
        return f"https://ocw.mit.edu/fake/{slug}.pdf"

    class _Resp:
        content = b"%PDF-1.4\nfakebytes"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _fake_resolve)
    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _Resp())

    # Force the storage layer to use a tmp local root, not Supabase.
    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)

    seed_mod._attach_official_solution(db, a, "mit6_262s11_assn01_sol")
    db.commit()
    db.refresh(a)

    assert a.official_solution_file_path == "official/6_262/mit6_262s11_assn01_sol.pdf"
    # On success the URL is cleared so resolve_key picks the file branch.
    assert a.official_solution_url == ""
    stored = storage_mod.read_bytes("solutions", a.official_solution_file_path)
    assert stored == b"%PDF-1.4\nfakebytes"


def test_attach_official_solution_idempotent(db, monkeypatch, tmp_path):
    a = _make_assignment(db)
    # Pre-populate.
    a.official_solution_file_path = "official/6_262/mit6_262s11_assn01_sol.pdf"
    db.commit()
    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)
    # Pre-write the file so the read succeeds.
    storage_mod.upload_bytes(
        "solutions",
        "official/6_262/mit6_262s11_assn01_sol.pdf",
        b"existing",
        "application/pdf",
    )

    def _boom(*a, **k):
        raise AssertionError("network must not be hit when already present")

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _boom)
    monkeypatch.setattr(seed_mod.httpx, "get", _boom)

    seed_mod._attach_official_solution(db, a, "mit6_262s11_assn01_sol")
    db.commit()
    # Still set, unchanged.
    assert a.official_solution_file_path == "official/6_262/mit6_262s11_assn01_sol.pdf"
    # URL was never set in this test and the idempotent skip path must not touch it.
    assert a.official_solution_url == ""


def test_attach_official_solution_redownloads_when_storage_object_missing(
    db, monkeypatch, tmp_path
):
    """Pre-populated file_path but the underlying Storage object is missing
    (e.g. bucket cleared / object deleted out-of-band) — the helper must
    re-download rather than trust the stale path."""
    a = _make_assignment(db)
    # Pre-populate but DON'T write the file to storage — read_bytes will fail.
    a.official_solution_file_path = "official/6_262/mit6_262s11_assn01_sol.pdf"
    db.commit()

    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)

    # Network must be hit this time.
    monkeypatch.setattr(
        seed_mod, "_resolve_pdf_url", lambda slug: f"https://x/{slug}.pdf"
    )

    class _Resp:
        content = b"fresh-pdf-bytes"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _Resp())

    seed_mod._attach_official_solution(db, a, "mit6_262s11_assn01_sol")
    db.commit()
    db.refresh(a)

    # File path unchanged (already matched the storage_key); URL cleared on
    # successful re-download; bytes now present.
    assert a.official_solution_file_path == "official/6_262/mit6_262s11_assn01_sol.pdf"
    assert a.official_solution_url == ""
    stored = storage_mod.read_bytes("solutions", a.official_solution_file_path)
    assert stored == b"fresh-pdf-bytes"


def test_attach_official_solution_graceful_on_failure(db, monkeypatch, tmp_path):
    a = _make_assignment(db)

    def _fail_resolve(slug):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _fail_resolve)
    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)

    # Must not raise.
    seed_mod._attach_official_solution(db, a, "mit6_262s11_assn01_sol")
    db.commit()
    db.refresh(a)
    # URL is still set as a fallback flag; file_path stays empty.
    assert a.official_solution_file_path == ""
    assert a.official_solution_url.endswith("/resources/mit6_262s11_assn01_sol/")


def test_seed_uploads_official_solutions(db, monkeypatch, tmp_path):
    # Stub the resolver to return predictable URLs and the network to return
    # fake PDFs. Exercises the per-assignment loop end-to-end.
    def _fake_resolve(slug):
        return f"https://ocw.mit.edu/fake/{slug}.pdf"

    class _Resp:
        content = b"%PDF-fake"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _fake_resolve)
    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _Resp())
    monkeypatch.setattr(storage_mod, "_supabase_configured", lambda: False)
    monkeypatch.setattr(storage_mod, "_LOCAL_ROOT", tmp_path)

    c = seed_mod.seed(db)
    paths = [a.official_solution_file_path for a in c.assignments]
    # All 14 graded assignments must have a path.
    assert len(paths) == 14
    assert all(p.startswith("official/6_262/") and p.endswith(".pdf") for p in paths)
    # All 12 PSets present.
    ps_paths = sorted(
        p for p in paths if "_assn" in p
    )
    assert len(ps_paths) == 12
    assert ps_paths[0].endswith("mit6_262s11_assn01_sol.pdf")
    assert ps_paths[-1].endswith("mit6_262s11_assn12_sol.pdf")
    # Midterm + Final present (2011 papers only).
    assert any(p.endswith("mit6_262s11_mid11_sol.pdf") for p in paths)
    assert any(p.endswith("mit6_262s11_final11_sol.pdf") for p in paths)
    # All URLs cleared — the autouse fixture's mocks succeed by default, so
    # every assignment goes through the success path which clears the URL
    # (resolve_key then picks the file branch).
    assert all(a.official_solution_url == "" for a in c.assignments)


def test_update_urls_refreshes_module_items(db):
    c = seed_mod.seed(db)
    # Manually corrupt a fixed-title item URL to simulate drift.
    for m in c.modules:
        for it in m.items:
            if it.title == "Syllabus":
                it.external_url = "https://example.com/STALE"
    db.commit()

    counts = seed_mod.update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] >= 1

    # The Syllabus URL is now correct again.
    found = False
    for m in c.modules:
        for it in m.items:
            if it.title == "Syllabus":
                assert it.external_url == seed_mod.SYLLABUS_URL
                found = True
    assert found


def test_update_urls_does_not_redownload_pdfs(db, monkeypatch):
    c = seed_mod.seed(db)

    def _boom(*a, **k):
        raise AssertionError("update_urls must NOT call _resolve_pdf_url")

    monkeypatch.setattr(seed_mod, "_resolve_pdf_url", _boom)
    counts = seed_mod.update_urls(db)
    assert counts["course_found"] is True
    # Solution file paths preserved.
    for a in c.assignments:
        assert a.official_solution_file_path.startswith("official/6_262/")


def test_update_urls_refreshes_assignment_fields(db):
    c = seed_mod.seed(db)
    ps1 = next(a for a in c.assignments if a.title.startswith("Problem Set 1 "))
    mid = next(a for a in c.assignments if a.title.startswith("Midterm Exam"))
    fin = next(a for a in c.assignments if a.title.startswith("Final Exam"))

    # Corrupt description + coverage on PS1; descriptions on midterm and final.
    # NOTE: We don't corrupt official_solution_url here — after seed (success
    # path) file_path is set so update_urls deliberately leaves the URL alone
    # to preserve the empty-URL state that lets resolve_key pick the file
    # branch. See _attach_official_solution.
    ps1.description_md = "STALE"
    ps1.covers_lecture_from = 999
    ps1.covers_lecture_to = 999
    mid.description_md = "STALE-MID"
    fin.description_md = "STALE-FIN"
    db.commit()

    counts = seed_mod.update_urls(db)
    # 3 assignments touched (ps1, mid, fin) — each counted once.
    assert counts["assignments_updated"] >= 3
    # PS1 coverage refreshed (1, 3) per PROBLEM_SETS[0].
    assert counts["coverage_updated"] >= 1
    db.refresh(ps1)
    db.refresh(mid)
    db.refresh(fin)
    assert ps1.description_md != "STALE"
    assert ps1.covers_lecture_from == 1
    assert ps1.covers_lecture_to == 3
    # URL stays empty because file_path is set (seed succeeded).
    assert ps1.official_solution_url == ""
    assert mid.description_md != "STALE-MID"
    assert fin.description_md != "STALE-FIN"


def test_refresh_solutions_redownloads(db, monkeypatch, tmp_path):
    # First seed call uses the autouse-fixture's default mocks → bytes b"%PDF-fake".
    c = seed_mod.seed(db)

    # Verify pre-state: each assignment has a path with the default bytes.
    a0 = c.assignments[0]
    pre_bytes = storage_mod.read_bytes("solutions", a0.official_solution_file_path)
    assert pre_bytes == b"%PDF-fake"

    # Now flip the fake bytes and call refresh.
    class _Resp2:
        content = b"second"
        def raise_for_status(self): pass

    monkeypatch.setattr(seed_mod.httpx, "get", lambda url, **kw: _Resp2())
    counts = seed_mod.refresh_solutions(db)
    assert counts["course_found"] is True
    assert counts["refreshed"] == 14
    # Storage now contains the second version.
    post_bytes = storage_mod.read_bytes("solutions", a0.official_solution_file_path)
    assert post_bytes == b"second"
