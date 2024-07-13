import scrapy
import asyncio
from twisted.internet import reactor, defer, threads
import scrapy
import asyncio
from twisted.internet import reactor, threads
from DuckDuckGo import DuckDuckGo
from GeminiQueryGenerator import Gemini



class SimpleSpider(scrapy.Spider):
    name = "simple_spider"

    def __init__(self, *args, **kwargs):
        super(SimpleSpider, self).__init__(*args, **kwargs)
        self.url_queue_size_threshold = 20
        self.fetching_urls = False
    
    def start_requests(self):
        self.run_async_fetch_urls()
        for url in self.start_urls:
            yield scrapy.Request(url, self.parse)

    def parse(self, response):
        self.logger.info(f"Parsing URL: {response.url}")

        self.check_queue_size()

    def check_queue_size(self):
        remaining_requests = len(self.crawler.engine.slot.scheduler)
        self.logger.info(f"Remaining requests in the queue: {remaining_requests}")
        if remaining_requests <= self.url_queue_size_threshold and not self.fetching_urls:
            self.logger.info("Queue size below threshold, fetching new URLs...")
            self.fetching_urls = True
            self.crawler.engine.pause()
            threads.deferToThread(self.run_async_fetch_urls)

    def run_async_fetch_urls(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.fetch_new_urls())
        loop.close()

    async def fetch_new_urls(self):

        gemini = Gemini()
        duckDuckGo = DuckDuckGo()

        # List to store links
        newLinks = []
        try:
            # Generate new queries
            newQueries = gemini.generate_queries()
            self.logger.info("Generated new queries: %s", newQueries)
            
            # Request results
            newLinks = duckDuckGo.requestResults(newQueries)
        except Exception as e:
            self.logger.error("An error occurred in main function: %s", e)


        for url in newLinks:
            self.crawler.engine.crawl(scrapy.Request(url, self.parse))
        
        self.logger.info(f"Added {len(newLinks)} new URLs to the queue")
        self.fetching_urls = False
        self.crawler.engine.unpause()
        # Schedule the next check
        reactor.callLater(1, self.check_queue_size)

    def spider_idle(self):
        self.check_queue_size()
        return defer.Deferred()  # Keep the spider open
