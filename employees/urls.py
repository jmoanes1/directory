"""Employee URL routes."""

from django.urls import path

from employees import views
from employees import views_extras

app_name = "employees"

urlpatterns = [
    path("", views.employee_list_view, name="list"),
    path("search/", views.employee_search_ajax, name="search_ajax"),
    path("create/", views.employee_create_view, name="create"),
    path("<int:pk>/", views.employee_detail_view, name="detail"),
    path("<int:pk>/edit/", views.employee_edit_view, name="edit"),
    path("<int:pk>/delete/", views.employee_delete_view, name="delete"),
    path("<int:pk>/toggle-active/", views.employee_toggle_active_view, name="toggle_active"),
    path("<int:pk>/create-account/", views.employee_create_account_view, name="create_account"),
    path("<int:pk>/qr/", views.employee_qr_view, name="qr"),
    path("export/excel/", views.employee_export_excel, name="export_excel"),
    path("export/pdf/", views.employee_export_pdf, name="export_pdf"),
    path("print/", views.employee_print_view, name="print"),
    path("positions/<int:department_id>/", views.positions_by_department_ajax, name="positions_by_department"),
    path("announcements/", views.announcement_list_view, name="announcements"),
    path("audit-log/", views.audit_log_view, name="audit_log"),
    path("recognition/", views.recognition_wall_view, name="recognition_wall"),
    path("<int:pk>/timeline/add/", views.employee_timeline_add, name="timeline_add"),
    path("<int:pk>/recognition/add/", views.employee_recognition_add, name="recognition_add"),
    # Advanced modules
    path("org-chart/", views_extras.org_chart_view, name="org_chart"),
    path("org-chart/data/", views_extras.org_chart_data_ajax, name="org_chart_data"),
    path("team-hierarchy/", views_extras.team_hierarchy_view, name="team_hierarchy"),
    path("ai-search/", views_extras.ai_search_view, name="ai_search"),
    path("ai-search/query/", views_extras.ai_search_ajax, name="ai_search_ajax"),
    path("skills/", views_extras.skills_matrix_view, name="skills_matrix"),
    path("skills/create/", views_extras.skill_create_view, name="skill_create"),
    path("skills/assign/", views_extras.employee_skill_assign_view, name="skill_assign"),
    path("<int:pk>/id-card/", views_extras.id_card_view, name="id_card"),
    path("<int:pk>/id-card/download/", views_extras.id_card_download_view, name="id_card_download"),
]
