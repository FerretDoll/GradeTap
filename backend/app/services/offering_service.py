from sqlalchemy import select, update

from app.db.models import Account, ClassGroup, Course, Offering
from app.services.access import error


def offering_view(offering, course, group):
    return dict(id=offering.id, course_id=course.id, class_group_id=group.id,
                course_name=course.course_name, class_name=group.class_name, term=offering.term,
                teaching_role="owner", allowed_actions=["create_task", "review", "publish", "export"])


def owned_offerings(owner_id):
    return select(Offering, Course, ClassGroup).select_from(Offering).join(Course).join(
        ClassGroup, ClassGroup.id == Offering.class_group_id).where(Offering.owner_id == owner_id)


def list_offerings(db, owner_id):
    return [offering_view(*row) for row in db.execute(owned_offerings(owner_id).order_by(Offering.id))]


def create_offering(db, owner_id, body):
    # Serialize name-based creation as well as creation from existing IDs.
    db.execute(update(Account).where(Account.id == owner_id).values(id=Account.id))
    term = body.term.strip()
    query = owned_offerings(owner_id).where(Offering.term == term)
    objects = []
    for model, attr, identifier, name in [(Course, Course.course_name, body.course_id, body.course_name),
                                          (ClassGroup, ClassGroup.class_name, body.class_group_id, body.class_name)]:
        if identifier is None:
            obj = model(owner_id=owner_id, **{attr.key: name.strip()})
            query = query.where(attr == name.strip())
        else:
            obj = db.get(model, identifier)
            if obj is None or obj.owner_id != owner_id:
                raise error(404, "not_found", "课程或班级不存在")
            query = query.where(model.id == identifier)
        objects.append(obj)
    if db.execute(query.with_for_update()).first():
        raise error(409, "offering_already_exists", "本学期已存在相同授课班")
    course, group = objects
    db.add_all(objects)
    db.flush()
    offering = Offering(owner_id=owner_id, course_id=course.id, class_group_id=group.id, term=term)
    db.add(offering)
    db.commit()
    return offering_view(offering, course, group)
