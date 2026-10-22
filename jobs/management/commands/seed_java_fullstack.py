from django.core.management.base import BaseCommand
from seed_java_fullstack import seed_java_full_stack


class Command(BaseCommand):
    help = "Seeds the 'Java Full Stack Developer' role and all associated skills."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running Java Full Stack Developer seeder..."))
        seed_java_full_stack()
        self.stdout.write(self.style.SUCCESS("Successfully seeded Java Full Stack Developer!"))
