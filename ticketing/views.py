from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import re

from .models import Event, Order, ForumMessage, OrderItem
from .services import book_ticket_securely, process_payment_and_issue_tickets

# --- LOGIKA SENSOR ---
def sensor_pesan(teks):
    if not teks:
        return teks
    
    daftar_kata_kasar = ['anjing', 'babi', 'bangsat', 'tolol', 'goblok', 'kontol', 'memek']
    for kata in daftar_kata_kasar:
        pola_kasar = re.compile(r'\b' + re.escape(kata) + r'\b', re.IGNORECASE)
        teks = pola_kasar.sub('*' * len(kata), teks)
    
    pola_telepon = re.compile(r'\b(\d{5,7})(\d{5})\b')
    teks = pola_telepon.sub(r'\g<1>*****', teks)
    
    return teks

def event_list(request):
    batas_kadaluarsa = timezone.now() - timedelta(days=3)
    
    # Base query untuk semua event yang belum expired (batas H+3)
    valid_events = Event.objects.select_related('venue').filter(tanggal__gte=batas_kadaluarsa)
    
    # 1. LARIS MANIS: Ambil 3 event dengan total tiket (OrderItem) berstatus PAID paling banyak
    top_events = valid_events.annotate(
        sold_tickets=Count('ticketcategory__orderitem', filter=Q(ticketcategory__orderitem__order__status='PAID'))
    ).order_by('-sold_tickets')[:3]
    
    # 2. EVENT TERDEKAT: Ambil 8 event terdekat yang belum berlalu
    closest_events = valid_events.filter(tanggal__gte=timezone.now()).order_by('tanggal')[:8]

    return render(request, 'ticketing/event_list.html', {
        'events': valid_events,         # Untuk carousel Rekomendasi
        'top_events': top_events,       # Untuk section Laris Manis
        'closest_events': closest_events# Untuk section Event Terdekat
    })

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    categories = event.ticketcategory_set.all()
    return render(request, 'ticketing/event_detail.html', {'event': event, 'categories': categories})

@login_required(login_url='login')
def book_ticket(request, category_id):
    if request.method == 'POST':
        quantity = request.POST.get('quantity', 1)
        try:
            pesanan = book_ticket_securely(request.user, category_id, quantity)
            return redirect('checkout', order_id=pesanan.id)
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect(request.META.get('HTTP_REFERER', '/'))
    return redirect('event_list')

@login_required(login_url='login')
def checkout(request, order_id):
    pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
    items = pesanan.orderitem_set.all()
    return render(request, 'ticketing/checkout.html', {'pesanan': pesanan, 'items': items})

@login_required(login_url='login')
def pay_order(request, order_id):
    if request.method == 'POST':
        try:
            process_payment_and_issue_tickets(request.user, order_id)
            return redirect('ticket_history')
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('checkout', order_id=order_id)
    return redirect('event_list')

@login_required(login_url='login')
def ticket_history(request):
    pesanan_lunas = Order.objects.filter(
        user=request.user, status='PAID'
    ).prefetch_related('orderitem_set__ticket', 'orderitem_set__category__event').order_by('-waktu_pesan')
    return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas})

def register(request):
    if request.user.is_authenticated:
        return redirect('event_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Akun {user.username} berhasil didaftarkan!")
            return redirect('event_list')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def forum_list(request):
    user_events = Event.objects.filter(
        ticketcategory__orderitem__order__user=request.user,
        ticketcategory__orderitem__order__status='PAID'
    ).distinct()
    return render(request, 'ticketing/forum_list.html', {'events': user_events})

@login_required
def forum_room(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    has_ticket = OrderItem.objects.filter(
        order__user=request.user,
        order__status='PAID',
        category__event=event
    ).exists()
    
    if not has_ticket:
        return redirect('forum_list')

    if request.method == 'POST':
        if event.is_forum_closed:
            messages.error(request, "Forum ini telah ditutup karena melewati batas H+3.")
            return redirect('forum_room', event_id=event.id)

        pesan = request.POST.get('message')
        gambar = request.FILES.get('image')
        
        if pesan:
            pesan = sensor_pesan(pesan)
        
        if pesan or gambar:
            ForumMessage.objects.create(
                event=event,
                sender=request.user,
                message=pesan,
                image=gambar
            )
        return redirect('forum_room', event_id=event.id)

    forum_messages = event.forum_messages.all()
    return render(request, 'ticketing/forum_room.html', {
        'event': event, 
        'forum_messages': forum_messages
    })

@login_required
def delete_forum_message(request, message_id):
    message = get_object_or_404(ForumMessage, id=message_id)
    if message.sender != request.user:
        messages.error(request, "Anda tidak berhak menghapus pesan ini.")
        return redirect('forum_room', event_id=message.event.id)
    
    event_id = message.event.id
    message.delete()
    return redirect('forum_room', event_id=event_id)