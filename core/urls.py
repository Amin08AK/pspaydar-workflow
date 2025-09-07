# core/urls.py

from django.urls import path
from . import views
# این خط فراموش شده بود و باید اضافه شود
from django.contrib.auth import views as auth_views

urlpatterns = [
    # URL های قبلی شما...
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('create-request/<int:process_id>/', views.create_request_view, name='create_request'),


    # --- URL های جدید برای فراموشی و تغییر رمز عبور ---
    
    # 1. صفحه درخواست بازنشانی رمز (کاربر ایمیلش را وارد می‌کند)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html', email_template_name='registration/password_reset_email.html'), 
         name='password_reset'),

    # 2. صفحه تایید (پیامی که می‌گوید ایمیل ارسال شد)
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), 
         name='password_reset_done'),

    # 3. لینک داخل ایمیل (که حاوی توکن است) و فرم تغییر رمز جدید
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), 
         name='password_reset_confirm'),

    # 4. صفحه تایید نهایی (پیامی که می‌گوید رمز با موفقیت تغییر کرد)
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),

    # --- URL های جدید برای تغییر رمز عبور کاربر لاگین شده ---
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), 
         name='password_change'),

    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), 
         name='password_change_done'),
    path('request/<int:request_id>/', views.request_detail_view, name='request_detail'),

    path('notifications/get/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-as-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
]