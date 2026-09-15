from django.contrib import admin
from .models import Project, ProjectSkill


class ProjectSkillInline(admin.TabularInline):
    model = ProjectSkill
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'student', 'difficulty', 'created_at')
    search_fields = ('name', 'student__username')
    inlines = [ProjectSkillInline]
