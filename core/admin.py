from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Process, ProcessStep, Request, RequestHistory

# این کلاس برای نمایش مراحل در داخل صفحه ویرایش فرایند استفاده می‌شود
class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 1 # یک فیلد خالی برای افزودن مرحله جدید

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    inlines = [ProcessStepInline]

@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ('process', 'name', 'step_order', 'responsible_unit', 'default_responsible_user')
    list_filter = ('process', 'responsible_unit')
    # کد زیر به صورت هوشمند، متن راهنما را به فیلد مسئول پیش‌فرض اضافه می‌کند
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # اضافه کردن متن راهنما
        ProcessStep._meta.get_field('default_responsible_user').help_text = \
            "این فیلد را خالی بگذارید تا درخواست به صورت خودکار به مدیر مستقیم ثبت‌کننده ارجاع داده شود."
        return fieldsets

# اضافه کردن فیلد "مدیر" به پنل ادمین کاربران
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('manager',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('manager',)}),
    )

# ثبت مدل‌ها در پنل ادمین
admin.site.register(User, CustomUserAdmin)
admin.site.register(Request)
admin.site.register(RequestHistory)