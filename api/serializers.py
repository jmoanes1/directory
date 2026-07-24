"""REST API serializers."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from departments.models import Department
from employees.models import Employee
from positions.models import Position

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)
    head_name = serializers.CharField(source="head.full_name", read_only=True, default=None)

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "description", "head", "head_name",
            "employee_count", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Position
        fields = [
            "id", "title", "department", "department_name", "description",
            "employee_count", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default=None)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id", "employee_id", "first_name", "middle_name", "last_name", "full_name",
            "email", "phone_number", "date_of_birth", "gender", "address",
            "date_hired", "department", "department_name", "position", "position_title",
            "manager", "manager_name", "employment_status", "profile_photo",
            "emergency_contact", "bio", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["employee_id", "created_at", "updated_at"]

    def validate(self, data):
        position = data.get("position") or (self.instance.position if self.instance else None)
        department = data.get("department") or (self.instance.department if self.instance else None)
        if position and department and position.department_id != department.id:
            raise serializers.ValidationError({"position": "Position must belong to the selected department."})
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "phone"]
        read_only_fields = ["id"]
