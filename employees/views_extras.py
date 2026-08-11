"""Extended employee views: org chart and ID cards."""

import io
import json

import qrcode
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from employees.models import Employee
from employees.org_chart import build_org_tree, get_org_stats
from employees.utils import log_activity


@login_required
def org_chart_view(request):
    """Interactive organizational chart visualization."""
    root_id = request.GET.get("root")
    root_employee = None
    if root_id:
        root_employee = get_object_or_404(Employee, pk=root_id)

    tree = build_org_tree(root_employee)
    stats = get_org_stats()
    top_managers = Employee.objects.filter(
        is_active=True, direct_reports__isnull=False
    ).distinct().order_by("last_name")[:20]

    return render(request, "employees/org_chart.html", {
        "org_tree_json": json.dumps(tree),
        "stats": stats,
        "top_managers": top_managers,
        "root_employee": root_employee,
    })


@login_required
def org_chart_data_ajax(request):
    """AJAX endpoint for org chart tree data."""
    root_id = request.GET.get("root")
    root = int(root_id) if root_id else None
    tree = build_org_tree(root)
    return JsonResponse({"tree": tree})


@login_required
def id_card_view(request, pk):
    """Preview employee ID card."""
    employee = get_object_or_404(
        Employee.objects.select_related("department", "position"), pk=pk
    )
    return render(request, "employees/id_card.html", {"employee": employee})


@login_required
def id_card_download_view(request, pk):
    """Generate downloadable PDF employee ID card."""
    employee = get_object_or_404(
        Employee.objects.select_related("department", "position"), pk=pk
    )

    buffer = io.BytesIO()
    card_width, card_height = 3.375 * inch, 2.125 * inch  # Standard CR80
    page_width, page_height = letter

    c = canvas.Canvas(buffer, pagesize=letter)
    x = (page_width - card_width) / 2
    y = (page_height - card_height) / 2

    # Card background
    c.setFillColor(colors.HexColor("#1e293b"))
    c.roundRect(x, y, card_width, card_height, 8, fill=1, stroke=0)

    # Header bar
    c.setFillColor(colors.HexColor("#2563eb"))
    c.roundRect(x, y + card_height - 0.45 * inch, card_width, 0.45 * inch, 8, fill=1, stroke=0)
    c.rect(x, y + card_height - 0.45 * inch, card_width, 0.15 * inch, fill=1, stroke=0)

    # Company name
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 0.15 * inch, y + card_height - 0.3 * inch, "EMPLOYEE DIRECTORY")

    # Photo placeholder or image
    photo_x = x + 0.15 * inch
    photo_y = y + 0.35 * inch
    photo_size = 0.85 * inch
    c.setFillColor(colors.HexColor("#334155"))
    c.roundRect(photo_x, photo_y, photo_size, photo_size, 4, fill=1, stroke=0)

    if employee.profile_photo:
        try:
            c.drawImage(
                ImageReader(employee.profile_photo.path),
                photo_x, photo_y, photo_size, photo_size,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(photo_x + photo_size / 2, photo_y + photo_size / 2 - 5, employee.initials)
    else:
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(photo_x + photo_size / 2, photo_y + photo_size / 2 - 5, employee.initials)

    # Employee info
    info_x = photo_x + photo_size + 0.12 * inch
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(info_x, y + card_height - 0.65 * inch, employee.full_name[:28])

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawString(info_x, y + card_height - 0.82 * inch, employee.position.title[:30])
    c.drawString(info_x, y + card_height - 0.97 * inch, employee.department.name[:30])

    c.setFillColor(colors.HexColor("#2563eb"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(info_x, y + 0.55 * inch, employee.employee_id)

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 7)
    c.drawString(info_x, y + 0.38 * inch, employee.email[:35])

    # QR code
    profile_url = request.build_absolute_uri(reverse("employees:detail", kwargs={"pk": pk}))
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(profile_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="white", back_color="#1e293b")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), x + card_width - 0.85 * inch, y + 0.15 * inch, 0.7 * inch, 0.7 * inch)

    # Footer
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 6)
    c.drawString(x + 0.15 * inch, y + 0.12 * inch, f"Hired: {employee.date_hired.strftime('%b %Y')}")

    c.showPage()
    c.save()

    log_activity(request, "export", f"Generated ID card for {employee.full_name}", "Employee", employee.pk)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{employee.employee_id}_id_card.pdf"'
    return response
