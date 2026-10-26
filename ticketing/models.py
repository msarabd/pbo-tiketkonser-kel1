import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.db.models import Q, F, Count
from django.apps import apps

HOLD_DURATION_MINUTES = 15

# ==============================================================================
# BASE MODEL (STANDARISASI UUID)
# ==============================================================================
class BaseModel(models.Model):
    """
    [OOP - ABSTRAKSI & INHERITANCE]
    Kelas dasar abstrak yang menjadi cetakan untuk seluruh entitas sistem.
    Menstandarkan primary key berupa UUID v4 di seluruh tabel database.
    Parameter abstract = True memastikan kelas ini tidak membuat tabel fisik sendiri.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


# ==============================================================================
# VENUE
# ==============================================================================
class Venue(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel untuk mendapatkan primary key UUID secara otomatis.
    Menyimpan lokasi fisik pelaksanaan konser musik.
    """
    nama = models.CharField(max_length=200)
    kota = models.CharField(max_length=100)

    class Meta:
        unique_together = ('nama', 'kota')

    def __str__(self):
        return f"{self.nama} ({self.kota})"


# ==============================================================================
# EVENT (KONSER MUSIK)
# ==============================================================================
class Event(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Mengelola jadwal, deskripsi, artis, dan venue konser.
    """
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
        """
        [OOP - ENKAPSULASI]
        Membungkus logika komparasi waktu konser dengan waktu server saat ini.
        Komponen luar cukup mengakses `event.time_status` untuk mengetahui status UPCOMING, LIVE, atau EXPIRED.
        """
        sekarang = timezone.now()
        hari_h_awal = self.tanggal.replace(hour=0, minute=0, second=0, microsecond=0)
        hari_h_akhir = hari_h_awal + timedelta(days=1)

        if sekarang < hari_h_awal:
            return "UPCOMING"
        elif hari_h_awal <= sekarang < hari_h_akhir:
            return "LIVE"
        return "EXPIRED"

    @property
    def is_forum_closed(self):
        """
        [OOP - ENKAPSULASI]
        Menyembunyikan kalkulasi batas penutupan forum diskusi (H+3 hari pelaksanaan).
        """
        batas_waktu = self.tanggal + timedelta(days=3)
        return timezone.now() >= batas_waktu

    @property
    def jam_tersisa_forum(self):
        """
        [OOP - ENKAPSULASI]
        Menghitung selisih jam aktif forum tanpa mengekspos variabel tanggal mentah.
        """
        if self.is_forum_closed:
            return 0
        batas_waktu = self.tanggal + timedelta(days=3)
        selisih = batas_waktu - timezone.now()
        return int(selisih.total_seconds() // 3600)

    def __str__(self):
        return f"{self.nama_konser} oleh {self.artis}"


# ==============================================================================
# TIKET
# ==============================================================================
class TicketCategory(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Mengelola jenis kategori tiket, kuota alokasi, dan harga satuan.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nama_kategori = models.CharField(max_length=100)
    harga = models.IntegerField()
    kuota = models.IntegerField()

    class Meta:
        unique_together = ('event', 'nama_kategori')

    @property
    def is_available(self):
        """
        [OOP - ENKAPSULASI]
        Menyediakan status ketersediaan kuota tanpa memperbolehkan manipulasi kuota dari luar secara langsung.
        """
        return self.kuota > 0

    def __str__(self):
        return f"{self.nama_kategori} ({self.event.nama_konser})"


# ==============================================================================
# ORDER & TRANSAKSI
# ==============================================================================
class Order(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Mengelola siklus hidup transaksi tiket pengguna.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    waktu_pesan = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="PENDING")
    total_harga = models.IntegerField(default=0)

    @property
    def expired_at(self):
        """
        [OOP - ENKAPSULASI]
        Menghitung tenggat waktu bayar pesanan secara dinamis berdasarkan batas hold tiket.
        """
        return self.waktu_pesan + timedelta(minutes=HOLD_DURATION_MINUTES)

    @property
    def is_expired(self):
        """
        [OOP - ENKAPSULASI]
        Mengevaluasi apakah order sudah melewati batas waktu bayar tanpa perlu dicek manual di view.
        """
        return timezone.now() > self.expired_at

    def cancel_order(self):
        """
        [OOP - ENKAPSULASI]
        Menyembunyikan seluruh prosedur pembatalan pesanan.
        Metode ini otomatis mengubah status menjadi CANCELED dan mengembalikan jumlah kuota
        ke masing-masing TicketCategory menggunakan ekspresi database atomik F().
        """
        if self.status == "PENDING":
            self.status = "CANCELED"
            self.save(update_fields=['status'])

            kategori_counts = self.orderitem_set.values('category_id').annotate(jumlah=Count('id'))
            for item in kategori_counts:
                TicketCategory.objects.filter(id=item['category_id']).update(kuota=F('kuota') + item['jumlah'])

    def __str__(self):
        return f"Order: {self.id} | Pemesan: {self.user.username}"


class OrderItem(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Menghubungkan pesanan induk dengan kategori tiket spesifik yang dipesan.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    harga_satuan = models.IntegerField()

    def __str__(self):
        return f"Item {self.category.nama_kategori} (Order {self.order.id})"


class Payment(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Mencatat status pembayaran dan referensi transaksi pembayaran tiket.
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    metode = models.CharField(max_length=50)
    status_bayar = models.CharField(max_length=20, default="UNPAID")
    kode_referensi = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Payment {self.id} [{self.status_bayar}]"


class Ticket(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Representasi fisik tiket digital yang memuat kode QR unik.
    """
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    kode_qr = models.CharField(max_length=255, unique=True)
    sudah_dipakai = models.BooleanField(default=False)

    def mark_as_used(self):
        """
        [OOP - ENKAPSULASI]
        Mengubah status tiket menjadi sudah terpakai hanya melalui prosedur internal kelas ini.
        """
        if not self.sudah_dipakai:
            self.sudah_dipakai = True
            self.save(update_fields=['sudah_dipakai'])

    def __str__(self):
        return f"Tiket {self.kode_qr[:8]}... | Status Dipakai: {self.sudah_dipakai}"


# ==============================================================================
# FORUM DISKUSI
# ==============================================================================
class ForumMessage(BaseModel):
    """
    [OOP - INHERITANCE]
    Mewarisi BaseModel. Menyimpan riwayat obrolan antar penonton pada konser yang sama.
    """
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
# SIGNALS (INTEGRASI OTOMATIS)
# ==============================================================================
@receiver(pre_delete, sender=OrderItem)
def bersihkan_data_sosial_saat_item_dihapus(sender, instance, **kwargs):
    order = instance.order
    user = order.user

    if not instance.category or not instance.category.event:
        return

    event = instance.category.event
    FriendRequest = apps.get_model('accounts', 'FriendRequest')

    masih_punya_tiket_lain = OrderItem.objects.filter(
        order__user=user,
        order__status='PAID',
        category__event=event
    ).exclude(id=instance.id).exists()

    if not masih_punya_tiket_lain:
        ForumMessage.objects.filter(sender=user, event=event).delete()
        FriendRequest.objects.filter(event=event).filter(
            Q(sender=user) | Q(receiver=user)
        ).delete()


@receiver(post_delete, sender=OrderItem)
def kembalikan_kuota_saat_item_dihapus(sender, instance, **kwargs):
    if instance.category_id:
        TicketCategory.objects.filter(id=instance.category_id).update(kuota=F('kuota') + 1)