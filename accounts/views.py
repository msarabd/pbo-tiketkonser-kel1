import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile
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
    
    buyers = list(UserProfile.objects.filter(
        user__order__status='PAID',
        user__order__orderitem__category__event_id=event_id
    ).exclude(user=request.user).distinct())

    my_lat = user_profile.latitude if user_profile else None
    my_lon = user_profile.longitude if user_profile else None

    for p in buyers:
        if my_lat and my_lon and p.latitude and p.longitude:
            p.calculated_distance = haversine_distance(my_lat, my_lon, p.latitude, p.longitude)
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