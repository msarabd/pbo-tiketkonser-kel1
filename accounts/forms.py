from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

# ================= FORM MULTILOGIN =================
class MultiLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username atau Nomor WhatsApp',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True, 'placeholder': 'Masukkan username atau nomor WA'})
    )

# ================= FORM LUPA PASSWORD =================
class ForgotPasswordForm(forms.Form):
    no_hp = forms.CharField(
        label='Nomor WhatsApp terdaftar',
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: 081234567890'})
    )

class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        label='Password Baru',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'minlength': '8', 'maxlength': '15'})
    )
    confirm_password = forms.CharField(
        label='Konfirmasi Password Baru',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'minlength': '8', 'maxlength': '15'})
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Password tidak cocok.")
        return cleaned_data
    
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "Maks. 20 karakter. Hanya huruf, angka, dan @/./+/-/_."
        self.fields['username'].max_length = 20
        self.fields['username'].widget.attrs['maxlength'] = '20'
        
        self.fields['no_hp'].required = True
        self.fields['no_hp'].widget.attrs.update({'placeholder': 'Contoh: 081234567890'})
        
        if 'password1' in self.fields:
            self.fields['password1'].help_text = "Wajib 8 hingga 15 karakter."
            self.fields['password1'].widget.attrs.update({'minlength': '8', 'maxlength': '15'})
            
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'minlength': '8', 'maxlength': '15'})

    def clean_no_hp(self):
        no_hp = self.cleaned_data.get('no_hp')
        if not no_hp.isdigit():
            raise forms.ValidationError("Nomor WhatsApp hanya boleh berisi angka.")
        if len(no_hp) < 10:
            raise forms.ValidationError("Nomor WhatsApp terlalu pendek (minimal 10 digit).")
        return no_hp

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            if len(password) < 8:
                raise forms.ValidationError("Sandi terlalu pendek (minimal 8 karakter).")
            if len(password) > 15:
                raise forms.ValidationError("Sandi terlalu panjang (maksimal 15 karakter).")
        return password
    
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['no_hp']
        labels = {
            'no_hp': 'Nomor WhatsApp / HP',
        }
        widgets = {
            'no_hp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: 081234567890'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['no_hp'].required = True

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'nik', 'nama_ktp', 'foto_ktp', 'background_image', 'profile_picture', 
            'profile_picture_2', 'profile_picture_3', 'bio', 'gender', 'birth_date', 
            'concert_vibe', 'social_energy', 'matching_goal', 'latitude', 'longitude'
        ]
        labels = {
            'nik': 'NIK KTP', 'nama_ktp': 'Nama Sesuai KTP', 'foto_ktp': 'Foto KTP',
            'background_image': 'Foto Background', 'profile_picture': 'Foto Profil Utama',
            'profile_picture_2': 'Foto Profil 2', 'profile_picture_3': 'Foto Profil 3',
            'bio': 'Tentang Saya', 'gender': 'Jenis Kelamin', 'birth_date': 'Tanggal Lahir',
            'concert_vibe': 'Gaya Nonton Konser', 'social_energy': 'Energi Sosial',
            'matching_goal': 'Tujuan Cari Teman',
        }
        widgets = {
            'nik': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '16', 'placeholder': 'Masukkan 16 digit NIK'}),
            'nama_ktp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap sesuai KTP'}),
            'foto_ktp': ModernClearableFileInput(attrs={'class': 'form-control', 'id': 'id_foto_ktp'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ceritakan sedikit tentang dirimu.'}),
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'concert_vibe': forms.Select(attrs={'class': 'form-select'}),
            'social_energy': forms.Select(attrs={'class': 'form-select'}),
            'matching_goal': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'background_image': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture_2': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'profile_picture_3': ModernClearableFileInput(attrs={'class': 'form-control'}),
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['nik'].required = True
        self.fields['nama_ktp'].required = True
        
        if not self.instance or not self.instance.foto_ktp:
            self.fields['foto_ktp'].required = True
        else:
            self.fields['foto_ktp'].required = False
        
        if not self.instance or not self.instance.profile_picture:
            self.fields['profile_picture'].required = True
        else:
            self.fields['profile_picture'].required = False

        dropdown_fields = ['gender', 'concert_vibe', 'social_energy', 'matching_goal']
        for field_name in dropdown_fields:
            if field_name in self.fields:
                existing_choices = [c for c in self.fields[field_name].choices if c[0] != '']
                self.fields[field_name].choices = [('', '-- Pilih salah satu --')] + existing_choices

    def clean(self):
        cleaned_data = super().clean()
        
        p1 = cleaned_data.get('profile_picture')
        p2 = cleaned_data.get('profile_picture_2')
        p3 = cleaned_data.get('profile_picture_3')

        active_pics = []
        for p in [p1, p2, p3]:
            if p: 
                active_pics.append(p)

        cleaned_data['profile_picture'] = active_pics[0] if len(active_pics) > 0 else False
        cleaned_data['profile_picture_2'] = active_pics[1] if len(active_pics) > 1 else False
        cleaned_data['profile_picture_3'] = active_pics[2] if len(active_pics) > 2 else False

        return cleaned_data