# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone # ایمپورت جدید

# مدل سفارشی کاربر برای اضافه کردن فیلد مدیر
class User(AbstractUser):
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')

    def __str__(self):
        return self.get_full_name() or self.username

# جدول تعریف کلی فرایندها
class Process(models.Model):
    name = models.CharField("نام فرایند", max_length=200)
    description = models.TextField("توضیحات", blank=True, null=True)
    is_active = models.BooleanField("فعال است؟", default=True)

    def __str__(self):
        return self.name

# جدول مراحل هر فرایند
class ProcessStep(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='steps', verbose_name="فرایند")
    name = models.CharField("نام مرحله", max_length=200)
    step_order = models.PositiveIntegerField("ترتیب مرحله")
    responsible_unit = models.CharField("واحد مسئول", max_length=100)
    default_responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="مسئول پیش‌فرض")
    # ===== فیلد جدید برای مهلت انجام =====
    deadline_days = models.PositiveIntegerField("مهلت انجام (به روز)", default=3, help_text="تعداد روز مجاز برای انجام این مرحله.")

    class Meta:
        ordering = ['process', 'step_order']

    def __str__(self):
        return f"{self.process.name} - مرحله {self.step_order}: {self.name}"

# جدول اصلی برای هر درخواست ثبت شده
class Request(models.Model):
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'در حال بررسی'),
        ('APPROVED', 'تایید شده'),
        ('REJECTED', 'رد شده'),
    ]

    process = models.ForeignKey(Process, on_delete=models.PROTECT, verbose_name="فرایند")
    initiator_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_requests', verbose_name="ثبت کننده")
    current_step = models.ForeignKey(ProcessStep, on_delete=models.PROTECT, null=True, blank=True, verbose_name="مرحله فعلی")
    current_assignee = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='assigned_requests', 
        null=True, 
        blank=True, 
        verbose_name="کاربر مسئول فعلی"
    )
    
    status = models.CharField("وضعیت", max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)
    # ===== فیلد جدید برای تاریخ سررسید =====
    due_date = models.DateTimeField("تاریخ سررسید", null=True, blank=True)

    def __str__(self):
        return f"درخواست {self.id} برای {self.process.name} توسط {self.initiator_user.username}"

    # ===== متد کمکی برای بررسی وضعیت سررسید =====
    @property
    def deadline_status(self):
        if self.status != 'IN_PROGRESS' or not self.due_date:
            return "normal"
        
        now = timezone.now()
        remaining_days = (self.due_date - now).days

        if remaining_days < 0:
            return "overdue" # معوق شده
        elif remaining_days <= 1:
            return "urgent" # فوری (کمتر از ۱ روز مانده)
        else:
            return "normal" # عادی

# جدول تاریخچه برای ردیابی هر اقدام روی درخواست
class RequestHistory(models.Model):
    ACTION_TYPES = [
        ('CREATED', 'ایجاد درخواست'),
        ('APPROVED', 'تایید و ارسال به مرحله بعد'),
        ('REJECTED', 'درخواست رد شد'),
        ('COMMENTED', 'نظر ثبت شد'),
        ('RETURNED', 'بازگردانده شد'),
        ('RESUBMITTED', 'مجدداً ارسال شد'),
    ]
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='history', verbose_name="درخواست")
    step = models.ForeignKey(ProcessStep, on_delete=models.PROTECT, null=True, blank=True, verbose_name="مرحله")
    action_user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="اقدام کننده")
    action_type = models.CharField("نوع اقدام", max_length=50, choices=ACTION_TYPES)
    timestamp = models.DateTimeField("زمان اقدام", auto_now_add=True)
    comments = models.TextField("توضیحات", blank=True, null=True)
    attachment = models.FileField("فایل پیوست", upload_to='attachments/%Y/%m/%d/', null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"تاریخچه برای درخواست {self.request.id} در مرحله {self.step.name if self.step else 'N/A'}"

# ===== مدل جدید برای اعلان‌های لحظه‌ای =====
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="کاربر")
    request = models.ForeignKey(Request, on_delete=models.CASCADE, verbose_name="درخواست مرتبط")
    message = models.CharField("پیام اعلان", max_length=255)
    is_read = models.BooleanField("خوانده شده؟", default=False)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"اعلان برای {self.user.username}: {self.message}"