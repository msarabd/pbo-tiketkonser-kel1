from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q, Min
from datetime import timedelta
import re
from .models import Event, Order, ForumMessage, OrderItem, Venue
from .services import book_ticket_securely, process_payment_and_issue_tickets
from accounts.models import UserProfile

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
    base_qs = Event.objects.select_related('venue').filter(tanggal__gte=batas_kadaluarsa)
    
    # --- DATA UNTUK TAB BERANDA ---
    top_events = base_qs.annotate(
        sold_tickets=Count('ticketcategory__orderitem', filter=Q(ticketcategory__orderitem__order__status='PAID'))
    ).order_by('-sold_tickets')[:3]
    
    closest_events = base_qs.filter(tanggal__gte=timezone.now()).order_by('tanggal')[:8]
    beranda_events = base_qs.order_by('tanggal') 
    
    # --- LOGIKA FILTER TAB JELAJAH ---
    jelajah_events = base_qs.annotate(harga_mulai=Min('ticketcategory__harga'))
    
    q = request.GET.get('q', '')
    lokasi = request.GET.get('lokasi', '')
    kategori = request.GET.get('kategori', '')
    waktu = request.GET.get('waktu', '')
    harga = request.GET.get('harga', '')
    sort_by = request.GET.get('sort', 'terdekat')
    
    if q:
        jelajah_events = jelajah_events.filter(
            Q(nama_konser__icontains=q) |
            Q(artis__icontains=q) |
            Q(venue__kota__icontains=q)
        )
    
    if lokasi:
        jelajah_events = jelajah_events.filter(venue__kota=lokasi)
        
    if kategori:
        jelajah_events = jelajah_events.filter(tipe=kategori)
        
    now = timezone.now()
    if waktu == 'minggu_ini':
        start_week = now - timedelta(days=now.weekday())
        end_week = start_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        jelajah_events = jelajah_events.filter(tanggal__range=[start_week, end_week])
    elif waktu == 'minggu_depan':
        start_next_week = now + timedelta(days=7 - now.weekday())
        end_next_week = start_next_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        jelajah_events = jelajah_events.filter(tanggal__range=[start_next_week, end_next_week])
    elif waktu == 'bulan_ini':
        jelajah_events = jelajah_events.filter(tanggal__year=now.year, tanggal__month=now.month)
    elif waktu == 'bulan_depan':
        next_month = 1 if now.month == 12 else now.month + 1
        next_year = now.year + 1 if now.month == 12 else now.year
        jelajah_events = jelajah_events.filter(tanggal__year=next_year, tanggal__month=next_month)
        
    if harga == '<200':
        jelajah_events = jelajah_events.filter(harga_mulai__lt=200000)
    elif harga == '<500':
        jelajah_events = jelajah_events.filter(harga_mulai__lt=500000)
    elif harga == '<1000':
        jelajah_events = jelajah_events.filter(harga_mulai__lt=1000000)
    elif harga == '>1000':
        jelajah_events = jelajah_events.filter(harga_mulai__gte=1000000)
        
    if sort_by == 'termurah':
        jelajah_events = jelajah_events.order_by('harga_mulai')
    elif sort_by == 'termahal':
        jelajah_events = jelajah_events.order_by('-harga_mulai')
    elif sort_by == 'terbaru':
        jelajah_events = jelajah_events.order_by('-tanggal')
    else: 
        jelajah_events = jelajah_events.order_by('tanggal')
        
    active_tab = request.GET.get('tab', 'beranda')
    
    # Data dropdown filter
    lokasi_list = Venue.objects.values_list('kota', flat=True).distinct().order_by('kota')
    kategori_list = Event.EventType.choices

    return render(request, 'ticketing/event_list.html', {
        'events': beranda_events,
        'top_events': top_events,
        'closest_events': closest_events,
        'jelajah_events': jelajah_events.distinct(),
        'lokasi_list': lokasi_list,
        'kategori_list': kategori_list,
        'active_tab': active_tab
    })

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    categories = event.ticketcategory_set.all()
    return render(request, 'ticketing/event_detail.html', {'event': event, 'categories': categories})

@login_required(login_url='login')
def book_ticket(request, category_id):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if not profile.nik or not profile.profile_picture or not request.user.no_hp:
        messages.warning(request, "Akses ditolak. Kamu wajib mengisi Nomor WA, NIK, dan mengunggah Foto Profil Utama sebelum memesan tiket.")
        return redirect('accounts:edit_profile')

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
    if pesanan.is_expired:
        pesanan.cancel_order()
        first_item = pesanan.orderitem_set.first()
        event_id = first_item.category.event.id if first_item else None
        messages.error(request, "Batas waktu pembayaran (24 Jam) telah habis. Pesanan Anda dibatalkan otomatis.")
        if event_id:
            return redirect('event_detail', event_id=event_id)
        return redirect('event_list')

    items = pesanan.orderitem_set.all()
    batas_waktu_iso = (pesanan.waktu_pesan + timedelta(hours=24)).isoformat()
    return render(request, 'ticketing/checkout.html', {
        'pesanan': pesanan, 'items': items, 'batas_waktu_iso': batas_waktu_iso
    })

@login_required(login_url='login')
def pay_order(request, order_id):
    if request.method == 'POST':
        pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
        if pesanan.is_expired:
            pesanan.cancel_order()
            messages.error(request, "Pesanan gagal diproses karena batas waktu 24 jam telah terlewati.")
            return redirect('event_list')
        try:
            process_payment_and_issue_tickets(request.user, order_id)
            return redirect('payment_success', order_id=order_id)
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('checkout', order_id=order_id)
    return redirect('event_list')

@login_required(login_url='login')
def payment_success(request, order_id):
    pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PAID')
    return render(request, 'ticketing/payment_success.html', {'pesanan': pesanan})

@login_required
def ticket_history(request):
    pesanan_lunas = Order.objects.filter(
        user=request.user, status='PAID'
    ).prefetch_related('orderitem_set__ticket', 'orderitem_set__category__event').order_by('-waktu_pesan')
    pesanan_pending = Order.objects.filter(
        user=request.user, status='PENDING'
    ).prefetch_related('orderitem_set__category__event').order_by('-waktu_pesan')
    tagihan_aktif = [p for p in pesanan_pending if not p.is_expired]
    return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas, 'tagihan_aktif': tagihan_aktif})

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
    
    if not has_ticket: return redirect('forum_list')

    if request.method == 'POST':
        if event.is_forum_closed:
            messages.error(request, "Forum ini telah ditutup karena melewati batas H+3.")
            return redirect('forum_room', event_id=event.id)
        pesan = request.POST.get('message')
        gambar = request.FILES.get('image')
        if pesan: pesan = sensor_pesan(pesan)
        if pesan or gambar:
            ForumMessage.objects.create(event=event, sender=request.user, message=pesan, image=gambar)
        return redirect('forum_room', event_id=event.id)

    forum_messages = event.forum_messages.all()
    return render(request, 'ticketing/forum_room.html', {'event': event, 'forum_messages': forum_messages})

@login_required
def delete_forum_message(request, message_id):
    message = get_object_or_404(ForumMessage, id=message_id)
    if message.sender != request.user:
        messages.error(request, "Anda tidak berhak menghapus pesan ini.")
        return redirect('forum_room', event_id=message.event.id)
    event_id = message.event.id
    message.delete()
    return redirect('forum_room', event_id=event_id)

@login_required
def choose_friend_concert(request):
    user_events = Event.objects.filter(
        ticketcategory__orderitem__order__user=request.user,
        ticketcategory__orderitem__order__status='PAID'
    ).distinct()
    return render(request, 'ticketing/choose_friend_concert.html', {'events': user_events})

@login_required(login_url='login')
def cancel_order_view(request, order_id):
    if request.method == 'POST':
        pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
        pesanan.cancel_order()
        messages.success(request, f"Pesanan #{str(pesanan.id)[:8].upper()} berhasil dibatalkan. Kuota telah dikembalikan ke sistem.")
    return redirect('ticket_history')