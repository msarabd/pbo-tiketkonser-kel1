import uuid
from datetime import date
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from PIL import Image
from ticketing.models import Event

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_hp = models.CharField(max_length=15, blank=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    nik = models.CharField(max_length=16, unique=True, blank=True, null=True, help_text="Nomor Induk Kependudukan 16 digit")
    nama_ktp = models.CharField(max_length=100, blank=True, null=True)
    
    background_image = models.ImageField(upload_to='profile_bgs/', blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    profile_picture_2 = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    profile_picture_3 = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    bio = models.TextField(max_length=500, blank=True, null=True, help_text="Ceritakan sedikit tentang dirimu.")
    
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

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    @property
    def age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    def __str__(self):
        return f"Profil dari {self.user.username}"

    def save(self, *args, **kwargs):
        image_fields = [self.profile_picture, self.profile_picture_2, self.profile_picture_3, self.background_image]

        for field in image_fields:
            if field and not getattr(field, '_committed', True):
                try:
                    img = Image.open(field.file)
                    img.verify()
                except Exception:
                    raise ValidationError("Salah satu file yang diunggah rusak atau bukan format gambar yang valid.")

        super().save(*args, **kwargs)

        for field in image_fields:
            if field and hasattr(field, 'path') and field.path:
                try:
                    img = Image.open(field.path)
                    if img.height > 800 or img.width > 800:
                        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        img.save(field.path, quality=85, optimize=True)
                except Exception:
                    pass

class FriendRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu'),
        ('ACCEPTED', 'Diterima'),
        ('REJECTED', 'Ditolak'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver', 'event')

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} [{self.status}]"