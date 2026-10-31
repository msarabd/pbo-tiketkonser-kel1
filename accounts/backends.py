from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class MultiFieldModelBackend(ModelBackend):
    """
    Menimpa backend autentikasi bawaan Django agar pengguna bisa 
    login menggunakan username ataupun nomor HP.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Cari user berdasarkan username ATAU no_hp
            user = User.objects.get(Q(username__iexact=username) | Q(no_hp__iexact=username))
        except User.DoesNotExist:
            # Jalankan hashing palsu untuk mencegah timing attack
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None