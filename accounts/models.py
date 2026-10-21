import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# ==============================================================================
# USER MODEL (Pindahan dari ticketing)
# ==============================================================================
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_hp = models.CharField(max_length=15, blank=True)

# ==============================================================================
# USER PROFILE (Untuk filter cari teman)
# ==============================================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    bio = models.TextField(max_length=500, blank=True, null=True, help_text="Ceritakan sedikit tentang dirimu.")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Kategori Filter Pencarian Teman
    VIBE_CHOICES = [
        ('fancam', 'Tim Fancam / Dokumentasi'),
        ('sing_along', 'Tim Sing-along'),
        ('frontline', 'Tim Frontline / Moshing'),
        ('santai', 'Tim Kalem / Penikmat Senja'),
        ('merch', 'Pemburu Merch'),
    ]
    ENERGY_CHOICES = [
        ('ekstrovert', 'Ekstrovert / Hype-maker'),
        ('introvert', 'Introvert / Pendengar'),
        ('ambivert', 'Ambivert / Fleksibel'),
    ]
    GOAL_CHOICES = [
        ('ride_sharing', 'Teman Jalan / Ride Sharing'),
        ('se_section', 'Teman Se-Section / Barrier Guard'),
        ('nginap', 'Teman Kost / Nginap'),
        ('networking', 'Networking / Teman Baru'),
    ]
    GENDER_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]

    concert_vibe = models.CharField(max_length=20, choices=VIBE_CHOICES, blank=True, null=True)
    social_energy = models.CharField(max_length=20, choices=ENERGY_CHOICES, blank=True, null=True)
    matching_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Profil dari {self.user.username}"