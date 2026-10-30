import re
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q, Min, Prefetch
from django.urls import reverse_lazy

from .models import Event, Order, ForumMessage, OrderItem, Venue, TicketCategory, HOLD_DURATION_MINUTES
from .services import book_ticket_securely, process_payment_and_issue_tickets
from accounts.models import UserProfile
from .forms import VenueForm, EventForm, TicketCategoryForm
from django.contrib.auth import get_user_model
User = get_user_model()

class MessageCensorService:
    KATA_KASAR = ['anjing', 'babi', 'bangsat', 'tolol', 'goblok', 'kontol', 'memek']

    @classmethod
    def sensor(cls, teks):
        if not teks:
            return teks
        for kata in cls.KATA_KASAR:
            pola_kasar = re.compile(r'\b' + re.escape(kata) + r'\b', re.IGNORECASE)
            teks = pola_kasar.sub('*' * len(kata), teks)
        pola_telepon = re.compile(r'\b(\d{5,7})(\d{5})\b')
        teks = pola_telepon.sub(r'\g<1>*****', teks)
        return teks


# ==============================================================================
# MIXIN KEAMANAN & AKSES
# ==============================================================================
class IsNotAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return not (self.request.user.is_staff or self.request.user.is_superuser)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Admin tidak diizinkan mengakses fitur transaksi dan pengguna.")
            return redirect('admin_dashboard')
        return redirect('login')


class IsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


# ==============================================================================
# VIEW PUBLIK & PENGGUNA BIASA
# ==============================================================================
class EventListView(ListView):
    model = Event
    template_name = 'ticketing/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        batas_kadaluarsa = timezone.now() - timedelta(days=3)
        return Event.objects.select_related('venue').filter(tanggal__gte=batas_kadaluarsa).order_by('tanggal')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batas_kadaluarsa = timezone.now() - timedelta(days=3)
        base_qs = Event.objects.select_related('venue').filter(tanggal__gte=batas_kadaluarsa)

        top_events = base_qs.annotate(
            sold_tickets=Count('ticketcategory__orderitem', filter=Q(ticketcategory__orderitem__order__status='PAID'))
        ).order_by('-sold_tickets')[:3]

        closest_events = base_qs.filter(tanggal__gte=timezone.now()).order_by('tanggal')[:8]
        jelajah_events = base_qs.annotate(harga_mulai=Min('ticketcategory__harga'))

        q = self.request.GET.get('q', '')
        lokasi = self.request.GET.get('lokasi', '')
        kategori = self.request.GET.get('kategori', '')
        waktu = self.request.GET.get('waktu', '')
        harga = self.request.GET.get('harga', '')
        sort_by = self.request.GET.get('sort', 'terdekat')

        if q:
            jelajah_events = jelajah_events.filter(Q(nama_konser__icontains=q) | Q(artis__icontains=q) | Q(venue__kota__icontains=q))
        if lokasi: jelajah_events = jelajah_events.filter(venue__kota=lokasi)
        if kategori: jelajah_events = jelajah_events.filter(tipe=kategori)

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

        if harga == '<200': jelajah_events = jelajah_events.filter(harga_mulai__lt=200000)
        elif harga == '<500': jelajah_events = jelajah_events.filter(harga_mulai__lt=500000)
        elif harga == '<1000': jelajah_events = jelajah_events.filter(harga_mulai__lt=1000000)
        elif harga == '>1000': jelajah_events = jelajah_events.filter(harga_mulai__gte=1000000)

        if sort_by == 'termurah': jelajah_events = jelajah_events.order_by('harga_mulai')
        elif sort_by == 'termahal': jelajah_events = jelajah_events.order_by('-harga_mulai')
        elif sort_by == 'terbaru': jelajah_events = jelajah_events.order_by('-tanggal')
        else: jelajah_events = jelajah_events.order_by('tanggal')

        context.update({
            'top_events': top_events,
            'closest_events': closest_events,
            'jelajah_events': jelajah_events.distinct(),
            'lokasi_list': Venue.objects.values_list('kota', flat=True).distinct().order_by('kota'),
            'kategori_list': Event.EventType.choices,
            'active_tab': self.request.GET.get('tab', 'beranda')
        })
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'ticketing/event_detail.html'
    context_object_name = 'event'
    pk_url_kwarg = 'event_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = self.object.ticketcategory_set.all()
        return context


class BookTicketView(LoginRequiredMixin, IsNotAdminMixin, View):
    def post(self, request, category_id):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.nik or not profile.profile_picture or not request.user.no_hp:
            messages.warning(request, "Akses ditolak. Kamu wajib mengisi Nomor WA, NIK, dan mengunggah Foto Profil Utama sebelum memesan tiket.")
            return redirect('accounts:edit_profile')

        kategori = get_object_or_404(TicketCategory, id=category_id)
        if kategori.event.time_status == 'EXPIRED':
            messages.error(request, "Pemesanan ditolak. Konser ini telah berakhir.")
            return redirect('event_detail', event_id=kategori.event.id)

        quantity = request.POST.get('quantity', 1)
        try:
            pesanan = book_ticket_securely(request.user, category_id, quantity)
            return redirect('checkout', order_id=pesanan.id)
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect(request.META.get('HTTP_REFERER', '/'))

    def get(self, request, category_id):
        return redirect('event_list')


class CheckoutView(LoginRequiredMixin, IsNotAdminMixin, View):
    def get(self, request, order_id):
        pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
        if pesanan.is_expired:
            pesanan.cancel_order()
            first_item = pesanan.orderitem_set.first()
            event_id = first_item.category.event.id if first_item else None
            messages.error(request, f"Batas waktu pembayaran ({HOLD_DURATION_MINUTES} menit) telah habis. Pesanan Anda dibatalkan otomatis.")
            if event_id: return redirect('event_detail', event_id=event_id)
            return redirect('event_list')

        items = pesanan.orderitem_set.all()
        batas_waktu_iso = pesanan.expired_at.isoformat()
        return render(request, 'ticketing/checkout.html', {
            'pesanan': pesanan, 'items': items, 'batas_waktu_iso': batas_waktu_iso
        })


class PayOrderView(LoginRequiredMixin, IsNotAdminMixin, View):
    def post(self, request, order_id):
        pesanan = Order.objects.filter(id=order_id, user=request.user).first()
        if not pesanan:
            messages.error(request, "Pesanan tidak ditemukan.")
            return redirect('event_list')

        if pesanan.status == 'PAID':
            return redirect('payment_success', order_id=pesanan.id)

        if pesanan.is_expired or pesanan.status == 'CANCELED':
            if pesanan.status == 'PENDING':
                pesanan.cancel_order()
            messages.error(request, f"Pesanan gagal diproses karena batas waktu {HOLD_DURATION_MINUTES} menit telah habis.")
            return redirect('event_list')

        try:
            process_payment_and_issue_tickets(request.user, order_id)
            return redirect('payment_success', order_id=order_id)
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('checkout', order_id=order_id)

    def get(self, request, order_id):
        return redirect('event_list')


class PaymentSuccessView(LoginRequiredMixin, IsNotAdminMixin, View):
    def get(self, request, order_id):
        pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PAID')
        return render(request, 'ticketing/payment_success.html', {'pesanan': pesanan})


class TicketHistoryView(LoginRequiredMixin, IsNotAdminMixin, View):
    def get(self, request):
        pesanan_lunas = Order.objects.filter(user=request.user, status='PAID').prefetch_related('orderitem_set__ticket', 'orderitem_set__category__event').order_by('-waktu_pesan')
        pesanan_pending = Order.objects.filter(user=request.user, status='PENDING').prefetch_related('orderitem_set__category__event').order_by('-waktu_pesan')

        tagihan_aktif = []
        for p in pesanan_pending:
            if p.is_expired: p.cancel_order()
            else: tagihan_aktif.append(p)

        return render(request, 'ticketing/history.html', {'pesanan_lunas': pesanan_lunas, 'tagihan_aktif': tagihan_aktif})


class ForumListView(LoginRequiredMixin, IsNotAdminMixin, View):
    def get(self, request):
        user_events = Event.objects.filter(ticketcategory__orderitem__order__user=request.user, ticketcategory__orderitem__order__status='PAID').distinct()
        return render(request, 'ticketing/forum_list.html', {'events': user_events})


class ForumRoomView(LoginRequiredMixin, IsNotAdminMixin, View):
    def dispatch(self, request, *args, **kwargs):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        has_ticket = OrderItem.objects.filter(order__user=request.user, order__status='PAID', category__event=event).exists()
        if not has_ticket: return redirect('forum_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        # Gunakan sender__profile agar data profil dan foto di-join langsung
        forum_messages = event.forum_messages.select_related('sender__profile').all()
        return render(request, 'ticketing/forum_room.html', {'event': event, 'forum_messages': forum_messages})

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        if event.is_forum_closed:
            messages.error(request, "Forum ini telah ditutup karena melewati batas H+3.")
            return redirect('forum_room', event_id=event.id)
            
        pesan = request.POST.get('message')
        gambar = request.FILES.get('image')
        
        if pesan: pesan = MessageCensorService.sensor(pesan)
        if pesan or gambar: ForumMessage.objects.create(event=event, sender=request.user, message=pesan, image=gambar)
        return redirect('forum_room', event_id=event.id)


class DeleteForumMessageView(LoginRequiredMixin, IsNotAdminMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(ForumMessage, id=message_id)
        if message.sender != request.user:
            messages.error(request, "Anda tidak berhak menghapus pesan ini.")
            return redirect('forum_room', event_id=message.event.id)
        event_id = message.event.id
        message.delete()
        return redirect('forum_room', event_id=event_id)


class ChooseFriendConcertView(LoginRequiredMixin, IsNotAdminMixin, View):
    def get(self, request):
        user_events = Event.objects.filter(ticketcategory__orderitem__order__user=request.user, ticketcategory__orderitem__order__status='PAID').distinct()
        return render(request, 'ticketing/choose_friend_concert.html', {'events': user_events})


class CancelOrderView(LoginRequiredMixin, IsNotAdminMixin, View):
    def post(self, request, order_id):
        pesanan = get_object_or_404(Order, id=order_id, user=request.user, status='PENDING')
        pesanan.cancel_order()
        messages.success(request, f"Pesanan #{str(pesanan.id)[:8].upper()} berhasil dibatalkan.")
        return redirect('ticket_history')

    def get(self, request, order_id):
        return redirect('ticket_history')


# ==============================================================================
# VIEW KHUSUS ADMIN (DASHBOARD & MONITORING FORUM DENGAN FITUR CHAT & HAPUS)
# ==============================================================================
class AdminDashboardView(IsAdminMixin, ListView):
    model = Event
    template_name = 'ticketing/admin_dashboard.html'
    context_object_name = 'events'

    def get_queryset(self):
        # Hitung jumlah tiket terjual yang status pembayarannya lunas (PAID)
        kategori_annotated = TicketCategory.objects.annotate(
            total_terjual=Count('orderitem', filter=Q(orderitem__order__status='PAID'))
        )
        return Event.objects.prefetch_related(
            Prefetch('ticketcategory_set', queryset=kategori_annotated),
            'venue'
        ).order_by('-tanggal')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venues'] = Venue.objects.all()
        return context


class AdminForumMonitorView(IsAdminMixin, View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        # Gunakan sender__profile agar data profil dan foto di-join langsung
        forum_messages = event.forum_messages.select_related('sender__profile').all()
        return render(request, 'ticketing/admin_forum_monitor.html', {
            'event': event, 
            'forum_messages': forum_messages
        })

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        pesan = request.POST.get('message')
        gambar = request.FILES.get('image')

        if pesan:
            pesan = MessageCensorService.sensor(pesan)
        if pesan or gambar:
            ForumMessage.objects.create(event=event, sender=request.user, message=pesan, image=gambar)

        return redirect('admin_forum_monitor', event_id=event.id)


class AdminDeleteForumMessageView(IsAdminMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(ForumMessage, id=message_id)
        event_id = message.event.id
        message.delete()
        messages.success(request, "Pesan forum berhasil dihapus oleh Moderator.")
        return redirect('admin_forum_monitor', event_id=event_id)


# --- KELAS DASAR CRUD ADMIN ---
class AdminBaseCreateView(IsAdminMixin, CreateView):
    template_name = 'ticketing/admin_form.html'
    success_url = reverse_lazy('admin_dashboard')
    def form_valid(self, form):
        messages.success(self.request, f"Data {self.model.__name__} berhasil ditambahkan.")
        return super().form_valid(form)

class AdminBaseUpdateView(IsAdminMixin, UpdateView):
    template_name = 'ticketing/admin_form.html'
    success_url = reverse_lazy('admin_dashboard')
    def form_valid(self, form):
        messages.success(self.request, f"Data {self.model.__name__} berhasil diperbarui.")
        return super().form_valid(form)

class AdminBaseDeleteView(IsAdminMixin, DeleteView):
    template_name = 'ticketing/admin_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard')
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"Data {self.model.__name__} berhasil dihapus.")
        return super().delete(request, *args, **kwargs)

# --- VENUE CRUD ---
class AdminVenueCreateView(AdminBaseCreateView): model = Venue; form_class = VenueForm
class AdminVenueUpdateView(AdminBaseUpdateView): model = Venue; form_class = VenueForm
class AdminVenueDeleteView(AdminBaseDeleteView): model = Venue

# --- EVENT CRUD ---
class AdminEventCreateView(AdminBaseCreateView): model = Event; form_class = EventForm
class AdminEventUpdateView(AdminBaseUpdateView): model = Event; form_class = EventForm
class AdminEventDeleteView(AdminBaseDeleteView): model = Event

# --- TICKET CATEGORY CRUD ---
class AdminTicketCategoryCreateView(AdminBaseCreateView): model = TicketCategory; form_class = TicketCategoryForm
class AdminTicketCategoryUpdateView(AdminBaseUpdateView): model = TicketCategory; form_class = TicketCategoryForm
class AdminTicketCategoryDeleteView(AdminBaseDeleteView): model = TicketCategory

class AdminEventBuyersView(IsAdminMixin, View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        # Ambil semua item pesanan yang sudah lunas (PAID) untuk konser ini
        sold_items = OrderItem.objects.filter(
            category__event=event,
            order__status='PAID'
        ).select_related('order__user__profile', 'category', 'ticket').order_by('-order__waktu_pesan')
        
        return render(request, 'ticketing/admin_event_buyers.html', {
            'event': event, 
            'sold_items': sold_items
        })

class AdminUserListView(IsAdminMixin, ListView):
    model = User
    template_name = 'ticketing/admin_user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        # Sengaja menyembunyikan superuser dari daftar agar tidak terhapus oleh admin awam
        return User.objects.filter(is_superuser=False).select_related('profile').order_by('-date_joined')

class AdminUserDeleteView(IsAdminMixin, View):
    def post(self, request, user_id):
        user_to_delete = get_object_or_404(User, id=user_id)
        
        if user_to_delete.is_staff or user_to_delete.is_superuser:
            messages.error(request, "Penolakan Sistem: Akun administrator tidak boleh dihapus dari panel ini.")
            return redirect('admin_user_list')
            
        username = user_to_delete.username
        # PERINGATAN: Tindakan ini akan memicu CASCADE DELETE pada Order, Ticket, dan ForumMessage
        user_to_delete.delete() 
        messages.success(request, f"Pengguna '{username}' dan seluruh riwayat datanya telah dimusnahkan secara permanen.")
        return redirect('admin_user_list')