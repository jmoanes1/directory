"""
AI-powered employee search engine.
Parses natural language queries into structured filters without external API dependency.
"""

import re
from datetime import date

from django.db.models import Q

from departments.models import Department
from employees.models import Employee, Skill
from positions.models import Position


# Intent patterns for natural language parsing
STATUS_KEYWORDS = {
    "active": Employee.EmploymentStatus.ACTIVE,
    "inactive": Employee.EmploymentStatus.INACTIVE,
    "on leave": Employee.EmploymentStatus.ON_LEAVE,
    "terminated": Employee.EmploymentStatus.TERMINATED,
}

QUERY_PATTERNS = [
    (r"who (?:reports to|works (?:under|for)) (.+)", "manager"),
    (r"(?:find|show|list|search) (.+?) in (.+?)(?:\s+department)?$", "dept_search"),
    (r"(?:find|show|list|search) (.+)", "general_search"),
    (r"(?:employees|people|staff) (?:in|from|at) (.+)", "department"),
    (r"(?:hired|joined) (?:in|during|since) (\d{4})", "hired_year"),
    (r"(?:with skill|skilled in|knows?) (.+)", "skill"),
    (r"manager(?:s)? (?:named|called)? (.+)", "manager_name"),
    (r"(?:email|contact) (.+)", "email_search"),
    (r"employee id (.+)", "employee_id"),
    (r"birthday (?:in|on) (\w+)", "birthday_month"),
    (r"how many (.+)", "count"),
]


def parse_natural_query(query: str) -> dict:
    """Parse a natural language query into structured search parameters."""
    query = query.strip().lower()
    if not query:
        return {"original_query": query, "interpreted": "Empty query"}

    params = {
        "original_query": query,
        "search_terms": [],
        "department": None,
        "position": None,
        "status": None,
        "manager_name": None,
        "skill": None,
        "hired_year": None,
        "birthday_month": None,
        "employee_id": None,
        "interpreted": "",
    }

    # Detect status keywords
    for keyword, status in STATUS_KEYWORDS.items():
        if keyword in query:
            params["status"] = status
            query = query.replace(keyword, "").strip()

    # Pattern matching
    for pattern, intent in QUERY_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            if intent == "manager":
                params["manager_name"] = match.group(1).strip()
                params["interpreted"] = f"Employees reporting to '{params['manager_name']}'"
            elif intent == "dept_search":
                params["search_terms"] = [match.group(1).strip()]
                params["department"] = match.group(2).strip()
                params["interpreted"] = f"'{match.group(1)}' in {match.group(2)} department"
            elif intent == "department":
                params["department"] = match.group(1).strip()
                params["interpreted"] = f"Employees in {match.group(1)}"
            elif intent == "hired_year":
                params["hired_year"] = int(match.group(1))
                params["interpreted"] = f"Hired in {match.group(1)}"
            elif intent == "skill":
                params["skill"] = match.group(1).strip()
                params["interpreted"] = f"Employees with skill '{match.group(1)}'"
            elif intent == "manager_name":
                params["manager_name"] = match.group(1).strip()
                params["interpreted"] = f"Manager named '{match.group(1)}'"
            elif intent == "email_search":
                params["search_terms"] = [match.group(1).strip()]
                params["interpreted"] = f"Contact search for '{match.group(1)}'"
            elif intent == "employee_id":
                params["employee_id"] = match.group(1).strip().upper()
                params["interpreted"] = f"Employee ID {match.group(1).upper()}"
            elif intent == "birthday_month":
                params["birthday_month"] = match.group(1).strip()
                params["interpreted"] = f"Birthdays in {match.group(1)}"
            elif intent == "count":
                params["department"] = match.group(1).strip()
                params["interpreted"] = f"Count of {match.group(1)}"
            break

    # Fallback: treat entire query as general search
    if not params["interpreted"]:
        params["search_terms"] = query.split()
        params["interpreted"] = f"Searching for: {' '.join(params['search_terms'])}"

    return params


def _resolve_department(name: str):
    """Fuzzy match department by name."""
    if not name:
        return None
    dept = Department.objects.filter(name__icontains=name, is_active=True).first()
    return dept


def _resolve_manager(name: str):
    """Find manager employee by name."""
    if not name:
        return None
    parts = name.split()
    qs = Employee.objects.filter(is_active=True)
    if len(parts) >= 2:
        return qs.filter(
            first_name__icontains=parts[0],
            last_name__icontains=parts[-1],
        ).first()
    return qs.filter(
        Q(first_name__icontains=name) | Q(last_name__icontains=name)
    ).first()


def _month_number(month_name: str):
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
        "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    }
    return months.get(month_name.lower())


def ai_search_employees(query: str, limit: int = 20):
    """
    Execute AI-powered employee search.
    Returns queryset, parsed params, and summary message.
    """
    params = parse_natural_query(query)
    qs = Employee.objects.select_related("department", "position", "manager").filter(is_active=True)

    if params.get("employee_id"):
        qs = qs.filter(employee_id__icontains=params["employee_id"])

    if params.get("department"):
        dept = _resolve_department(params["department"])
        if dept:
            qs = qs.filter(department=dept)
        else:
            qs = qs.filter(department__name__icontains=params["department"])

    if params.get("manager_name"):
        manager = _resolve_manager(params["manager_name"])
        if manager:
            qs = qs.filter(manager=manager)
        else:
            qs = qs.filter(
                Q(manager__first_name__icontains=params["manager_name"])
                | Q(manager__last_name__icontains=params["manager_name"])
            )

    if params.get("skill"):
        qs = qs.filter(skills__skill__name__icontains=params["skill"]).distinct()

    if params.get("hired_year"):
        qs = qs.filter(date_hired__year=params["hired_year"])

    if params.get("birthday_month"):
        month = _month_number(params["birthday_month"])
        if month:
            qs = qs.filter(date_of_birth__month=month)

    if params.get("status"):
        qs = qs.filter(employment_status=params["status"])

    if params.get("search_terms"):
        term_q = Q()
        for term in params["search_terms"]:
            term_q |= (
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(email__icontains=term)
                | Q(position__title__icontains=term)
                | Q(department__name__icontains=term)
                | Q(employee_id__icontains=term)
            )
        qs = qs.filter(term_q)

    count = qs.count()
    results = qs[:limit]

    if count == 0:
        summary = f"No employees found for: {params['interpreted']}"
    elif count == 1:
        summary = f"Found 1 employee matching: {params['interpreted']}"
    else:
        summary = f"Found {count} employees matching: {params['interpreted']}"

    return results, params, summary


def generate_chat_response(query: str) -> dict:
    """Generate directory assistant response for chat interface."""
    query_lower = query.lower().strip()

    # Greeting responses
    if query_lower in ("hi", "hello", "hey", "help"):
        return {
            "type": "text",
            "message": (
                "Hello! I'm your Directory Assistant. I can help you find employees. Try asking:\n"
                "• \"Find engineers in Engineering\"\n"
                "• \"Who reports to John Doe?\"\n"
                "• \"Employees hired in 2024\"\n"
                "• \"Show active HR staff\"\n"
                "• \"Employees with Python skill\""
            ),
            "employees": [],
        }

    # Count queries
    if query_lower.startswith("how many"):
        params = parse_natural_query(query)
        qs = Employee.objects.filter(is_active=True)
        if params.get("department"):
            dept = _resolve_department(params["department"])
            if dept:
                qs = qs.filter(department=dept)
                return {
                    "type": "text",
                    "message": f"There are {qs.count()} active employees in {dept.name}.",
                    "employees": [],
                }
        total = Employee.objects.filter(is_active=True).count()
        return {
            "type": "text",
            "message": f"There are {total} active employees in the company.",
            "employees": [],
        }

    results, params, summary = ai_search_employees(query, limit=5)
    employees_data = [
        {
            "id": e.pk,
            "name": e.full_name,
            "department": e.department.name,
            "position": e.position.title,
            "email": e.email,
            "employee_id": e.employee_id,
        }
        for e in results
    ]

    return {
        "type": "search_results",
        "message": summary,
        "interpreted": params.get("interpreted", ""),
        "employees": employees_data,
    }
