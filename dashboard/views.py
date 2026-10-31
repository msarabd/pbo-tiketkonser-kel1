import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Q

from accounts.models import User, UserProfile
from accounts.forms import UserEditForm, UserProfileForm
from ticketing.models import Venue, Event, TicketCategory, OrderItem, ForumMessage
from ticketing.views import MessageCensorService

# Impor dari layer internal Dashboard
from .forms import VenueForm, EventForm, TicketCategoryForm
from .services import DashboardAnalyticsService, DashboardModerationService


@staff_member_required(login_url='login')
def dashboard_index(request):
    metrics = DashboardAnalyticsService.get_summary_metrics()
    chart_labels, chart_data = DashboardAnalyticsService.get_sales_trend(days=7)
    
    context = {
        'total_event': metrics['total_event'],
        'total_venue': metrics['total_venue'],
        'total_anggota': metrics['total_anggota'],
        'total_terjual': metrics['total_terjual'],
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'event_terpopuler': DashboardAnalyticsService.get_top_events(),
        'aktivitas_terbaru': DashboardAnalyticsService.get_recent_transactions(),
        'active_tab': 'dashboard',
    }
    return render(request, 'dashboard/index.html', context)


# ==============================================================================
# TAB 2: KELOLA VENUE
# ==============================================================================
@staff_member_required(login_url='login')
def kelola_venue(request):
    venues = Venue.objects.annotate(total_event=Count('event')).order_by('nama')
    return render(request, 'dashboard/kelola_venue.html', {'venues': venues, 'active_tab': 'venue'})

@staff_member_required(login_url='login')
def tambah_venue(request):
    form = VenueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Venue baru berhasil ditambahkan.")
        return redirect('dashboard:kelola_venue')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': 'Tambah Venue Baru', 'active_tab': 'venue', 'back_url': 'dashboard:kelola_venue'
    })

@staff_member_required(login_url='login')
def edit_venue(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id)
    form = VenueForm(request.POST or None, instance=venue)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Venue '{venue.nama}' berhasil diperbarui.")
        return redirect('dashboard:kelola_venue')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': f'Edit Venue: {venue.nama}', 'active_tab': 'venue', 'back_url': 'dashboard:kelola_venue'
    })

@staff_member_required(login_url='login')
def hapus_venue(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id)
    nama = venue.nama
    venue.delete()
    messages.success(request, f"Venue '{nama}' berhasil dihapus.")
    return redirect('dashboard:kelola_venue')


# ==============================================================================
# TAB 3: KELOLA EVENT & FORUM
# ==============================================================================
@staff_member_required(login_url='login')
def kelola_event(request):
    events = Event.objects.select_related('venue').order_by('-tanggal')
    return render(request, 'dashboard/kelola_event.html', {'events': events, 'active_tab': 'event'})

@staff_member_required(login_url='login')
def tambah_event(request):
    form = EventForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Event baru berhasil ditambahkan.")
        return redirect('dashboard:kelola_event')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': 'Tambah Event Konser Baru', 'active_tab': 'event', 'back_url': 'dashboard:kelola_event'
    })

@staff_member_required(login_url='login')
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Event '{event.nama_konser}' berhasil diperbarui.")
        return redirect('dashboard:kelola_event')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': f'Edit Event: {event.nama_konser}', 'active_tab': 'event', 'back_url': 'dashboard:kelola_event'
    })

@staff_member_required(login_url='login')
def hapus_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        DashboardModerationService.delete_event_safely(event)
        messages.success(request, "Event berhasil dihapus.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('dashboard:kelola_event')

@staff_member_required(login_url='login')
def event_buyers(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    sold_items = OrderItem.objects.filter(category__event=event, order__status='PAID').select_related('order__user__profile', 'category', 'ticket').order_by('-order__waktu_pesan')
    return render(request, 'dashboard/event_buyers.html', {'event': event, 'sold_items': sold_items, 'active_tab': 'event'})

@staff_member_required(login_url='login')
def forum_monitor(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        pesan = request.POST.get('message')
        gambar = request.FILES.get('image')
        if pesan:
            pesan = MessageCensorService.sensor(pesan)
        if pesan or gambar:
            ForumMessage.objects.create(event=event, sender=request.user, message=pesan, image=gambar)
        return redirect('dashboard:forum_monitor', event_id=event.id)
    forum_messages = event.forum_messages.select_related('sender__profile').all()
    return render(request, 'dashboard/forum_monitor.html', {'event': event, 'forum_messages': forum_messages, 'active_tab': 'event'})

@staff_member_required(login_url='login')
def delete_forum_message(request, message_id):
    message = get_object_or_404(ForumMessage, id=message_id)
    event_id = message.event.id
    message.delete()
    messages.success(request, "Pesan forum berhasil dihapus oleh Moderator.")
    return redirect('dashboard:forum_monitor', event_id=event_id)


# ==============================================================================
# TAB 4: KELOLA TICKET CATEGORY
# ==============================================================================
@staff_member_required(login_url='login')
def kelola_ticket_kategory(request):
    categories = TicketCategory.objects.select_related('event').annotate(
        total_terjual=Count('orderitem', filter=Q(orderitem__order__status='PAID'))
    ).order_by('event__nama_konser')
    return render(request, 'dashboard/kelola_ticket_kategory.html', {'categories': categories, 'active_tab': 'ticket_kategory'})

@staff_member_required(login_url='login')
def tambah_ticket_kategory(request):
    form = TicketCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Kategori tiket berhasil ditambahkan.")
        return redirect('dashboard:kelola_ticket_kategory')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': 'Tambah Kategori Tiket', 'active_tab': 'ticket_kategory', 'back_url': 'dashboard:kelola_ticket_kategory'
    })

@staff_member_required(login_url='login')
def edit_ticket_kategory(request, category_id):
    category = get_object_or_404(TicketCategory, id=category_id)
    form = TicketCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Kategori '{category.nama_kategori}' berhasil diperbarui.")
        return redirect('dashboard:kelola_ticket_kategory')
    return render(request, 'dashboard/form.html', {
        'form': form, 'title': f'Edit Kategori: {category.nama_kategori}', 'active_tab': 'ticket_kategory', 'back_url': 'dashboard:kelola_ticket_kategory'
    })

@staff_member_required(login_url='login')
def hapus_ticket_kategory(request, category_id):
    category = get_object_or_404(TicketCategory, id=category_id)
    nama = category.nama_kategori
    category.delete()
    messages.success(request, f"Kategori tiket '{nama}' berhasil dihapus.")
    return redirect('dashboard:kelola_ticket_kategory')


# ==============================================================================
# TAB 5: KELOLA USER
# ==============================================================================
@staff_member_required(login_url='login')
def kelola_user(request):
    users = User.objects.filter(is_staff=False).select_related('profile').order_by('-date_joined')
    return render(request, 'dashboard/kelola_user.html', {'users': users, 'active_tab': 'user'})

@staff_member_required(login_url='login')
def edit_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if target_user.is_staff or target_user.is_superuser:
        messages.error(request, "Penolakan Sistem: Tidak diizinkan mengedit profil sesama Administrator.")
        return redirect('dashboard:kelola_user')

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=target_user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=target_profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f'Data pengguna {target_user.username} berhasil diintervensi dan diperbarui.')
            return redirect('dashboard:kelola_user')
    else:
        user_form = UserEditForm(instance=target_user)
        profile_form = UserProfileForm(instance=target_profile)

    return render(request, 'dashboard/edit_user.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'target_user': target_user,
        'active_tab': 'user'
    })

@staff_member_required(login_url='login')
def toggle_user_status(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if user_obj.is_staff or user_obj.is_superuser:
        messages.error(request, "Status akun staf atau superuser tidak boleh diubah dari panel ini.")
        return redirect('dashboard:kelola_user')

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=['is_active'])
    status_str = "diaktifkan" if user_obj.is_active else "dinonaktifkan"
    messages.success(request, f"Akun pengguna '{user_obj.username}' berhasil {status_str}.")
    return redirect('dashboard:kelola_user')