from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
import qrcode
from io import BytesIO
from django.core.files import File

class Concert(models.Model):
    name = models.CharField(max_length=200)
    venue = models.CharField(max_length=200)
    city = models.CharField(max_length=100, default='Jakarta')
    genre = models.CharField(max_length=50, default='Pop')
    date = models.DateTimeField()
    description = models.TextField()
    # Ini atribut baru wajib untuk fotomu
    poster = models.ImageField(upload_to='concert_posters/', blank=True, null=True) 

    def __str__(self):
        return self.name
    
class TicketCategory(models.Model):
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_quota = models.IntegerField()

    def __str__(self):
        return f"{self.concert.name} - {self.name}"

    def get_available_tickets(self):
        # 1. Hitung total tiket yang sudah lunas (PAID)
        sold_tickets = self.order_set.filter(status='PAID').aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # 2. Hitung total tiket yang sedang 'ditahan' dan BELUM kedaluwarsa
        # Batas waktu adalah sekarang dikurangi 15 menit. 
        time_threshold = timezone.now() - timedelta(minutes=15)
        active_holds = self.tickethold_set.filter(held_at__gte=time_threshold).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # 3. Ketersediaan = Kuota Total - (Terjual + Sedang Ditahan)
        return self.total_quota - (sold_tickets + active_holds)

class TicketHold(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    held_at = models.DateTimeField(auto_now_add=True)
    
    def is_expired(self):
        # Mengembalikan True jika waktu saat ini sudah melewati batas 15 menit dari held_at
        return timezone.now() > self.held_at + timedelta(minutes=15)

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), 
        ('PAID', 'Paid'), 
        ('FAILED', 'Failed')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def calculate_total(self):
        # OOP dasar: Objek Order menghitung harganya sendiri dengan mengambil harga dari relasi Category
        self.total_price = self.category.price * self.quantity
        self.save()

    def generate_qr(self):
        # Hanya buat QR jika belum ada QR dan status sudah dibayar
        if not self.qr_code and self.status == 'PAID':
            # Data yang disimpan di dalam QR
            qr_data = f"ORDER-{self.id}-USER-{self.user.id}-CAT-{self.category.name}"
            
            # Generate gambar QR
            img = qrcode.make(qr_data)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Simpan ke field database
            file_name = f"tiket_{self.id}_{self.user.username}.png"
            self.qr_code.save(file_name, File(buffer), save=False)
            self.save()