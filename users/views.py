from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from .forms import UserLoginForm, UserPasswordChangeForm, UserProfileForm
from .utils import get_or_create_user_profile


class UserLoginView(AuthLoginView):
    template_name = 'users/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.request.POST.get('next') or self.request.GET.get('next')
        if redirect_to:
            return redirect_to
        user = self.request.user
        if user.is_superuser:
            return reverse('admin_dashboard')
        return reverse('home')
    def form_valid(self, form):
        messages.success(self.request, f'Hoş geldiniz, {form.get_user().display_name}.')
        return super().form_valid(form)


class UserLogoutView(AuthLogoutView):
    next_page = reverse_lazy('landing')
    def dispatch(self, request, *args, **kwargs):
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
