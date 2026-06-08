from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from common.brand_access import resolve_post_login_url, user_is_dealer_only
from common.brand_scope import create_brand_for_user, set_active_brand, _brand_id_allowed_for_user
from common.login_throttle import clear_login_attempts, is_login_blocked, register_failed_login
from common.register_throttle import is_register_blocked, register_attempt
from common.tenant import allocate_host_slug, build_brand_public_url, tenant_login_url
from core_settings.billing.subscription import create_subscription_for_register
from core_settings.models import Plan

from .activation import send_activation_email, user_from_activation_token
from .forms import UserLoginForm, UserPasswordChangeForm, UserProfileForm
from .register_form import UserRegisterForm
from .utils import get_or_create_user_profile


class UserLoginView(AuthLoginView):
    template_name = 'users/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and is_login_blocked(request):
            messages.error(
                request,
                'Çok fazla başarısız giriş denemesi. Lütfen 15 dakika sonra tekrar deneyin.',
            )
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, 'tenant_brand', None)
        context['tenant_brand'] = tenant
        context['is_dealer_login'] = bool(tenant and tenant.panel_kind == 'dealer')
        context['is_tenant_login'] = bool(tenant)
        return context

    def get_success_url(self):
        redirect_to = self.request.POST.get('next') or self.request.GET.get('next')
        user = self.request.user

        if redirect_to:
            if url_has_allowed_host_and_scheme(
                redirect_to,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            ):
                return redirect_to

        return resolve_post_login_url(self.request, user)

    def form_invalid(self, form):
        register_failed_login(self.request)
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        tenant = getattr(self.request, 'tenant_brand', None)

        if tenant and not _brand_id_allowed_for_user(user, tenant.pk):
            register_failed_login(self.request)
            messages.error(self.request, 'Bu panele erişim yetkiniz yok.')
            return self.form_invalid(form)

        if not tenant and user_is_dealer_only(user):
            register_failed_login(self.request)
            brand = user.brand_memberships.filter(
                brand__panel_kind='dealer',
                brand__is_active=True,
            ).select_related('brand').first()
            login_url = build_brand_public_url(brand.brand, self.request).rstrip('/') + '/giris/' if brand else tenant_login_url(self.request)
            messages.error(
                self.request,
                'Bayi hesapları yalnızca kendi panel adresinden giriş yapabilir.',
            )
            return redirect(login_url)

        clear_login_attempts(self.request, form.cleaned_data.get('username', ''))
        messages.success(self.request, f'Hoş geldiniz, {user.display_name}.')
        return super().form_valid(form)


class UserLogoutView(AuthLogoutView):
    next_page = reverse_lazy('landing')

    def dispatch(self, request, *args, **kwargs):
        from users.impersonation import SESSION_IMPERSONATE_USER_ID, SESSION_IMPERSONATOR_KEY

        if request.method == 'POST':
            request.session.pop(SESSION_IMPERSONATE_USER_ID, None)
            request.session.pop(SESSION_IMPERSONATOR_KEY, None)
        response = super().dispatch(request, *args, **kwargs)
        if request.method == 'POST':
            messages.info(request, 'Oturum kapatıldı.')
        return response


class ProfileSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile_settings.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_or_create_user_profile(self.request.user)
        context['profile'] = profile
        context['profile_form'] = UserProfileForm(instance=profile, user=self.request.user)
        context['password_form'] = UserPasswordChangeForm(user=self.request.user)
        context['active_plan'] = self.request.user.active_plan
        return context

    def post(self, request, *args, **kwargs):
        profile = get_or_create_user_profile(request.user)
        action = request.POST.get('form_action', 'profile')

        if action == 'password':
            password_form = UserPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, 'Şifreniz güncellendi.')
            else:
                messages.error(request, 'Şifre güncellenemedi. Lütfen alanları kontrol edin.')
            return redirect('profile_settings')

        profile_form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user,
        )
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profil bilgileriniz kaydedildi.')
        else:
            messages.error(request, 'Profil güncellenemedi. Lütfen alanları kontrol edin.')
        return redirect('profile_settings')


class UserRegisterView(View):
    def _registration_blocked(self, request):
        tenant = getattr(request, 'tenant_brand', None)
        if tenant:
            messages.info(
                request,
                'Üyelik yalnızca ana platform adresinden açılabilir. Bayi panelleri için yöneticiniz hesap oluşturur.',
            )
            return True
        return False

    def _resolve_plan(self, plan_id):
        if not plan_id:
            return Plan.objects.filter(is_active=True, price=0).order_by('price').first()
        return Plan.objects.filter(pk=plan_id, is_active=True).first()

    def _register_context(self, form, selected_plan=None):
        return {
            'form': form,
            'selected_plan': selected_plan,
            'plans': Plan.objects.filter(is_active=True).order_by('price'),
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        if self._registration_blocked(request):
            return redirect('login')
        plan_id = request.GET.get('plan')
        selected_plan = self._resolve_plan(plan_id) if plan_id else self._resolve_plan(None)
        if plan_id and not Plan.objects.filter(pk=plan_id, is_active=True).exists():
            messages.warning(request, 'Seçilen plan bulunamadı; ücretsiz paketle devam edebilirsiniz.')
            selected_plan = self._resolve_plan(None)
        form = UserRegisterForm()
        return render(request, 'users/register.html', self._register_context(form, selected_plan))

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        if self._registration_blocked(request):
            return redirect('login')
        if is_register_blocked(request):
            messages.error(
                request,
                'Çok fazla kayıt denemesi. Lütfen bir saat sonra tekrar deneyin.',
            )
            return redirect('register')
        register_attempt(request)
        form = UserRegisterForm(request.POST)
        plan_id = request.POST.get('plan_id') or request.POST.get('plan_pick')
        selected_plan = self._resolve_plan(plan_id) or self._resolve_plan(None)

        if form.is_valid() and not selected_plan:
            form.add_error(None, 'Kayıt için aktif bir ücretsiz plan bulunamadı. Lütfen yönetici ile iletişime geçin.')

        if form.is_valid():
            from users.models import Role

            user = form.save(commit=False)
            user.is_active = False
            admin_role = Role.objects.filter(slug='admin').first()
            if admin_role:
                user.role = admin_role
            if selected_plan and selected_plan.price == 0:
                user.plan = selected_plan
            user.save()

            if selected_plan:
                create_subscription_for_register(user, selected_plan)

            get_or_create_user_profile(user)
            host_slug = allocate_host_slug(form.cleaned_data['brand_name'])
            brand = create_brand_for_user(
                user,
                form.cleaned_data['brand_name'],
                host_slug=host_slug,
            )

            try:
                send_activation_email(request, user)
            except Exception:
                messages.warning(
                    request,
                    'Hesap oluşturuldu ancak aktivasyon e-postası gönderilemedi. '
                    'Lütfen destek ile iletişime geçin.',
                )
                return redirect('login')

            messages.success(
                request,
                f'"{brand.name}" markanız oluşturuldu. '
                f'E-posta adresinize ({user.email}) aktivasyon bağlantısı gönderildi.',
            )
            return redirect('login')

        return render(request, 'users/register.html', self._register_context(form, selected_plan))


class ActivateAccountView(View):
    def get(self, request, token):
        user = user_from_activation_token(token)
        if not user:
            messages.error(request, 'Aktivasyon bağlantısı geçersiz veya süresi dolmuş.')
            return redirect('login')

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        from core_settings.billing.subscription import get_active_subscription, refresh_subscription_status
        from core_settings.models import Subscription

        refresh_subscription_status(user)
        sub = get_active_subscription(user)
        login(request, user)

        if user.brand_memberships.exists():
            default_mem = user.brand_memberships.filter(is_default=True).first()
            if not default_mem:
                default_mem = user.brand_memberships.order_by('joined_at').first()
            if default_mem:
                set_active_brand(request, default_mem.brand_id)

        if sub and sub.plan.price > 0 and sub.status in (
            Subscription.STATUS_TRIALING,
            Subscription.STATUS_PAST_DUE,
        ):
            messages.success(
                request,
                'Hesabınız aktifleştirildi. Ücretli plan için ödeme adımını tamamlayın.',
            )
            return redirect('subscription_checkout')

        messages.success(request, 'Hesabınız aktifleştirildi. Hoş geldiniz!')
        return redirect('home')

