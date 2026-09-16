from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'college', 'degree', 'graduation_year')
    search_fields = ('user__username', 'college')
