from django.contrib import admin
from .models import SkillAnalysis, SkillGap


class SkillGapInline(admin.TabularInline):
    model = SkillGap
    extra = 0
    readonly_fields = ('skill', 'status', 'priority', 'reasoning')
    can_delete = False


@admin.register(SkillAnalysis)
class SkillAnalysisAdmin(admin.ModelAdmin):
    list_display = ('student', 'job_role', 'readiness_score', 'created_at')
    inlines = [SkillGapInline]
