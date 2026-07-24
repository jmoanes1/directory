"""REST API viewsets."""

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import (
    IsDepartmentManagerOrReadOnly,
    IsHRManagerOrReadOnly,
    IsPositionManagerOrReadOnly,
)
from api.serializers import DepartmentSerializer, EmployeeSerializer, PositionSerializer
from departments.models import Department
from employees.models import Employee
from positions.models import Position


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("department", "position", "manager").all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRManagerOrReadOnly]
    search_fields = ["first_name", "last_name", "email", "employee_id"]
    ordering_fields = ["last_name", "first_name", "date_hired", "employee_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search", "")
        department = self.request.query_params.get("department", "")
        position = self.request.query_params.get("position", "")
        status = self.request.query_params.get("status", "")

        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(employee_id__icontains=search)
            )
        if department:
            qs = qs.filter(department_id=department)
        if position:
            qs = qs.filter(position_id=position)
        if status:
            qs = qs.filter(employment_status=status)
        return qs

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        employee = self.get_object()
        employee.is_active = not employee.is_active
        if employee.is_active:
            employee.employment_status = Employee.EmploymentStatus.ACTIVE
        else:
            employee.employment_status = Employee.EmploymentStatus.INACTIVE
        employee.save()
        return Response(EmployeeSerializer(employee).data)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("head").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsDepartmentManagerOrReadOnly]
    search_fields = ["name", "code"]


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.select_related("department").all()
    serializer_class = PositionSerializer
    permission_classes = [IsPositionManagerOrReadOnly]
    search_fields = ["title"]

    def get_queryset(self):
        qs = super().get_queryset()
        department = self.request.query_params.get("department", "")
        if department:
            qs = qs.filter(department_id=department)
        return qs
