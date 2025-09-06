# core/views.py

import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import User, Process, ProcessStep, Request, RequestHistory
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login, logout, authenticate # authenticate را اضافه کنید
from django.contrib import messages
from .utils import generate_process_graph # ابزار جدید برای رسم گراف



def send_otp_email(email, otp):
    """این تابع ایمیل واقعی ارسال می‌کند"""
    subject = 'کد تایید ورود به سیستم اتوماسیون'
    message = f'کد تایید شما: {otp}'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email, ]
    send_mail(subject, message, email_from, recipient_list)
    print(f"یک ایمیل واقعی حاوی کد {otp} به {email} ارسال شد.") # این خط برای راحتی در کنسول هم نمایش میدهد

# core/views.py

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            # ارسال پیام خطا به قالب
            return render(request, 'login.html', {'error': 'نام کاربری یا رمز عبور اشتباه است.'})

    return render(request, 'login.html')
def verify_otp_view(request):
    email = request.session.get('otp_email')
    if not email:
        return redirect('login')

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        otp_session = str(request.session.get('otp'))

        if otp_entered == otp_session:
            user = User.objects.get(email=email)
            login(request, user)
            del request.session['otp']
            del request.session['otp_email']
            return redirect('dashboard')
        else:
            return render(request, 'verify_otp.html', {'email': email, 'error': 'کد وارد شده صحیح نیست.'})
            
    return render(request, 'verify_otp.html', {'email': email})

def logout_view(request):
    logout(request)
    return redirect('login')

# core/views.py

@login_required
def dashboard_view(request):
    user = request.user
    
    # 1. فرایندهایی که کاربر می‌تواند شروع کند
    active_processes = Process.objects.filter(is_active=True)
    
    # 2. درخواست‌های دریافت شده (کارتابل)
    received_requests = Request.objects.filter(
        current_assignee=user, 
        status='IN_PROGRESS'
    ).order_by('-created_at')

    # 3. درخواست‌های ارسال شده توسط خود کاربر
    sent_requests = Request.objects.filter(initiator_user=user).order_by('-created_at')

    # --- داده‌های جدید برای کارت‌های آمار ---
    received_count = received_requests.count()
    in_progress_sent_count = sent_requests.filter(status='IN_PROGRESS').count()
    
    context = {
        'active_processes': active_processes,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'received_count': received_count,
        'in_progress_sent_count': in_progress_sent_count,
    }
    return render(request, 'dashboard.html', context)
@login_required
def create_request_view(request, process_id):
    process = Process.objects.get(id=process_id)
    first_step = process.steps.order_by('step_order').first()

    if first_step:
        assignee = None
        if first_step.default_responsible_user:
            assignee = first_step.default_responsible_user
        else:
            assignee = request.user.manager

        if assignee:
            Request.objects.create(
                process=process,
                initiator_user=request.user,
                current_step=first_step,
                current_assignee=assignee
            )
            messages.success(request, f"فرایند '{process.name}' با موفقیت شروع شد.")
        # --- این بخش جدید و کلیدی است ---
        else:
            messages.error(request, "ثبت درخواست ممکن نیست! مدیر مستقیم برای حساب کاربری شما تعریف نشده است. لطفاً با ادمین سیستم تماس بگیرید.")
        # -----------------------------------
    
    return redirect('dashboard')


# core/views.py

@login_required
def request_detail_view(request, request_id):
    try:
        req = Request.objects.get(id=request_id)
        if not (request.user == req.initiator_user or request.user == req.current_assignee):
            messages.error(request, "شما اجازه دسترسی به این درخواست را ندارید.")
            return redirect('dashboard')
    except Request.DoesNotExist:
        messages.error(request, "درخواستی با این شناسه یافت نشد.")
        return redirect('dashboard')

    # --- بخش جدید: تولید گراف فرایند برای نمایش به کاربر ---
    process_graph_svg = None
    # اگر فرایند هنوز تمام نشده و مرحله فعلی دارد، آن را هایلایت کن
    if req.current_step:
        process_graph_svg = generate_process_graph(req.process, req.current_step.id)

    if request.method == 'POST':
        comments = request.POST.get('comments', '').strip()
        action = request.POST.get('action')

        # --- سناریوی ۱: بازگرداندن درخواست (Return) ---
        if action == 'return':
            if not comments:
                messages.error(request, "برای بازگرداندن درخواست، نوشتن توضیحات اجباری است.")
                return redirect('request_detail', request_id=req.id)
            
            # پیدا کردن مرحله قبلی
            current_step_order = req.current_step.step_order
            previous_step = ProcessStep.objects.filter(process=req.process, step_order__lt=current_step_order).order_by('-step_order').first()

            return_assignee = None
            return_step = None

            # اگر مرحله قبلی وجود داشت
            if previous_step:
                previous_approver = RequestHistory.objects.filter(request=req, step=previous_step, action_type='APPROVED').order_by('-timestamp').first()
                return_assignee = previous_approver.action_user if previous_approver else None
                return_step = previous_step
            # اگر این اولین مرحله بود، به ثبت‌کننده اصلی برگردان
            else:
                return_assignee = req.initiator_user
                return_step = req.current_step # مرحله تغییر نمی‌کند

            if return_assignee:
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='RETURNED', comments=comments)
                req.current_step = return_step
                req.current_assignee = return_assignee
                req.save()
                messages.info(request, "درخواست با موفقیت بازگردانده شد.")
            else:
                messages.error(request, "خطا در یافتن مسئول قبلی. امکان بازگرداندن وجود ندارد.")
            
            return redirect('request_detail', request_id=req.id)

        # --- سناریوی ۲: ارسال مجدد توسط ثبت‌کننده (Resubmit) ---
        elif action == 'resubmit':
            # پیدا کردن مسئول بعدی برای مرحله فعلی
            forward_assignee = req.current_step.default_responsible_user or req.initiator_user.manager
            
            if forward_assignee:
                # اگر کاربر توضیحات جدیدی اضافه کرده بود، آن را ثبت می‌کنیم
                if comments:
                     RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='COMMENTED', comments=comments)
                
                # رویداد ارسال مجدد را ثبت می‌کنیم
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='RESUBMITTED', comments="درخواست مجدداً جهت بررسی ارسال شد.")
                
                req.current_assignee = forward_assignee
                req.save()
                messages.success(request, "درخواست شما مجدداً برای بررسی ارسال شد.")
                return redirect('dashboard')
            else:
                messages.error(request, "ارسال مجدد ممکن نیست! مدیر مستقیم برای حساب کاربری شما تعریف نشده است.")
                return redirect('request_detail', request_id=req.id)
        
        # --- بقیه سناریوها (نظر، تایید، رد) ---
        # این بخش‌ها تقریباً بدون تغییر باقی می‌مانند
        
        elif action == 'comment':
            if comments:
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='COMMENTED', comments=comments)
                messages.success(request, "نظر شما با موفقیت ثبت شد.")
            else:
                messages.warning(request, "لطفاً متن نظر خود را وارد کنید.")
            return redirect('request_detail', request_id=req.id)
        
        if request.user == req.current_assignee:
            if action == 'approve':
                current_step_order = req.current_step.step_order
                next_step = ProcessStep.objects.filter(process=req.process, step_order__gt=current_step_order).order_by('step_order').first()
                if next_step:
                    next_assignee = next_step.default_responsible_user or req.initiator_user.manager
                    if next_assignee:
                        RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='APPROVED', comments=comments)
                        req.current_step = next_step
                        req.current_assignee = next_assignee
                        req.save()
                        messages.success(request, f"درخواست #{req.id} با موفقیت به مرحله بعد ارسال شد.")
                    else:
                        messages.error(request, "ارسال ممکن نیست! مدیر مستقیم برای ثبت‌کننده تعریف نشده است.")
                        return redirect('request_detail', request_id=req.id)
                else:
                    RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='APPROVED', comments=comments)
                    req.status = 'APPROVED'
                    req.current_assignee = None
                    req.save()
                    messages.success(request, f"فرایند برای درخواست #{req.id} با موفقیت تایید نهایی شد.")
                return redirect('dashboard')

            elif action == 'reject':
                RequestHistory.objects.create(request=req, step=req.current_step, action_user=request.user, action_type='REJECTED', comments=comments)
                req.status = 'REJECTED'
                req.current_assignee = None
                req.save()
                messages.warning(request, f"درخواست #{req.id} توسط شما رد شد.")
                return redirect('dashboard')

    history = req.history.all().order_by('timestamp')
    context = {
        'req': req,
        'history': history,
        'process_graph_svg': process_graph_svg, # گراف را به کانتکست اضافه می‌کنیم
    }
    return render(request, 'request_detail.html', context)