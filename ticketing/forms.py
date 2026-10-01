from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

# Mengambil model User kustom yang aktif (ticketing.User)
User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)  # Tambahkan 'email' jika model usermu mewajibkan email