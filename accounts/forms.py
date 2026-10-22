from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class ModernClearableFileInput(forms.ClearableFileInput):
    template_name = 'accounts/custom_clearable_file_input.html'

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
            'nik', 
            'nama_ktp',
            'background_image', 
            'profile_picture', 
            'profile_picture_2', 
            'profile_picture_3',
            'bio', 
            'gender', 
            'birth_date', 
            'concert_vibe', 
            'social_energy', 
            'matching_goal'
        ]
        labels = {
            'nik': 'NIK KTP',
            'nama_ktp': 'Nama Sesuai KTP',
            'background_image': 'Foto Background',
            'profile_picture': 'Foto Profil Utama',
            'profile_picture_2': 'Foto Profil 2',
            'profile_picture_3': 'Foto Profil 3',
            'bio': 'Tentang Saya',
            'gender': 'Jenis Kelamin',
            'birth_date': 'Tanggal Lahir',
            'concert_vibe': 'Gaya Nonton Konser',
            'social_energy': 'Energi Sosial',
            'matching_goal': 'Tujuan Cari Teman',
        }
        widgets = {
            'nik': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '16', 'placeholder': 'Masukkan 16 digit NIK'}),
            'nama_ktp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap sesuai KTP'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ceritakan sedikit tentang dirimu.'}),
            
            # Format ISO dipaksa di sini agar browser mau menampilkan tanggal dari database
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            
            'concert_vibe': forms.Select(attrs={'class': 'form-select'}),
            'social_energy': forms.Select(attrs={'class': 'form-select'}),
            'matching_goal': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            
            'background_image': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture_2': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture_3': ModernClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['nik'].required = True
        self.fields['nama_ktp'].required = True
        
        if not self.instance or not self.instance.profile_picture:
            self.fields['profile_picture'].required = True
        else:
            self.fields['profile_picture'].required = False

        dropdown_fields = ['gender', 'concert_vibe', 'social_energy', 'matching_goal']
        for field_name in dropdown_fields:
            if field_name in self.fields:
                existing_choices = [c for c in self.fields[field_name].choices if c[0] != '']
                self.fields[field_name].choices = [('', '-- Pilih salah satu --')] + existing_choices