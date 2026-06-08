from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

INPUT = (
    'w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm '
    'focus:ring-2 focus:ring-brand-500 outline-none'
)


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='Ad',
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'Adınız',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Soyad',
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'Soyadınız',
            'autocomplete': 'family-name',
        }),
    )
    email = forms.EmailField(
        required=True,
        label='E-posta',
        widget=forms.EmailInput(attrs={
            'class': INPUT,
            'placeholder': 'ornek@sirket.com',
            'autocomplete': 'email',
        }),
    )
    brand_name = forms.CharField(
        max_length=255,
        required=True,
        label='Marka / firma adı',
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'Örn. Cool Servis Ltd.',
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': INPUT,
            'placeholder': 'Kullanıcı adı',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': INPUT,
            'placeholder': 'En az 8 karakter',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': INPUT,
            'placeholder': 'Şifreyi tekrar girin',
            'autocomplete': 'new-password',
        })
        self.fields['password1'].label = 'Şifre'
        self.fields['password2'].label = 'Şifre (tekrar)'
