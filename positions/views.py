"""Position views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import position_manager_required
from employees.utils import log_activity
from positions.forms import PositionForm
from positions.models import Position


@login_required
def position_list_view(request):
    positions = Position.objects.select_related("department").all()
    return render(request, "positions/list.html", {
        "positions": positions,
        "can_manage": request.user.can_manage_positions(),
    })


@position_manager_required
def position_create_view(request):
    form = PositionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        position = form.save()
        log_activity(request, "create", f"Created position {position.title}", "Position", position.pk, position.title)
        messages.success(request, f"Position {position.title} created successfully.")
        return redirect("positions:list")

    return render(request, "positions/form.html", {"form": form, "title": "Create Position"})


@position_manager_required
def position_edit_view(request, pk):
    position = get_object_or_404(Position, pk=pk)
    form = PositionForm(request.POST or None, instance=position)
    if request.method == "POST" and form.is_valid():
        position = form.save()
        log_activity(request, "update", f"Updated position {position.title}", "Position", position.pk, position.title)
        messages.success(request, f"Position {position.title} updated successfully.")
        return redirect("positions:list")

    return render(request, "positions/form.html", {
        "form": form, "position": position, "title": "Edit Position",
    })


@position_manager_required
@require_POST
def position_delete_view(request, pk):
    position = get_object_or_404(Position, pk=pk)
    if position.employees.exists():
        messages.error(request, "Cannot delete position with assigned employees.")
        return redirect("positions:list")

    title = position.title
    pos_id = position.pk
    position.delete()
    log_activity(request, "delete", f"Deleted position {title}", "Position", pos_id, title)
    messages.success(request, f"Position {title} deleted successfully.")
    return redirect("positions:list")
