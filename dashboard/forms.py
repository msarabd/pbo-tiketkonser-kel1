from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from accounts.models import User, UserProfile
from ticketing.models import Venue, Event, TicketCategory

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = '__all__'

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'

class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model = TicketCategory
        fields = '__all__'

# ================= FORM EDIT PENGGUNA KHUSUS ADMIN =================
class AdminUserEditForm(forms.ModelForm):
    password_baru = forms.CharField(
        label="Password Baru",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Kosongkan jika tidak ingin mengubah password'}),
        help_text="Minimal 6 karakter. Biarkan kosong jika pengguna tidak ingin mengganti password."
    )
    konfirmasi_password = forms.CharField(
        label="Konfirmasi Password Baru",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ulangi password baru'})
    )

    class Meta:
        model = User
        fields = ['username', 'no_hp']
        labels = {
            'username': 'Nama Profil / Username',
            'no_hp': 'Nomor WhatsApp',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'no_hp': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password_baru')
        p2 = cleaned_data.get('konfirmasi_password')

        if p1 or p2:
            if p1 != p2:
                raise ValidationError("Konfirmasi password baru tidak cocok!")
            if len(p1) < 6:
                raise ValidationError("Password baru minimal 6 karakter.")
        return cleaned_data