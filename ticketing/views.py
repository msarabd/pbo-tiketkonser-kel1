from django.shortcuts import render, get_object_or_404
from .models import Event

def event_list(request):
    # Mengambil semua event. 
    # select_related digunakan untuk mengambil data Venue sekaligus, mencegah query lambat (N+1 problem)
    events = Event.objects.select_related('venue').all()
    return render(request, 'ticketing/event_list.html', {'events': events})

def event_detail(request, event_id):
    # UUID digunakan sebagai parameter pengaman
    event = get_object_or_404(Event, id=event_id)
    categories = event.ticketcategory_set.all()
    return render(request, 'ticketing/event_detail.html', {'event': event, 'categories': categories})

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from .services import book_ticket_securely
from .models import Order

@login_required(login_url='/admin/login/')
def book_ticket(request, category_id):
    if request.method == 'POST':
        # Tangkap jumlah yang diinput pengguna dari form HTML
        quantity = request.POST.get('quantity', 1)
        
        try:
            # KABEL 2: Eksekusi mesin utama dari services.py
            pesanan = book_ticket_securely(request.user, category_id, quantity)
            
            # Jika lolos Race Condition, lempar ke halaman pembayaran
            return redirect('checkout', order_id=pesanan.id)
            
        except ValidationError as e:
            # Jika overselling atau kuota tidak cukup, tangkap errornya
            messages.error(request, e.message)
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
    return redirect('event_list')

@login_required(login_url='/admin/login/')
def checkout(request, order_id):
    # Kunci pesanan hanya untuk user yang sedang login agar tidak bisa diintip orang lain
    pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
    items = pesanan.orderitem_set.all()
    
    return render(request, 'ticketing/checkout.html', {'pesanan': pesanan, 'items': items})

from .services import process_payment_and_issue_tickets

@login_required(login_url='/admin/login/')
def pay_order(request, order_id):
    if request.method == 'POST':
        try:
            # Panggil layanan pembayaran
            process_payment_and_issue_tickets(request.user, order_id)
            # Jika sukses, lempar ke halaman riwayat pesanan
            return redirect('ticket_history')
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('checkout', order_id=order_id)
    return redirect('event_list')

@login_required(login_url='/admin/login/')
def ticket_history(request):
    # Ambil pesanan yang LUNAS, beserta relasi Item dan Tiketnya agar tidak lambat
    pesanan_lunas = Order.objects.filter(
        user=request.user, status='PAID'
    ).prefetch_related('orderitem_set__ticket', 'orderitem_set__category__event').order_by('-waktu_pesan')
    
    return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas})