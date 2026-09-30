from django.db import transaction
from django.core.exceptions import ValidationError
from .models import TicketCategory, TicketHold

def hold_ticket_for_user(user, category_id, quantity):
    """
    Service ini mencegah 2 orang mengambil tiket terakhir di milidetik yang sama.
    """
    # transaction.atomic memastikan jika ada error di tengah jalan, database di-rollback utuh.
    with transaction.atomic():
        # SELECT FOR UPDATE adalah nyawa sistem tiket. 
        # Ini MENGUNCI baris kategori tiket ini di database. 
        # User lain yang mau beli tiket ini akan disuruh antre menunggu eksekusi ini selesai.
        category = TicketCategory.objects.select_for_update().get(id=category_id)
        
        # Cek ketersediaan MENGGUNAKAN method OOP yang sudah kamu buat di models.py
        available = category.get_available_tickets()
        
        if available >= quantity:
            # Jika tiket ada, buat objek penahanan (Hold)
            hold = TicketHold.objects.create(
                user=user,
                category=category,
                quantity=quantity
            )
            return hold
        else:
            # Jika tidak ada, tolak secara brutal.
            raise ValidationError("Tiket tidak cukup atau sudah ditahan pengguna lain.")