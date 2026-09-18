from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('student', 'file', 'uploaded_at')
    readonly_fields = ('extracted_text',)
