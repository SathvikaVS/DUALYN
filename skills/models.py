from django.db import models

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    normalized_name = models.CharField(max_length=100, unique=True, editable=False)
    category = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        self.normalized_name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
