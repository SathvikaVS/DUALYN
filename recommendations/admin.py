from django.contrib import admin
from .models import Recommendation, LearningRoadmap, RoadmapItem


class RoadmapItemInline(admin.TabularInline):
    model = RoadmapItem
    extra = 0


@admin.register(LearningRoadmap)
class LearningRoadmapAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'created_at')
    inlines = [RoadmapItemInline]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('skill_gap', 'analysis')
