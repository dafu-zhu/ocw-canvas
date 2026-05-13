from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem


def test_course_module_item_cascade(db):
    course = Course(code="MIT 18.100B", title="Real Analysis")
    db.add(course)
    db.flush()
    module = Module(course_id=course.id, title="Unit 1", position=0)
    db.add(module)
    db.flush()
    db.add(
        ModuleItem(
            module_id=module.id,
            kind="link",
            title="OCW page",
            external_url="https://ocw.mit.edu",
            position=0,
        )
    )
    db.commit()

    db.delete(course)
    db.commit()
    assert db.query(Module).count() == 0
    assert db.query(ModuleItem).count() == 0


def test_assignment_belongs_to_group_and_course(db):
    course = Course(code="MIT 18.100B", title="Real Analysis")
    db.add(course)
    db.flush()
    group = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=50, drop_lowest_n=1, position=0
    )
    db.add(group)
    db.flush()
    a = Assignment(
        course_id=course.id, assignment_group_id=group.id, title="Problem Set 1", points_possible=100
    )
    db.add(a)
    db.commit()
    assert a.group.name == "Problem Sets"
    assert a.course.code == "MIT 18.100B"
