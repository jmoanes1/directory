"""Build organizational hierarchy data for org chart visualization."""

from employees.models import Employee


def build_org_tree(root_employee=None):
    """
    Build nested tree structure from manager relationships.
    Returns dict suitable for JSON serialization and chart rendering.
    """
    employees = Employee.objects.filter(is_active=True).select_related(
        "department", "position", "manager"
    )

    # Index employees by id
    emp_map = {e.pk: e for e in employees}
    children_map = {e.pk: [] for e in employees}

    roots = []
    for emp in employees:
        if emp.manager_id and emp.manager_id in children_map:
            children_map[emp.manager_id].append(emp.pk)
        elif not emp.manager_id or emp.manager_id not in emp_map:
            roots.append(emp.pk)

    def build_node(emp_id):
        emp = emp_map.get(emp_id)
        if not emp:
            return None
        return {
            "id": emp.pk,
            "employee_id": emp.employee_id,
            "name": emp.full_name,
            "initials": emp.initials,
            "department": emp.department.name,
            "position": emp.position.title,
            "email": emp.email,
            "photo_url": emp.profile_photo.url if emp.profile_photo else "",
            "direct_reports_count": len(children_map.get(emp_id, [])),
            "children": [
                build_node(child_id)
                for child_id in sorted(
                    children_map.get(emp_id, []),
                    key=lambda cid: emp_map[cid].last_name if cid in emp_map else "",
                )
            ],
        }

    if root_employee:
        root_id = root_employee.pk if isinstance(root_employee, Employee) else root_employee
        node = build_node(root_id)
        return [node] if node else []

    return [build_node(rid) for rid in sorted(roots, key=lambda rid: emp_map[rid].last_name if rid in emp_map else "")]


def build_department_hierarchy():
    """Build team hierarchy grouped by department with managers."""
    from departments.models import Department

    departments = Department.objects.filter(is_active=True).prefetch_related(
        "employees", "employees__position", "employees__manager"
    )

    hierarchy = []
    for dept in departments:
        members = dept.employees.filter(is_active=True).select_related("position", "manager")
        head = dept.head
        dept_managers = members.filter(direct_reports__isnull=False).distinct()

        hierarchy.append({
            "id": dept.pk,
            "name": dept.name,
            "head": {
                "id": head.pk,
                "name": head.full_name,
                "position": head.position.title,
            } if head else None,
            "employee_count": members.count(),
            "teams": [
                {
                    "manager": {
                        "id": mgr.pk,
                        "name": mgr.full_name,
                        "position": mgr.position.title,
                    },
                    "members": [
                        {
                            "id": m.pk,
                            "name": m.full_name,
                            "position": m.position.title,
                        }
                        for m in members.filter(manager=mgr).order_by("last_name")
                    ],
                }
                for mgr in dept_managers.order_by("last_name")
            ],
            "unassigned": [
                {"id": m.pk, "name": m.full_name, "position": m.position.title}
                for m in members.filter(manager__isnull=True).exclude(pk=head.pk if head else None).order_by("last_name")
            ],
        })

    return hierarchy


def get_org_stats():
    """Summary statistics for org chart page."""
    total = Employee.objects.filter(is_active=True).count()
    with_manager = Employee.objects.filter(is_active=True, manager__isnull=False).count()
    top_level = Employee.objects.filter(is_active=True, manager__isnull=True).count()
    managers = Employee.objects.filter(is_active=True, direct_reports__isnull=False).distinct().count()

    return {
        "total_employees": total,
        "with_manager": with_manager,
        "top_level": top_level,
        "managers": managers,
    }
