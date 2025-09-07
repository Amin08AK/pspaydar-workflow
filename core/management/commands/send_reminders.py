# core/management/commands/send_reminders.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Request
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

class Command(BaseCommand):
    help = 'Sends reminder emails for overdue requests.'

    def handle(self, *args, **options):
        # درخواست‌های در حال بررسی که تاریخ سررسید آن‌ها گذشته است را پیدا کن
        overdue_requests = Request.objects.filter(
            status='IN_PROGRESS',
            due_date__isnull=False,
            due_date__lt=timezone.now()
        )

        if not overdue_requests.exists():
            self.stdout.write(self.style.SUCCESS('هیچ درخواست معوقی یافت نشد.'))
            return

        self.stdout.write(f'تعداد {overdue_requests.count()} درخواست معوق یافت شد. در حال ارسال ایمیل...')

        for req in overdue_requests:
            recipient = req.current_assignee
            if recipient and recipient.email:
                subject = f"یادآوری: وظیفه معوق در سیستم اتوماسیون - درخواست #{req.id}"
                
                # ساخت لینک مستقیم به درخواست
                # برای این کار باید اسکیم و دامنه را به صورت دستی تنظیم کنیم چون در کامند به request دسترسی نداریم
                domain = "your-domain.com" # <-- آدرس دامنه خود را اینجا وارد کنید
                scheme = "https"
                request_url = f"{scheme}://{domain}{reverse('request_detail', args=[req.id])}"

                message = f"""
کاربر گرامی {recipient.get_full_name() or recipient.username}،

این یک یادآوری است که مهلت انجام وظیفه زیر به پایان رسیده است:

- شناسه درخواست: #{req.id}
- فرایند: {req.process.name}
- تاریخ سررسید: {req.due_date.strftime('%Y-%m-%d')}

لطفاً در اسرع وقت جهت بررسی و اقدام به سیستم مراجعه فرمایید:
{request_url}

با تشکر،
سیستم اتوماسیون
"""
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient.email],
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f'ایمیل یادآوری برای درخواست #{req.id} به {recipient.email} ارسال شد.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'خطا در ارسال ایمیل برای درخواست #{req.id}: {e}'))
        
        self.stdout.write(self.style.SUCCESS('عملیات ارسال یادآوری‌ها به پایان رسید.'))