# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# ===== مدل جدید را ایمپورت کنید =====
from .models import User, Process, ProcessStep, Request, RequestHistory, Notification
from django.urls import path
from django.shortcuts import render
from .utils import generate_process_graph, generate_org_chart_graph
from django.utils.html import format_html
from jalali_date.widgets import AdminSplitJalaliDateTime
from django.db import models# ===== تغییر نهایی و صحیح: ایمپورت کردن ویجت درست برای تاریخ و زمان =====
from jalali_date.widgets import AdminSplitJalaliDateTime
from django.db import models

class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 1

# این کلاس پایه به جنگو می‌گوید که برای تمام فیلدهای تاریخ و زمان (DateTimeField)،
# از ویجت تقویم شمسی جداگانه برای تاریخ و زمان استفاده کن.
class JalaliModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.DateTimeField: {'widget': AdminSplitJalaliDateTime}
    }

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    inlines = [ProcessStepInline]
    change_form_template = "admin/core/process/change_form.html"

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['process_graph_svg'] = None
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        process = self.get_object(request, object_id)
        if process and process.steps.exists():
            extra_context['process_graph_svg'] = generate_process_graph(process)
        else:
            extra_context['process_graph_svg'] = "ابتدا مراحل فرایند را ذخیره کنید تا گراف نمایش داده شود."
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    
    list_display = ('process', 'name', 'step_order', 'responsible_unit', 'default_responsible_user', 'deadline_days')
    list_filter = ('process', 'responsible_unit')
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        ProcessStep._meta.get_field('default_responsible_user').help_text = \
            "این فیلد را خالی بگذارید تا درخواست به صورت خودکار به مدیر مستقیم ثبت‌کننده ارجاع داده شود."
        return fieldsets

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('manager',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('manager',)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('org-chart/', self.admin_site.admin_view(self.org_chart_view), name='user_org_chart'),
        ]
        return custom_urls + urls

    def org_chart_view(self, request):
        root_users = User.objects.filter(manager__isnull=True).prefetch_related('subordinates')
        org_chart_svg = generate_org_chart_graph(root_users)
        context = dict(
           self.admin_site.each_context(request),
           title="چارت سازمانی",
           org_chart_svg=org_chart_svg,
        )
        return render(request, "admin/org_chart.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_org_chart_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(RequestHistory)
class RequestHistoryAdmin(JalaliModelAdmin):
    list_display = ('request', 'step', 'action_user', 'action_type', 'timestamp')
    list_filter = ('action_type',)

# ===== مدل جدید را در ادمین رجیستر کنید =====
@admin.register(Notification)
class NotificationAdmin(JalaliModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'user')

admin.site.register(User, CustomUserAdmin)