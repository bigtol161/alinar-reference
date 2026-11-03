import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Category, District, Master, Review, ServiceRequest
from .utils import digits_only

PHONE_RE = re.compile(r'^\d{11}$')


def validate_phone(value):
    digits = digits_only(value)
    if not PHONE_RE.match(digits):
        raise ValidationError('Введите телефон в формате +7 (XXX) XXX-XX-XX')
    if digits[0] not in '78':
        raise ValidationError('Телефон должен начинаться с +7')
    return value


class PhoneFieldMixin:
    def clean_phone(self):
        return validate_phone(self.cleaned_data['phone'])


class RequestForm(PhoneFieldMixin, forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['category', 'service', 'name', 'phone', 'district', 'desired_date', 'budget', 'comment']
        widgets = {
            'desired_date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = 'Выберите категорию'
        self.fields['category'].required = True
        self.fields['district'].empty_label = 'Не важно'
        self.fields['budget'].min_value = 0
        self.fields['service'].widget.attrs['placeholder'] = 'Например: замена смесителя'
        for name in ('name', 'service'):
            self.fields[name].widget.attrs['class'] = 'input'


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'author', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].required = False
        self.fields['author'].widget.attrs['placeholder'] = 'Ваше имя'
        self.fields['text'].widget.attrs['placeholder'] = 'Расскажите о работе мастера'


class MasterForm(forms.ModelForm):
    class Meta:
        model = Master
        fields = ['name', 'category', 'title', 'experience', 'price_from', 'phone', 'about', 'verified', 'districts']
        widgets = {
            'districts': forms.CheckboxSelectMultiple,
            'about': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'title': 'Специализация',
            'experience': 'Опыт работы, лет',
            'price_from': 'Цена от, ₽',
            'verified': 'Готов подтвердить документы (паспорт, документы об образовании)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = 'Выберите категорию'
        self.fields['title'].widget.attrs['placeholder'] = 'Например: сантехник, репетитор, фотограф'
        self.fields['about'].widget.attrs['placeholder'] = 'Расскажите о опыте, гарантии и особенностях работы'
        for name in ('name', 'title', 'phone'):
            self.fields[name].widget.attrs['class'] = 'input'


class SignUpForm(forms.Form):
    name = forms.CharField(label='Имя и фамилия', max_length=120)
    phone = forms.CharField(label='Телефон', max_length=32)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)

    def clean_phone(self):
        digits = digits_only(self.cleaned_data['phone'])
        validate_phone(self.cleaned_data['phone'])
        return digits

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p1 != p2:
            raise ValidationError('Пароли не совпадают')
        if p1 and len(p1) < 6:
            raise ValidationError('Пароль должен быть не короче 6 символов')
        return cleaned


class SignInForm(forms.Form):
    phone = forms.CharField(label='Телефон', max_length=32)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def clean_phone(self):
        return digits_only(self.cleaned_data['phone'])
