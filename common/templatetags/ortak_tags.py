from django import template

from common.permissions import can_manage_payroll, can_manage_teams, can_manage_personnel

register = template.Library()


@register.simple_tag(takes_context=True)
def user_can_manage_payroll(context):
    return can_manage_payroll(context['request'].user)


@register.simple_tag(takes_context=True)
def user_can_manage_teams(context):
    return can_manage_teams(context['request'].user)


@register.simple_tag(takes_context=True)
def user_can_manage_personnel(context):
    return can_manage_personnel(context['request'].user)


@register.filter
def dict_get(mapping, key):
    if not mapping or key is None:
        return None
    return mapping.get(key)
