from django.contrib import admin
from .models import UserRole


@admin.action(description='Mark selected as verified')
def verify_selected(modeladmin, request, queryset):
    queryset.update(is_verified=True)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'organization', 'is_verified')
    list_filter = ('role', 'is_verified')
    list_editable = ('is_verified',)
    search_fields = ('user__username', 'user__email', 'organization')
    actions = [verify_selected]