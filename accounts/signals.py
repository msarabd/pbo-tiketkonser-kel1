# accounts/signals.py

from django.db.models.signals import pre_delete
from django.dispatch import receiver
from ticketing.models import OrderItem
from accounts.models import UserProfile

@receiver(pre_delete, sender=OrderItem)
def clean_tutorial_memory(sender, instance, **kwargs):
    try:
        # Tangkap user dan event dari tiket yang akan dihapus
        user = instance.order.user
        event = instance.category.event
        
        # Cek apakah user masih punya tiket pesanan lain (yang belum dihapus) untuk konser ini
        has_other_tickets = OrderItem.objects.filter(
            order__user=user,
            category__event=event
        ).exclude(id=instance.id).exists()
        
        # Jika tidak ada tiket lain, cabut ingatan tutorialnya
        if not has_other_tickets:
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                profile.tutorial_seen_events.remove(event)
    except Exception:
        # Blok try-except penting jika objek terkait (seperti order) sudah terlanjur hancur di database
        pass