from django.contrib import admin
from .models import Student_Profile


@admin.register(Student_Profile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('Full_name', 'Status', 'Education', 'Year_of_Study', 'College', 'Carrer_Interest')
    list_filter = ('Status', 'Education', 'Carrer_Interest')
    search_fields = ('Full_name', 'College')