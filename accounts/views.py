import math
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from .models import UserProfile, FriendRequest, User
from .forms import UserProfileForm, CustomUserCreationForm, UserEditForm
from ticketing.models import Event, OrderItem

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Akun berhasil dibuat! Silakan masuk.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})

@login_required
def edit_profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil dan Nomor Kontak berhasil diperbarui!')
            return redirect('accounts:profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)
        
    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'form': profile_form
    })

def haversine_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
        
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@login_required
def swipe_friends_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    has_ticket = OrderItem.objects.filter(
        order__user=request.user,
        order__status='PAID',
        category__event=event
    ).exists()

    if not has_ticket:
        messages.error(request, "Kamu belum memiliki tiket lunas untuk konser ini.")
        return redirect('event_detail', event_id=event.id)
        
    return render(request, 'accounts/swipe_friends.html', {'event': event})

@login_required
def api_get_swipe_data(request, event_id):
    user_profile = getattr(request.user, 'profile', None)
    
    interacted_ids = FriendRequest.objects.filter(
        event_id=event_id
    ).filter(
        models.Q(sender=request.user) | models.Q(receiver=request.user)
    ).values_list('receiver_id', 'sender_id')
    
    flat_interacted_ids = set([id for tuple in interacted_ids for id in tuple])

    buyers = list(UserProfile.objects.filter(
        user__order__status='PAID',
        user__order__orderitem__category__event_id=event_id
    ).exclude(user=request.user).exclude(user__id__in=flat_interacted_ids).distinct())

    my_lat = user_profile.latitude if user_profile else None
    my_lon = user_profile.longitude if user_profile else None

    for p in buyers:
        if my_lat is not None and my_lon is not None and p.latitude is not None and p.longitude is not None:
            try:
                p.calculated_distance = haversine_distance(float(my_lat), float(my_lon), float(p.latitude), float(p.longitude))
            except TypeError:
                p.calculated_distance = float('inf')
        else:
            p.calculated_distance = float('inf')

    buyers.sort(key=lambda x: x.calculated_distance)

    data = []
    for p in buyers:
        if p.calculated_distance != float('inf'):
            dist_str = f"{round(p.calculated_distance, 1)} km dari lokasimu"
        else:
            dist_str = "Jarak tidak diketahui"

        images = []
        if p.profile_picture: images.append(p.profile_picture.url)
        if p.profile_picture_2: images.append(p.profile_picture_2.url)
        if p.profile_picture_3: images.append(p.profile_picture_3.url)

        data.append({
            'id': p.user.id,
            'username': p.user.username,
            'age': p.age or '',
            'nama_ktp': p.nama_ktp or '',
            'bio': p.bio or 'Belum ada bio.',
            'gender': p.get_gender_display() or '',
            'distance': dist_str,
            'vibe': p.get_concert_vibe_display() or '',
            'energy': p.get_social_energy_display() or '',
            'goal': p.get_matching_goal_display() or '',
            'images': images,
            'bg_image': p.background_image.url if p.background_image else None
        })

    return JsonResponse({'profiles': data})

@login_required
@require_POST
def api_send_friend_request(request, event_id):
    try:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        event = get_object_or_404(Event, id=event_id)
        receiver_user = get_object_or_404(User, id=receiver_id)

        if request.user == receiver_user:
            return JsonResponse({'error': 'Tidak valid'}, status=400)

        obj, created = FriendRequest.objects.get_or_create(
            sender=request.user,
            receiver=receiver_user,
            event=event,
            defaults={'status': 'PENDING'}
        )
        return JsonResponse({'status': 'success', 'created': created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def api_respond_friend_request(request, request_id):
    try:
        data = json.loads(request.body)
        action = data.get('action') 
        
        freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)
        
        if action == 'accept':
            freq.status = 'ACCEPTED'
        elif action == 'reject':
            freq.status = 'REJECTED'
        freq.save()
        
        return JsonResponse({'status': 'success', 'new_status': freq.status})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_get_friend_requests(request):
    sent = FriendRequest.objects.filter(sender=request.user).select_related('receiver__profile', 'event')
    received = FriendRequest.objects.filter(receiver=request.user).select_related('sender__profile', 'event')

    my_profile = getattr(request.user, 'profile', None)
    my_lat = my_profile.latitude if my_profile else None
    my_lon = my_profile.longitude if my_profile else None

    data = []
    
    def process_requests(queryset, direction):
        for req in queryset:
            p = req.receiver.profile if direction == 'sent' else req.sender.profile
            
            dist_str = "Jarak tidak diketahui"
            if my_lat is not None and my_lon is not None and p.latitude is not None and p.longitude is not None:
                try:
                    dist = haversine_distance(float(my_lat), float(my_lon), float(p.latitude), float(p.longitude))
                    dist_str = f"{round(dist, 1)} km dari lokasimu"
                except TypeError:
                    pass

            data.append({
                'req_id': req.id,
                'direction': direction,
                'status': req.status,
                'user_id': p.user.id,
                'username': p.user.username,
                'event_name': req.event.nama_konser,
                'profile_pic': p.profile_picture.url if p.profile_picture else None,
                'no_hp': p.user.no_hp if req.status == 'ACCEPTED' else None,
                'age': p.age,
                'bio': p.bio,
                'gender': p.get_gender_display(),
                'vibe': p.get_concert_vibe_display(),
                'energy': p.get_social_energy_display(),
                'goal': p.get_matching_goal_display(),
                'distance': dist_str,
                'bg_image': p.background_image.url if p.background_image else None
            })

    process_requests(sent, 'sent')
    process_requests(received, 'received')

    return JsonResponse({'requests': data})