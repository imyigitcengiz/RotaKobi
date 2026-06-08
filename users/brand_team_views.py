from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import RedirectView, ListView, CreateView, UpdateView, DeleteView

from common.brand_team import (
    assignable_roles_queryset,
    attach_user_to_brand,
    brand_assignable_permissions_queryset,
    PlanLimitExceeded,
    check_team_user_limit,
    owned_brand_ids,
    owned_brands_queryset,
    sanitize_brand_permission_ids,
    team_users_queryset,
)
from core_settings.models import BrandMembership, BusinessBrand
from users.admin_forms import RoleForm
from users.admin_views import RoleFormMixin
from users.admin_services import user_delete_context_basic
from users.brand_team_forms import BrandTeamUserCreateForm, BrandTeamUserUpdateForm
from users.impersonation import get_real_user
from users.mixins import BrandTeamManagerMixin
from users.models import Role

User = get_user_model()


def _manager(request):
    return get_real_user(request)


def _brand_filter_id(request) -> int | None:
    raw = request.GET.get('marka', '').strip()
    if raw.isdigit():
        brand_id = int(raw)
        if brand_id in owned_brand_ids(_manager(request)):
            return brand_id
    return None


class BrandTeamHomeView(BrandTeamManagerMixin, RedirectView):
    pattern_name = 'brand_team_users'
    permanent = False


class BrandTeamUserListView(BrandTeamManagerMixin, ListView):
    model = User
    template_name = 'users/brand_team/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        return team_users_queryset(_manager(self.request), brand_id=_brand_filter_id(self.request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = _manager(self.request)
        context['owned_brands'] = owned_brands_queryset(manager)
        context['active_brand_filter'] = _brand_filter_id(self.request)
        return context


class BrandTeamUserCreateView(BrandTeamManagerMixin, CreateView):
    model = User
    form_class = BrandTeamUserCreateForm
    template_name = 'users/brand_team/user_form.html'
    success_url = reverse_lazy('brand_team_users')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['manager'] = _manager(self.request)
        return kwargs

    def form_valid(self, form):
        manager = _manager(self.request)
        brand = form.cleaned_data['brand']
        try:
            check_team_user_limit(manager, brand)
        except PlanLimitExceeded as exc:
            form.add_error('brand', exc.message)
            return self.form_invalid(form)

        user = form.save()
        attach_user_to_brand(
            user,
            brand,
            membership_role=form.cleaned_data['membership_role'],
            is_default=form.cleaned_data.get('is_default_brand', True),
        )
        from users.utils import get_or_create_user_profile

        get_or_create_user_profile(user)
        messages.success(self.request, 'Ekip üyesi oluşturuldu.')
        return redirect(self.success_url)


class BrandTeamUserUpdateView(BrandTeamManagerMixin, UpdateView):
    model = User
    form_class = BrandTeamUserUpdateForm
    template_name = 'users/brand_team/user_form.html'
    success_url = reverse_lazy('brand_team_users')

    def get_queryset(self):
        return team_users_queryset(_manager(self.request))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['manager'] = _manager(self.request)
        kwargs['editor'] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        manager = _manager(self.request)
        selected_brands = set(form.cleaned_data['brands'].values_list('pk', flat=True))
        allowed_ids = set(owned_brand_ids(manager))

        for brand_id in selected_brands:
            if brand_id not in allowed_ids:
                continue
            brand = BusinessBrand.objects.get(pk=brand_id)
            existing = BrandMembership.objects.filter(user=user, brand_id=brand_id).first()
            if not existing:
                try:
                    check_team_user_limit(manager, brand)
                except PlanLimitExceeded as exc:
                    messages.error(self.request, exc.message)
                    return redirect('brand_team_user_edit', pk=user.pk)
            attach_user_to_brand(
                user,
                brand,
                membership_role=existing.role if existing else BrandMembership.ROLE_MEMBER,
                is_default=existing.is_default if existing else False,
            )

        BrandMembership.objects.filter(
            user=user,
            brand_id__in=allowed_ids,
        ).exclude(brand_id__in=selected_brands).delete()

        messages.success(self.request, 'Kullanıcı güncellendi.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context.update(_brand_team_delete_context(_manager(self.request), self.object))
        return context


def _brand_team_delete_context(manager, target):
    ctx = user_delete_context_basic(manager, target)
    if BrandMembership.objects.filter(
        user=target,
        role=BrandMembership.ROLE_OWNER,
        brand_id__in=owned_brand_ids(manager),
    ).exists():
        ctx['user_can_delete'] = False
        ctx['user_delete_blocked_reason'] = 'Abonelik / marka sahipleri silinemez.'
    return ctx


class BrandTeamUserDeleteView(BrandTeamManagerMixin, DeleteView):
    model = User
    template_name = 'users/brand_team/user_confirm_delete.html'
    success_url = reverse_lazy('brand_team_users')

    def get_queryset(self):
        return team_users_queryset(_manager(self.request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_brand_team_delete_context(_manager(self.request), self.object))
        return context

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        ctx = _brand_team_delete_context(_manager(request), user)
        if not ctx['user_can_delete']:
            messages.error(request, ctx['user_delete_blocked_reason'])
            return redirect('brand_team_users')
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        ctx = _brand_team_delete_context(_manager(request), user)
        if not ctx['user_can_delete']:
            messages.error(request, ctx['user_delete_blocked_reason'])
            return redirect('brand_team_users')
        allowed_ids = owned_brand_ids(_manager(request))
        BrandMembership.objects.filter(user=user, brand_id__in=allowed_ids).delete()
        if not BrandMembership.objects.filter(user=user).exists():
            label = user.display_name
            user.delete()
            messages.info(request, f'"{label}" kullanıcısı silindi.')
        else:
            messages.info(request, f'"{user.display_name}" kullanıcısı panellerinizden çıkarıldı.')
        return redirect(self.success_url)


class BrandTeamRoleFormMixin(RoleFormMixin):
    def _permission_ids_from_post(self):
        return sanitize_brand_permission_ids(super()._permission_ids_from_post())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allowed_ids = set(brand_assignable_permissions_queryset().values_list('pk', flat=True))
        context['access_permissions'] = [
            p for p in context['access_permissions'] if p.pk in allowed_ids
        ]
        context['action_permissions_by_module'] = {
            module: [p for p in perms if p.pk in allowed_ids]
            for module, perms in context['action_permissions_by_module'].items()
            if any(p.pk in allowed_ids for p in perms)
        }
        return context


class BrandTeamRoleListView(BrandTeamManagerMixin, ListView):
    model = Role
    template_name = 'users/brand_team/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        from django.db.models import Count

        manager = _manager(self.request)
        return (
            assignable_roles_queryset(manager)
            .annotate(user_count=Count('users'))
            .order_by('name')
        )


class BrandTeamRoleCreateView(BrandTeamManagerMixin, BrandTeamRoleFormMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = 'users/brand_team/role_form.html'
    success_url = reverse_lazy('brand_team_roles')

    def form_valid(self, form):
        form.instance.is_system = False
        form.instance.owner = _manager(self.request)
        messages.success(self.request, 'Rol oluşturuldu.')
        return super().form_valid(form)


class BrandTeamRoleUpdateView(BrandTeamManagerMixin, BrandTeamRoleFormMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'users/brand_team/role_form.html'
    success_url = reverse_lazy('brand_team_roles')

    def get_queryset(self):
        manager = _manager(self.request)
        return assignable_roles_queryset(manager)

    def form_valid(self, form):
        if self.object.is_system:
            form.instance.slug = self.object.slug
            form.instance.name = self.object.name
            messages.info(self.request, 'Sistem rolleri düzenlenemez.')
            return redirect(self.success_url)
        messages.success(self.request, 'Rol güncellendi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_is_readonly'] = self.object.is_system
        return context


class BrandTeamRoleDeleteView(BrandTeamManagerMixin, DeleteView):
    model = Role
    template_name = 'users/brand_team/role_confirm_delete.html'
    success_url = reverse_lazy('brand_team_roles')

    def get_queryset(self):
        manager = _manager(self.request)
        return Role.objects.filter(is_system=False, owner=manager)

    def delete(self, request, *args, **kwargs):
        role = self.get_object()
        if role.users.exists():
            messages.error(request, 'Bu role atanmış kullanıcılar var; silinemez.')
            return redirect('brand_team_roles')
        messages.info(request, f'"{role.name}" rolü silindi.')
        return super().delete(request, *args, **kwargs)
