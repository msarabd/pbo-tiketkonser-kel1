from django.db import transaction
from django.core.exceptions import ValidationError
from .models import TicketCategory, Seat, Order, OrderItem, Payment, Ticket

def book_ticket_securely(user, category_id, quantity):
    """
    Logika transaksional OOP untuk mencegah Race Condition (Overselling)
    """
    # Memaksa kuantitas menjadi integer yang valid
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValidationError("Jumlah tiket tidak valid.")
    except ValueError:
        raise ValidationError("Format jumlah tiket salah.")

    # 1. Buka gerbang transaksi atomik (Semua sukses, atau semua dibatalkan)
    with transaction.atomic():
        # 2. LOCK DATABASE: Kunci kategori ini agar tidak bisa dibaca user lain yang menekan tombol bersamaan
        try:
            category = TicketCategory.objects.select_for_update().get(id=category_id)
        except TicketCategory.DoesNotExist:
            raise ValidationError("Kategori tiket tidak ditemukan.")

        # 3. Cek sisa kuota (Aman dari overselling karena sudah dilock)
        if category.kuota < quantity:
            raise ValidationError(f"Gagal. Sisa kuota tiket ini hanya {category.kuota}.")

        # 4. Alokasi Kursi (Jika kategori ini menggunakan kursi spesifik)
        alokasi_kursi = []
        if category.pakai_kursi:
            # Ambil kursi yang statusnya TERSEDIA sebanyak jumlah tiket, lalu KUNCI
            alokasi_kursi = list(Seat.objects.select_for_update().filter(
                category=category, status='TERSEDIA'
            )[:quantity])
            
            if len(alokasi_kursi) < quantity:
                raise ValidationError("Jumlah kursi kosong tidak mencukupi untuk pesanan ini.")
            
            # Ubah status kursi menjadi DITAHAN agar tidak direbut orang lain
            for seat in alokasi_kursi:
                seat.status = 'DITAHAN'
                seat.save()

        # 5. Kurangi Kuota Kategori
        category.kuota -= quantity
        category.save()

        # 6. Pembuatan UUID dan Objek Order secara Simultan
        pesanan = Order.objects.create(
            user=user,
            total_harga=category.harga * quantity,
            status='PENDING' # Status ditahan, belum dibayar
        )

        # 7. Pembuatan OrderItem (Pecahan per tiket)
        for i in range(quantity):
            # Jika ada kursi, pasangkan. Jika tidak (festival), biarkan None.
            kursi_terpilih = alokasi_kursi[i] if alokasi_kursi else None
            
            OrderItem.objects.create(
                order=pesanan,
                category=category,
                seat=kursi_terpilih,
                harga_satuan=category.harga
            )
            
    # Jika kode sampai di baris ini tanpa terhenti oleh ValidationError, 
    # maka transaksi dianggap LULUS dan kunci database dilepas.
    return pesanan

import uuid

def process_payment_and_issue_tickets(user, order_id):
    """
    Simulasi Payment Gateway (QRIS) dan Penerbitan Tiket Final
    """
    with transaction.atomic():
        # 1. Kunci pesanan yang akan dibayar
        try:
            pesanan = Order.objects.select_for_update().get(id=order_id, user=user, status='PENDING')
        except Order.DoesNotExist:
            raise ValidationError("Pesanan tidak ditemukan atau sudah dibayar.")
            
        # 2. Ubah status pesanan menjadi LUNAS
        pesanan.status = 'PAID'
        pesanan.save()
        
        # 3. Buat catatan Pembayaran (Konsep Polymorphism di Class Diagram)
        Payment.objects.create(
            order=pesanan,
            metode='QRIS',
            status_bayar='PAID',
            kode_referensi=f"QRIS-{uuid.uuid4().hex[:8].upper()}"
        )
        
        # 4. TERBITKAN TIKET untuk setiap item pesanan
        items = pesanan.orderitem_set.all()
        for item in items:
            Ticket.objects.create(
                order_item=item,
                kode_qr=f"TIX-{uuid.uuid4().hex.upper()}", # Men-generate string unik untuk QR
                sudah_dipakai=False
            )
            
        return pesanan