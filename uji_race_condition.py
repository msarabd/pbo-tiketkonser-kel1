import os
import django
import concurrent.futures
from django.utils import timezone

# 1. Inisiasi environment Django di luar manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from ticketing.services import hold_ticket_for_user
from ticketing.models import Concert, TicketCategory, TicketHold
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

def setup_data_ujian():
    """Membuat panggung ujian bersih dari nol"""
    print("Menyiapkan data ujian...")
    # Bersihkan data lama agar tes ini valid
    TicketHold.objects.all().delete()
    
    # Buat 1 konser dan 1 kategori dengan HANYA 5 TIKET
    konser, _ = Concert.objects.get_or_create(
        name="Konser Ujian OOP", 
        defaults={'venue': "Terminal", 'date': timezone.now(), 'description': "Tes"}
    )
    kategori, _ = TicketCategory.objects.get_or_create(
        concert=konser, name="Reguler",
        defaults={'price': 100000, 'total_quota': 5}
    )
    
    # Pastikan kuota reset ke 5 setiap kali script jalan
    kategori.total_quota = 5
    kategori.save()
    
    # Buat 10 User bot untuk menyerang sistem
    users = []
    for i in range(10):
        user, _ = User.objects.get_or_create(username=f"bot_pembeli_{i}")
        users.append(user)
        
    return users, kategori

def serang_sistem(user, kategori_id):
    """Fungsi yang akan dijalankan bersamaan oleh banyak thread"""
    try:
        # Setiap bot mencoba menahan 2 tiket
        hold = hold_ticket_for_user(user, kategori_id, quantity=2)
        return f"SUKSES: {user.username} menahan 2 tiket. (Sisa: {hold.category.get_available_tickets()})"
    except ValidationError as e:
        return f"DITOLAK (Validasi): {user.username} - {str(e)}"
    except Exception as e:
        # Menangkap error 'database is locked' khas SQLite
        return f"DITOLAK (DB Lock): {user.username} - {str(e)}"

if __name__ == '__main__':
    users, kategori = setup_data_ujian()
    print(f"\nMULAI UJIAN: Tersedia {kategori.get_available_tickets()} tiket.")
    print("Menyerang dengan 10 bot secara bersamaan (Total permintaan: 20 tiket)...\n")

    # Mengeksekusi fungsi serang_sistem menggunakan 10 thread secara paralel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(serang_sistem, user, kategori.id) for user in users]
        
        for future in concurrent.futures.as_completed(futures):
            print(future.result())

    print(f"\nUJIAN SELESAI. Sisa tiket sesungguhnya: {kategori.get_available_tickets()}")