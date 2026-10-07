from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# --- INHERITANCE: User -> Buyer & Organizer ---
class User(AbstractUser):
    # AbstractUser Django sudah memiliki id, nama (first_name), dan email.
    # Kita tambahkan noHp sesuai spesifikasi Class Diagram
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_hp = models.CharField(max_length=15, blank=True)
    is_organizer = models.BooleanField(default=False)

class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nama = models.CharField(max_length=200)
    kota = models.CharField(max_length=100)

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    nama_konser = models.CharField(max_length=200)
    artis = models.CharField(max_length=200)
    tanggal = models.DateTimeField()
    tipe = models.CharField(max_length=50) # misal: Konser, Festival
    poster = models.ImageField(upload_to='event_posters/', null=True, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_organizer': True})

class TicketCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nama_kategori = models.CharField(max_length=100)
    harga = models.IntegerField()
    kuota = models.IntegerField()
    pakai_kursi = models.BooleanField(default=False)

# Class Seat merepresentasikan kursi spesifik (jika pakai_kursi = True)
class Seat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    kode_kursi = models.CharField(max_length=10) # Misal: A1, B2
    status = models.CharField(max_length=20, default='TERSEDIA') # TERSEDIA, DITAHAN, TERJUAL

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    waktu_pesan = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='PENDING')
    total_harga = models.IntegerField(default=0)

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, blank=True)
    harga_satuan = models.IntegerField()

# --- INTERFACE & POLYMORPHISM: MetodePembayaran ---
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    metode = models.CharField(max_length=50) # QRIS atau Virtual Account
    status_bayar = models.CharField(max_length=20, default='UNPAID')
    kode_referensi = models.CharField(max_length=100, blank=True)

class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    kode_qr = models.CharField(max_length=255, unique=True)
    sudah_dipakai = models.BooleanField(default=False)

class ForumMessage(models.Model):
    # Relasi ke Event. 1 Event punya 1 room chat.
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='forum_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Isi pesan (Teks dan Gambar)
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='forum_images/', blank=True, null=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Urutkan dari pesan terlama ke terbaru

    def __str__(self):
        return f"{self.sender.username} di {self.event.nama_konser}"