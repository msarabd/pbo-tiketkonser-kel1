from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rute aplikasi autentikasi buatanmu (Register, Profil, Edit Profil)
    path('accounts/', include('accounts.urls')), 
    
    # Rute bawaan Django untuk Login, Logout, dan Password Reset
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # Rute aplikasi tiketmu yang lama
    path('tickets/', include('ticketing.urls')), 
]

# Wajib ditambahkan agar Django bisa melayani file gambar/media saat tahap development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)