from app.models import Course
from seed.seed_cornell_cs4220 import (
    BASE,
    CODE,
    DESCRIPTION,
    HOME,
    HOME_MD,
    HOMEWORKS,
    HW_DATA_URL,
    PROJ_DATA_URL,
    PROJECTS,
    SYLLABUS_MD,
    TEXTBOOK,
    _hw_url,
    _modules,
    _proj_url,
    seed,
    update_urls,
)


def test_code_and_base():
    assert CODE == "Cornell CS 4220"
    assert BASE == "https://www.cs.cornell.edu/courses/cs4220/2024sp"
    assert HOME == BASE + "/"


def test_hw_and_proj_urls():
    assert _hw_url(1) == BASE + "/hw1.pdf"
    assert _hw_url(6) == BASE + "/hw6.pdf"
    assert _proj_url(1) == BASE + "/P1.pdf"
    assert _proj_url(2) == BASE + "/P2.pdf"
    assert HW_DATA_URL == {2: BASE + "/hw2_data.zip"}
    assert PROJ_DATA_URL == {1: BASE + "/P1data.zip"}


def test_homeworks_cover_1_to_42_no_gaps():
    nums = [k for (k, *_rest) in HOMEWORKS]
    assert nums == [1, 2, 3, 4, 5, 6]
    last_to = 0
    for k, _topic, lec_from, lec_to in HOMEWORKS:
        assert lec_from == last_to + 1, f"HW{k} from must follow previous to"
        assert lec_to >= lec_from
        last_to = lec_to
    assert last_to == 42


def test_projects_overlap_homework_ranges():
    nums = [k for (k, *_rest) in PROJECTS]
    assert nums == [1, 2]
    assert PROJECTS[0][2] == 1 and PROJECTS[0][3] == 20
    assert PROJECTS[1][2] == 21 and PROJECTS[1][3] == 37


def test_modules_shape():
    mods = _modules()
    titles = [m[0] for m in mods]
    assert titles == [
        "Direct links",
        "Background & error analysis",
        "Direct linear solvers",
        "Least squares & QR",
        "Eigenvalue problems",
        "Iterative methods",
        "Nonlinear systems & optimization",
        "Advanced topics",
    ]


def test_modules_no_video_items():
    """Per feedback-module-content-chapter-readings Rule 1: no video items in
    Modules; Bindel publishes no video anyway."""
    for _title, items in _modules():
        for it in items:
            assert it["kind"] != "video"


def test_modules_direct_links_lists_hw_and_projects():
    mods = dict(_modules())
    titles = [i["title"] for i in mods["Direct links"]]
    for n in (1, 2, 3, 4, 5, 6):
        assert f"Homework {n}" in titles
    for n in (1, 2):
        assert f"Project {n}" in titles
    assert "CS 4220 / MATH 4260 course home (Bindel, Spring 2024)" in titles


def test_syllabus_describes_self_study_split():
    assert "60%" in SYLLABUS_MD
    assert "40%" in SYLLABUS_MD
    # Self-study version drops the take-home midterm/final.
    assert "Gradescope" in SYLLABUS_MD or "exam" in SYLLABUS_MD.lower()
    # Project-mode policy is documented.
    assert "project mode" in SYLLABUS_MD.lower()


def test_home_md_mentions_bindel_and_self_study():
    assert "Bindel" in HOME_MD
    assert "self-study" in HOME_MD


def test_description_and_textbook_nonempty():
    assert "linear algebra" in DESCRIPTION.lower()
    assert "Ascher" in TEXTBOOK
    assert "Greif" in TEXTBOOK


def test_seed_creates_basic_shape(db):
    c = seed(db)
    assert c.code == CODE
    assert c.title == "Numerical Analysis: Linear and Nonlinear Problems"
    assert c.instructor == "Prof. David Bindel"
    assert c.institution == "Cornell University"
    assert c.term_label == "Spring 2030"
    assert c.color == "#B31B1B"
    assert c.display_order == 5
    assert c.status == "planned"
    assert c.external_home_url == HOME


def test_seed_groups_and_weights(db):
    c = seed(db)
    weights = {g.name: (float(g.weight), g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Homework"] == (60.0, 0)
    assert weights["Projects"] == (40.0, 0)
    assert sum(w for w, _ in weights.values()) == 100.0


def test_seed_assignment_and_module_counts(db):
    c = seed(db)
    assert len(c.assignments) == 8  # 6 HWs + 2 projects
    assert len(c.modules) == 8  # Direct links + 7 topic modules


def test_seed_homework_coverage(db):
    c = seed(db)
    hws = sorted(
        (a for a in c.assignments if a.title.startswith("Homework")),
        key=lambda a: a.position,
    )
    assert len(hws) == 6
    assert all(a.requires_solution_key for a in hws)
    assert hws[0].covers_lecture_from == 1
    assert hws[0].covers_lecture_to == 7
    assert hws[-1].covers_lecture_from == 37
    assert hws[-1].covers_lecture_to == 42


def test_seed_projects_use_project_mode(db):
    c = seed(db)
    projs = sorted(
        (a for a in c.assignments if a.title.startswith("Project")),
        key=lambda a: a.position,
    )
    assert len(projs) == 2
    assert all(not a.requires_solution_key for a in projs)
    assert projs[0].covers_lecture_from == 1
    assert projs[0].covers_lecture_to == 20
    assert projs[1].covers_lecture_from == 21
    assert projs[1].covers_lecture_to == 37
    for a in projs:
        assert "project mode" in a.description_md.lower()


def test_seed_module_items_no_video(db):
    c = seed(db)
    for m in c.modules:
        for it in m.items:
            assert it.kind != "video"


def test_seed_is_idempotent(db):
    c1 = seed(db)
    n1 = (len(c1.modules), len(c1.assignments))
    c2 = seed(db)
    assert c2.id == c1.id
    assert (len(c2.modules), len(c2.assignments)) == n1
    assert db.query(Course).filter(Course.code == CODE).count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == CODE).count() == 1
    assert len(c.assignments) == 8


def test_update_urls_idempotent(db):
    seed(db)
    counts1 = update_urls(db)
    counts2 = update_urls(db)
    assert counts1["course_found"] is True
    assert counts2["items_updated"] == 0
    assert counts2["assignments_updated"] == 0
    assert counts2["coverage_updated"] == 0


def test_update_urls_no_course(db):
    """If no Cornell CS 4220 course exists, update_urls returns course_found=False."""
    assert update_urls(db) == {"course_found": False}
