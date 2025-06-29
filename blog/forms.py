from django import forms
# from .models import Contact
from .models import Profile
from django.contrib.auth.models import User
# class ContactForm(forms.ModelForm):
#     class Meta:
#         model = Contact
#         fields = ['name', 'email', 'subject', 'message']
#         widgets = {
#             'message': forms.Textarea(attrs={'rows': 5}),
#         }
        
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()
    
    
class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_pic', 'bio', 'phone']