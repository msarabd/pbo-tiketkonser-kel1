from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'no_hp')
        labels = {
            'username': 'Nama Pengguna',
            'no_hp': 'Nomor WhatsApp / HP',
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 
            'bio', 
            'gender', 
            'birth_date', 
            'concert_vibe', 
            'social_energy', 
            'matching_goal'
        ]
        labels = {
            'profile_picture': 'Foto Profil',
            'bio': 'Tentang Saya',
            'gender': 'Jenis Kelamin',
            'birth_date': 'Tanggal Lahir',
            'concert_vibe': 'Gaya Nonton Konser',
            'social_energy': 'Energi Sosial',
            'matching_goal': 'Tujuan Cari Teman',
        }
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Ceritakan musisi favorit atau kebiasaan konsermu...'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'concert_vibe': forms.Select(attrs={'class': 'form-select'}),
            'social_energy': forms.Select(attrs={'class': 'form-select'}),
            'matching_goal': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Menimpa pilihan kosong default (- Select an option -) menjadi bahasa Indonesia
        dropdown_fields = ['gender', 'concert_vibe', 'social_energy', 'matching_goal']
        for field_name in dropdown_fields:
            if field_name in self.fields:
                existing_choices = [c for c in self.fields[field_name].choices if c[0] != '']
                self.fields[field_name].choices = [('', '-- Pilih salah satu --')] + existing_choices