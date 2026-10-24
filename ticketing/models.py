from datetime import timedelta
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.db.models import Q, F
from django.apps import apps

# ==============================================================================
# BASE MODEL (STANDARISASI UUID)
# ==============================================================================
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

# ==============================================================================
# VENUE
# ==============================================================================
class Venue(BaseModel):
    nama = models.CharField(max_length=200)
    kota = models.CharField(max_length=100)

    class Meta:
        unique_together = ('nama', 'kota')

    def __str__(self):
        return f"{self.nama} ({self.kota})"

# ==============================================================================
# EVENT (TERPUSAT KHUSUS MUSIK)
# ==============================================================================
class Event(BaseModel):

    class EventType(models.TextChoices):
        FESTIVAL = "FESTIVAL", "Festival Musik"
        SOLO_CONCERT = "SOLO_CONCERT", "Konser Tunggal"
        INTIMATE_SHOW = "INTIMATE_SHOW", "Intimate Show"
        CAMPUS_FEST = "CAMPUS_FEST", "Pensi & Campus Fest"

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    nama_konser = models.CharField(max_length=200)
    artis = models.CharField(max_length=200)
    tanggal = models.DateTimeField()
    tipe = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.FESTIVAL,
    )
    poster = models.ImageField(upload_to="event_posters/", null=True, blank=True)
    deskripsi = models.TextField(blank=True, null=True)
    syarat_ketentuan = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('nama_konser', 'tanggal')

    @property
    def time_status(self):
        sekarang = timezone.now()
        hari_h_awal = self.tanggal.replace(hour=0, minute=0, second=0, microsecond=0)
        hari_h_akhir = hari_h_awal + timedelta(days=1)

        if sekarang < hari_h_awal:
            return "UPCOMING"
        elif hari_h_awal <= sekarang < hari_h_akhir:
            return "LIVE"
        else:
            return "EXPIRED"

    @property
    def is_forum_closed(self):
        batas_waktu = self.tanggal + timedelta(days=3)
        return timezone.now() >= batas_waktu

    @property
    def jam_tersisa_forum(self):
        if self.is_forum_closed:
            return 0
        batas_waktu = self.tanggal + timedelta(days=3)
        selisih = batas_waktu - timezone.now()
        return int(selisih.total_seconds() // 3600)

    def __str__(self):
        return f"{self.nama_konser} oleh {self.artis}"

# ==============================================================================
# TIKET & KURSI
# ==============================================================================
class TicketCategory(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nama_kategori = models.CharField(max_length=100)
    harga = models.IntegerField()
    kuota = models.IntegerField()
    pakai_kursi = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'nama_kategori')

    @property
    def is_available(self):
        return self.kuota > 0

    def __str__(self):
        return f"{self.nama_kategori} ({self.event.nama_konser})"


class Seat(BaseModel):
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    kode_kursi = models.CharField(max_length=10)
    status = models.CharField(max_length=20, default="TERSEDIA")

    @property
    def is_booked(self):
        return self.status != "TERSEDIA"

    def __str__(self):
        return f"{self.kode_kursi} [{self.status}]"

# ==============================================================================
# ORDER & TRANSAKSI
# ==============================================================================
class Order(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    waktu_pesan = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="PENDING")
    total_harga = models.IntegerField(default=0)

    @property
    def is_expired(self):
        # Ubah durasi hold tiket menjadi 15 menit
        batas_waktu = self.waktu_pesan + timedelta(minutes=15)
        return timezone.now() > batas_waktu
    
    def cancel_order(self):
        if self.status == "PENDING":
            self.status = "CANCELED"
            self.save()
            
            items = self.orderitem_set.all()
            for item in items:
                category = item.category
                category.kuota += 1
                category.save()
                
                if item.seat:
                    item.seat.status = "TERSEDIA"
                    item.seat.save()

    def __str__(self):
        return f"Order: {self.id} | Pemesan: {self.user.username}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, blank=True)
    harga_satuan = models.IntegerField()

    def __str__(self):
        return f"Item {self.category.nama_kategori} (Order {self.order.id})"


class Payment(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    metode = models.CharField(max_length=50)
    status_bayar = models.CharField(max_length=20, default="UNPAID")
    kode_referensi = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Payment {self.id} [{self.status_bayar}]"


class Ticket(BaseModel):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    kode_qr = models.CharField(max_length=255, unique=True)
    sudah_dipakai = models.BooleanField(default=False)

    def mark_as_used(self):
        if not self.sudah_dipakai:
            self.sudah_dipakai = True
            self.save()

    def __str__(self):
        return f"Tiket {self.kode_qr[:8]}... | Status Dipakai: {self.sudah_dipakai}"

# ==============================================================================
# FORUM DISKUSI
# ==============================================================================
class ForumMessage(BaseModel):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="forum_messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="forum_images/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender.username} di {self.event.nama_konser}"

# ==============================================================================
# SIGNALS
# ==============================================================================
@receiver(pre_delete, sender=OrderItem)
def bersihkan_data_sosial_saat_item_dihapus(sender, instance, **kwargs):
    order = instance.order
    user = order.user
    
    if not instance.category or not instance.category.event:
        return
        
    event = instance.category.event
    FriendRequest = apps.get_model('accounts', 'FriendRequest')
    
    # Cek apakah user MASIH memiliki tiket PAID lain di event yang sama
    # (Kecualikan OrderItem yang sedang dalam proses dihapus ini)
    masih_punya_tiket_lain = OrderItem.objects.filter(
        order__user=user,
        order__status='PAID',
        category__event=event
    ).exclude(id=instance.id).exists()
    
    # Jika ini tiket aktif terakhir miliknya untuk konser tersebut, musnahkan relasi sosialnya
    if not masih_punya_tiket_lain:
        ForumMessage.objects.filter(sender=user, event=event).delete()
        FriendRequest.objects.filter(event=event).filter(
            Q(sender=user) | Q(receiver=user)
        ).delete()


from django.db.models import F

@receiver(post_delete, sender=OrderItem)
def kembalikan_kuota_saat_item_dihapus(sender, instance, **kwargs):
    if instance.category_id:
        # Eksekusi penambahan langsung di level SQL database (bebas dari tabrakan memori Python)
        TicketCategory.objects.filter(id=instance.category_id).update(kuota=F('kuota') + 1)