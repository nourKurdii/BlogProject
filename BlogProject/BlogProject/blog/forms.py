from django import forms
from django.core.exceptions import ValidationError

from .models import Comment, Post
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class commentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(commentForm, self).__init__(*args, **kwargs)
        if user.is_authenticated:
            self.fields['email'].required = False
            self.fields['name'].required = False
            self.fields['email'].widget = forms.HiddenInput()
            self.fields['name'].widget = forms.HiddenInput()

    class Meta:
        model = Comment
        fields = ['email', 'name', 'body']


class registerForm(UserCreationForm):
    username = forms.CharField(min_length=5, max_length=200)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def username_clean(self):
        username = self.cleaned_data['username']
        new = User.objects.filter(username=username)
        if new.count():
            raise ValidationError('User Already Exist')
        return username

    def email_clean(self):
        email = self.cleaned_data['email']
        new = User.objects.filter(email=email)
        if new.count():
            raise ValidationError('Email Already Exist')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match ")
        return password2

    def save(self, commit=True):
        user = User.objects.create_user(
            self.cleaned_data['username'],
            self.cleaned_data['email'],
            self.cleaned_data['password1']
        )
        return user


class postEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'body', 'status']


class createPostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'body', 'status']


class generatePost(forms.Form):
    subject = forms.CharField(max_length=100)
