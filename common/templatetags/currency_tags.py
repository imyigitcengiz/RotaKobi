from django import template

from common.currency import format_money

register = template.Library()


@register.filter
def money(value, arg=None):
    """
    Tutarı site para birimine göre biçimlendirir.
    Kullanım: {{ amount|money }}  veya  {{ amount|money:0 }} (ondalıksız)
    """
    decimals = 2
    if arg is not None and str(arg).strip().isdigit():
        decimals = int(str(arg).strip())
    return format_money(value, decimals=decimals)
