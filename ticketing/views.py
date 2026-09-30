from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest
from .models import Concert, TicketHold, Order
from .services import hold_ticket_for_user
from django.core.exceptions import ValidationError

def concert_list(request):
    concerts = Concert.objects.prefetch_related('ticketcategory_set').all()
    
    # Menangkap permintaan dari form frontend
    search_query = request.GET.get('search', '')
    city_query = request.GET.get('city', '')
    genre_query = request.GET.get('genre', '')
    
    # Mengeksekusi filter OOP pada database
    if search_query:
        concerts = concerts.filter(name__icontains=search_query)
    if city_query:
        concerts = concerts.filter(city__icontains=city_query)
    if genre_query:
        concerts = concerts.filter(genre__icontains=genre_query)
        
    return render(request, 'ticketing/concert_list.html', {
        'concerts': concerts,
        'search_query': search_query,
    })

def book_ticket(request, category_id):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return HttpResponseBadRequest("Tolak: Anda harus login.")
        
        quantity = int(request.POST.get('quantity', 1))
        try:
            hold = hold_ticket_for_user(request.user, category_id, quantity)
            # PERUBAHAN: Jangan kembalikan teks, tapi redirect ke halaman checkout
            return redirect('checkout', hold_id=hold.id)
        except ValidationError as e:
            return HttpResponseBadRequest(str(e))
    return HttpResponseBadRequest("Metode tidak diizinkan.")

def checkout(request, hold_id):
    # Cari tiket yang ditahan, pastikan milik user yang sedang login
    hold = get_object_or_404(TicketHold, id=hold_id, user=request.user)
    
    # OOP in action: Cek apakah waktu 15 menit sudah habis
    if hold.is_expired():
        hold.delete() # Kembalikan tiket ke kuota publik
        return HttpResponseBadRequest("Waktu pembayaran Anda habis. Tiket telah dilepas.")
    
    # Hitung sementara untuk ditampilkan di layar (bukan untuk disimpan ke DB)
    total_sementara = hold.category.price * hold.quantity
    
    return render(request, 'ticketing/checkout.html', {'hold': hold, 'total': total_sementara})

def process_payment(request, hold_id):
    """Simulasi gerbang pembayaran dan finalisasi OOP"""
    if request.method == 'POST':
        hold = get_object_or_404(TicketHold, id=hold_id, user=request.user)
        
        if hold.is_expired():
            hold.delete()
            return HttpResponseBadRequest("Terlambat. Waktu habis saat memproses pembayaran.")

        # FINALISASI OOP: Buat objek Order di memori
        pesanan = Order(
            user=hold.user, 
            category=hold.category, 
            quantity=hold.quantity, 
            status='PAID'
        )
        
        # Panggil method OOP untuk menghitung harga (Aman dari manipulasi hacker)
        pesanan.calculate_total()
        
        # Panggil method OOP untuk membuat QR Code
        pesanan.generate_qr()
        
        # Hapus objek penahanan karena sudah resmi jadi pesanan lunas
        hold.delete()
        
        return redirect('order_success', order_id=pesanan.id)

def order_success(request, order_id):
    pesanan = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'ticketing/success.html', {'pesanan': pesanan})

def ticket_history(request):
    # Mengambil semua pesanan LUNAS milik pengguna yang sedang login
    pesanan_lunas = Order.objects.filter(user=request.user, status='PAID').order_by('-created_at')
    return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas})

from django.contrib.auth.decorators import login_required

@login_required(login_url='/admin/login/') # Memaksa user login, jika belum lempar ke halaman login admin
def ticket_history(request):
    # Logika OOP: Ambil Order, filter berdasarkan user yang request, filter status lunas, urutkan dari yang terbaru
    pesanan_lunas = Order.objects.filter(user=request.user, status='PAID').order_by('-created_at')
    return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas})