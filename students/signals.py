from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Student_Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        Student_Profile.objects.get_or_create(User=instance, defaults={'Full_name': instance.username})