from django.core.management.base import BaseCommand
from websites.models import Website
from websites.tasks import crawl_website_task

class Command(BaseCommand):
    help = 'Crawls websites to extract style guide, tone, and metadata.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Crawl all websites, ignoring needs_crawl flag',
        )
        parser.add_argument(
            '--async-mode',
            action='store_true',
            help='Run crawl tasks asynchronously via Celery',
        )

    def handle(self, *args, **options):
        all_sites = options['all']
        async_mode = options['async_mode']

        if all_sites:
            websites = Website.objects.all()
            self.stdout.write(self.style.NOTICE('Queuing crawl for all websites...'))
        else:
            websites = Website.objects.filter(needs_crawl=True)
            self.stdout.write(self.style.NOTICE('Queuing crawl for websites requiring update (needs_crawl=True)...'))

        count = websites.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No websites to crawl.'))
            return

        for website in websites:
            self.stdout.write(f"Starting crawl for {website.name} ({website.url})...")
            if async_mode:
                crawl_website_task.delay(website.id)
                self.stdout.write(self.style.SUCCESS(f"Task queued in background for {website.name}."))
            else:
                try:
                    # Run synchronously using Celery's .apply()
                    result = crawl_website_task.apply(args=[website.id])
                    if result.status == 'SUCCESS':
                        self.stdout.write(self.style.SUCCESS(f"Successfully crawled and updated {website.name}."))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to crawl {website.name}: {result.result}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Exception during crawl for {website.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} websites."))
