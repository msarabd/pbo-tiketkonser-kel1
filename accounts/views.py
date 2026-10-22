from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .forms import UserProfileForm, CustomUserCreationForm

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
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil berhasil diperbarui!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=profile)
        
    return render(request, 'accounts/edit_profile.html', {'form': form})

@login_required
def find_friends_view(request):
    # Mengambil profil pengguna lain (mengecualikan diri sendiri)
    profiles = UserProfile.objects.exclude(user=request.user).select_related('user')

    # Parameter filter query GET
    vibe_filter = request.GET.get('concert_vibe', '')
    energy_filter = request.GET.get('social_energy', '')
    goal_filter = request.GET.get('matching_goal', '')
    gender_filter = request.GET.get('gender', '')

    if vibe_filter:
        profiles = profiles.filter(concert_vibe=vibe_filter)
    if energy_filter:
        profiles = profiles.filter(social_energy=energy_filter)
    if goal_filter:
        profiles = profiles.filter(matching_goal=goal_filter)
    if gender_filter:
        profiles = profiles.filter(gender=gender_filter)

    context = {
        'profiles': profiles,
        'vibe_choices': UserProfile.VIBE_CHOICES,
        'energy_choices': UserProfile.ENERGY_CHOICES,
        'goal_choices': UserProfile.GOAL_CHOICES,
        'gender_choices': UserProfile.GENDER_CHOICES,
        'selected_vibe': vibe_filter,
        'selected_energy': energy_filter,
        'selected_goal': goal_filter,
        'selected_gender': gender_filter,
    }
    return render(request, 'accounts/find_friends.html', context)