from django.contrib import admin
from .models import SkillAnalysis, SkillGap, ShareLink


class SkillGapInline(admin.TabularInline):
    model = SkillGap
    extra = 0
    readonly_fields = ('skill', 'status', 'priority', 'reasoning')
    can_delete = False


@admin.register(SkillAnalysis)
class SkillAnalysisAdmin(admin.ModelAdmin):
    list_display = ('student', 'job_role', 'readiness_score', 'created_at')
    inlines = [SkillGapInline]


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'token', 'expires_at', 'revoked_at', 'hide_name', 'created_at')
    search_fields = ('token', 'analysis__student__username', 'analysis__job_role__title')
    list_filter = ('hide_name', 'revoked_at')
