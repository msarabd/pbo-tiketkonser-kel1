import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import TicketCategory, Order, OrderItem, Payment, Ticket

def book_ticket_securely(user, category_id, quantity):
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValidationError("Jumlah tiket tidak valid.")
    except ValueError:
        raise ValidationError("Format jumlah tiket salah.")

    with transaction.atomic():
        try:
            category = TicketCategory.objects.select_for_update().get(id=category_id)
        except TicketCategory.DoesNotExist:
            raise ValidationError("Kategori tiket tidak ditemukan.")

        if category.kuota < quantity:
            raise ValidationError(f"Gagal. Sisa kuota tiket ini hanya {category.kuota}.")

        category.kuota -= quantity
        category.save(update_fields=['kuota'])

        pesanan = Order.objects.create(
            user=user,
            total_harga=category.harga * quantity,
            status='PENDING'
        )

        order_items = [
            OrderItem(order=pesanan, category=category, harga_satuan=category.harga)
            for _ in range(quantity)
        ]
        OrderItem.objects.bulk_create(order_items)

    return pesanan


def process_payment_and_issue_tickets(user, order_id):
    with transaction.atomic():
        try:
            pesanan = Order.objects.select_for_update().get(id=order_id, user=user, status='PENDING')
        except Order.DoesNotExist:
            raise ValidationError("Pesanan tidak ditemukan atau sudah dibayar.")

        pesanan.status = 'PAID'
        pesanan.save(update_fields=['status'])

        Payment.objects.create(
            order=pesanan,
            metode='QRIS',
            status_bayar='PAID',
            kode_referensi=f"QRIS-{uuid.uuid4().hex[:8].upper()}"
        )

        items = pesanan.orderitem_set.all()
        tickets = [
            Ticket(
                order_item=item,
                kode_qr=f"TIX-{uuid.uuid4().hex.upper()}",
                sudah_dipakai=False
            )
            for item in items
        ]
        Ticket.objects.bulk_create(tickets)

        return pesanan