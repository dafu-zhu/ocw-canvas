from app.models import Course, ModuleItem
from seed.seed_template_course import CODE, seed


def _shape(course: Course) -> tuple[int, int, int]:
    n_modules = len(course.modules)
    n_items = sum(len(m.items) for m in course.modules)
    n_assign = len(course.assignments)
    return n_modules, n_items, n_assign


def test_seed_creates_18_100b(db):
    c = seed(db)
    assert c.code == CODE
    assert c.title == "Real Analysis"
    assert c.status == "planned"
    assert c.color == "#A31F34"
    assert c.syllabus_md and "50%" in c.syllabus_md  # the grading split

    # 3 weighted groups summing to 100; Problem Sets drops the lowest 1
    weights = {g.name: (g.weight, g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Problem Sets"] == (50, 1)
    assert weights["Midterm"] == (20, 0)
    assert weights["Final Exam"] == (30, 0)
    assert sum(float(g.weight) for g in c.assignment_groups) == 100

    # 10 problem sets + Midterm + Final = 12 assignments
    n_modules, n_items, n_assign = _shape(c)
    assert n_assign == 12
    assert n_modules >= 8
    assert n_items > 30

    # at least one module item points at an assignment, and it resolves
    assign_items = [i for m in c.modules for i in m.items if i.kind == "assignment"]
    assert assign_items
    for it in assign_items:
        assert it.assignment_id is not None
        assert db.get(ModuleItem, it.id).assignment_id == it.assignment_id

    # every link/video item links out to mit.edu, nothing is re-hosted
    for m in c.modules:
        for it in m.items:
            if it.kind in ("link", "video"):
                assert "ocw.mit.edu" in it.external_url


def test_seed_is_idempotent(db):
    c1 = seed(db)
    id1 = c1.id
    n1 = _shape(c1)
    c2 = seed(db)  # no force -> same course, no duplication
    assert c2.id == id1
    assert _shape(c2) == n1
    assert db.query(Course).filter(Course.code == CODE).count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == CODE).count() == 1
    assert len(c.assignments) == 12
