# core/views.py

import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import User, Process, ProcessStep, Request, RequestHistory, Notification
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .utils import generate_process_graph
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q

def update_request_due_date(request_obj):
    """بر اساس مرحله فعلی درخواست، تاریخ سررسید آن را به‌روز می‌کند."""
    if request_obj.current_step and request_obj.current_step.deadline_days is not None:
        deadline_days = request_obj.current_step.deadline_days
        request_obj.due_date = timezone.now() + timedelta(days=deadline_days)
    else:
        request_obj.due_date = None
    request_obj.save(update_fields=['due_date'])

def send_notification_email(request, recipient, request_obj, action_user, action_type_display, comments):
    if not recipient.email:
        print(f"ارسال ایمیل به {recipient.username} انجام نشد چون ایمیلی برای او ثبت نشده است.")
        return
    subject = f"وظیفه جدید در سیستم اتوماسیون: درخواست #{request_obj.id}"
    request_url = request.build_absolute_uri(reverse('request_detail', args=[request_obj.id]))
    message = f"""
کاربر گرامی {recipient.get_full_name() or recipient.username}،

یک وظیفه جدید در کارتابل شما قرار گرفت.
"""
    # ... (بقیه متن ایمیل)
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient.email], fail_silently=False)
        print(f"ایمیل اطلاع رسانی با موفقیت به {recipient.email} ارسال شد.")
    except Exception as e:
        print(f"خطا در ارسال ایمیل به {recipient.email}: {e}")

def notify_user(request, recipient, request_obj, action_user, action_type_display, comments):
    """یک اعلان درون‌برنامه‌ای ایجاد کرده و ایمیل اطلاع‌رسانی را ارسال می‌کند."""
    if not recipient:
        return
    message = f"وظیفه جدید: درخواست #{request_obj.id} توسط {action_user.get_full_name()} برای شما ارسال شد."
    Notification.objects.create(user=recipient, request=request_obj, message=message)
    send_notification_email(request, recipient, request_obj, action_user, action_type_display, comments)



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'نام کاربری یا رمز عبور اشتباه است.'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    user = request.user
    active_processes = Process.objects.filter(is_active=True)

    received_requests_query = Request.objects.filter(current_assignee=user, status='IN_PROGRESS').select_related('process', 'initiator_user', 'current_step').order_by('-created_at')
    sent_requests_query = Request.objects.filter(initiator_user=user).select_related('process', 'current_assignee', 'current_step').order_by('-created_at')

    search_received_id = request.GET.get('search_received_id')
    if search_received_id and search_received_id.isdigit():
        received_requests_query = received_requests_query.filter(id=int(search_received_id))

    search_sent_id = request.GET.get('search_sent_id')
    search_sent_process = request.GET.get('search_sent_process')
    search_sent_status = request.GET.get('search_sent_status')
    
    if search_sent_id and search_sent_id.isdigit():
        sent_requests_query = sent_requests_query.filter(id=int(search_sent_id))
    if search_sent_process and search_sent_process.isdigit():
        sent_requests_query = sent_requests_query.filter(process_id=int(search_sent_process))
    if search_sent_status:
        sent_requests_query = sent_requests_query.filter(status=search_sent_status)
    
    context = {
        'active_processes': active_processes,
        'received_requests': received_requests_query,
        'sent_requests': sent_requests_query,
        'received_count': received_requests_query.count(),
        'in_progress_sent_count': sent_requests_query.filter(status='IN_PROGRESS').count(),
        'search_values': request.GET
    }
    return render(request, 'dashboard.html', context)

@login_required
def create_request_view(request, process_id):
    process = Process.objects.get(id=process_id)
    first_step = process.steps.order_by('step_order').first()

    if first_step:
        assignee = first_step.default_responsible_user or request.user.manager
        if assignee:
            new_request = Request.objects.create(
                process=process,
                initiator_user=request.user,
                current_step=first_step,
                current_assignee=assignee
            )
            update_request_due_date(new_request)
            notify_user(request, assignee, new_request, request.user, "ایجاد درخواست", "فرایند جدیدی برای شما ارسال شده است.")
            messages.success(request, f"فرایند '{process.name}' با موفقیت شروع شد.")
        else:
            messages.error(request, "ثبت درخواست ممکن نیست! مدیر مستقیم برای حساب کاربری شما تعریف نشده است. لطفاً با ادمین سیستم تماس بگیرید.")
    return redirect('dashboard')

@login_required
def request_detail_view(request, request_id):
    try:
        req = Request.objects.select_related(
            'process', 'initiator_user', 'current_step', 'current_assignee'
        ).get(id=request_id)
        
        if not (request.user == req.initiator_user or request.user == req.current_assignee):
            messages.error(request, "شما اجازه دسترسی به این درخواست را ندارید.")
            return redirect('dashboard')
    except Request.DoesNotExist:
        messages.error(request, "درخواستی با این شناسه یافت نشد.")
        return redirect('dashboard')

    returnable_steps = []
    if req.status == 'IN_PROGRESS' and req.current_step:
        returnable_steps = ProcessStep.objects.filter(
            process=req.process,
            step_order__lt=req.current_step.step_order
        ).order_by('step_order')

    process_graph_svg = generate_process_graph(req.process, req.current_step.id if req.current_step else None)

    if request.method == 'POST':
        comments = request.POST.get('comments', '').strip()
        action = request.POST.get('action')
        attachment_file = request.FILES.get('attachment')

        if action == 'return':
            if not comments:
                messages.error(request, "برای بازگرداندن درخواست، نوشتن توضیحات اجباری است.")
                return redirect('request_detail', request_id=req.id)
            
            return_target = request.POST.get('return_step_id')
            if not return_target:
                messages.error(request, "مقصد بازگشت انتخاب نشده است.")
                return redirect('request_detail', request_id=req.id)

            # ===== منطق جدید برای مدیریت هر دو نوع بازگشت =====
            notification_message = ""
            success_message = ""
            
            if return_target == 'initiator':
                return_step = req.process.steps.order_by('step_order').first()
                return_assignee = req.initiator_user
                notification_message = "بازگردانده شد به ثبت کننده"
                success_message = "درخواست با موفقیت به ثبت‌کننده بازگردانده شد."
            
            elif return_target.isdigit():
                try:
                    return_step = returnable_steps.get(id=int(return_target))
                    return_assignee = return_step.default_responsible_user or req.initiator_user.manager

                    if not return_assignee:
                        messages.error(request, f"کاربر مسئولی برای مرحله '{return_step.name}' یافت نشد.")
                        return redirect('request_detail', request_id=req.id)
                    
                    notification_message = f"بازگردانده شد به مرحله '{return_step.name}'"
                    success_message = f"درخواست با موفقیت به مرحله '{return_step.name}' بازگردانده شد."

                except ProcessStep.DoesNotExist:
                    messages.error(request, "مرحله انتخاب شده برای بازگشت معتبر نیست.")
                    return redirect('request_detail', request_id=req.id)
            else:
                messages.error(request, "مقصد بازگشت نامعتبر است.")
                return redirect('request_detail', request_id=req.id)

            # بخش مشترک برای هر دو نوع بازگشت
            RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='RETURNED', comments=comments, attachment=attachment_file)
            req.current_step = return_step
            req.current_assignee = return_assignee
            req.save()
            
            update_request_due_date(req)
            notify_user(request, return_assignee, req, request.user, notification_message, comments)
            messages.info(request, success_message)
            return redirect('dashboard')

        elif action == 'resubmit':
            forward_assignee = req.current_step.default_responsible_user or req.initiator_user.manager
            if forward_assignee:
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='RESUBMITTED', comments=comments, attachment=attachment_file)
                req.current_assignee = forward_assignee
                req.save()
                
                update_request_due_date(req)
                notify_user(request, forward_assignee, req, request.user, "ارسال مجدد", comments)
                messages.success(request, "درخواست شما مجدداً برای بررسی ارسال شد.")
                return redirect('dashboard')
            else:
                messages.error(request, "ارسال مجدد ممکن نیست! مدیر مستقیم برای حساب کاربری شما تعریف نشده است.")
        
        elif action == 'comment':
            if comments or attachment_file:
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='COMMENTED', comments=comments, attachment=attachment_file)
                messages.success(request, "نظر/فایل شما با موفقیت ثبت شد.")
            else:
                messages.warning(request, "لطفاً متن نظر خود را وارد کنید یا فایلی را پیوست نمایید.")
        
        elif request.user == req.current_assignee:
            if action == 'approve':
                next_step = ProcessStep.objects.filter(process=req.process, step_order__gt=req.current_step.step_order).order_by('step_order').first()
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='APPROVED', comments=comments, attachment=attachment_file)
                if next_step:
                    next_assignee = next_step.default_responsible_user or req.initiator_user.manager
                    if next_assignee:
                        req.current_step = next_step
                        req.current_assignee = next_assignee
                        req.save()
                        update_request_due_date(req)
                        notify_user(request, next_assignee, req, request.user, "تایید و ارسال به مرحله بعد", comments)
                        messages.success(request, f"درخواست #{req.id} با موفقیت به مرحله بعد ارسال شد.")
                    else:
                        messages.error(request, "ارسال ممکن نیست! مدیر مستقیم برای ثبت‌کننده تعریف نشده است.")
                        return redirect('request_detail', request_id=req.id)
                else: 
                    req.status = 'APPROVED'
                    req.current_assignee = None
                    req.current_step = None
                    req.due_date = None
                    req.save()
                    messages.success(request, f"فرایند برای درخواست #{req.id} با موفقیت تایید نهایی شد.")
                return redirect('dashboard')

            elif action == 'reject':
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='REJECTED', comments=comments, attachment=attachment_file)
                req.status = 'REJECTED'
                req.current_assignee = None
                req.current_step = None
                req.due_date = None
                req.save()
                messages.warning(request, f"درخواست #{req.id} توسط شما رد شد.")
                return redirect('dashboard')
        
        return redirect('request_detail', request_id=req.id)

    history = req.history.all().order_by('timestamp')
    context = {
        'req': req,
        'history': history,
        'process_graph_svg': process_graph_svg,
        'returnable_steps': returnable_steps,
    }
    return render(request, 'request_detail.html', context)


@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    data = {
        'count': notifications.count(),
        'notifications': [
            {'id': n.id, 'message': n.message, 'url': reverse('mark_notification_as_read', args=[n.id])}
            for n in notifications
        ]
    }
    return JsonResponse(data)

@login_required
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return redirect('request_detail', request_id=notification.request.id)
    except Notification.DoesNotExist:
        messages.error(request, "اعلان مورد نظر یافت نشد.")
        return redirect('dashboard')