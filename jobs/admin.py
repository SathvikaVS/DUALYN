from django.contrib import admin
from .models import JobRole, JobSkill


class JobSkillInline(admin.TabularInline):
    model = JobSkill
    extra = 3
    autocomplete_fields = ['skill']


@admin.register(JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'skill_count')
    search_fields = ('title',)
    inlines = [JobSkillInline]

    def skill_count(self, obj):
        return obj.job_skills.count()
    skill_count.short_description = 'Required Skills'
