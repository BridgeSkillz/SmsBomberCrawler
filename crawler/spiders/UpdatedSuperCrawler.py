import scrapy
import asyncio
from twisted.internet import reactor, defer, threads
import scrapy
import asyncio
from twisted.internet import reactor, threads
from DuckDuckGo import DuckDuckGo
from GeminiQueryGenerator import Gemini


from scrapy.http import HtmlResponse
from urllib.parse import urlparse

from Model import SearchEngineResponse, CrawlerDiscovery, SitesWithTelField, get_session, get_engine
from typing import List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import hashlib
import os
from CommonMethods import get_domain_link


class SuperSpider(scrapy.Spider):
    name = "SUPER_SPIDER"

    def __init__(self, *args, **kwargs):
        super(SuperSpider, self).__init__(*args, **kwargs)
        self.url_queue_size_threshold = 20
        self.fetching_urls = False
        self.engine = get_engine()


    def start_requests(self):
        self.run_async_fetch_urls()
        for url in self.start_urls:
            yield scrapy.Request(url, self.parse)

    def parse(self, response):
        self.logger.info(f"Parsing response from {response.url}")
        new_domains = self.get_new_domains(response)
        self.phoneNumberFieldDetectorFilter(response)
        self.saveNewDomains(new_domains)
        yield from self.visit_existing_links(response)
        self.check_queue_size()

    def check_queue_size(self):
        remaining_requests = len(self.crawler.engine.slot.scheduler)
        self.logger.info(f"Remaining requests in the queue: {remaining_requests}")
        if (
            remaining_requests <= self.url_queue_size_threshold
            and not self.fetching_urls
        ):
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
            newLinks = await duckDuckGo.requestResults(newQueries)
        except Exception as e:
            self.logger.error("An error occurred in fetching new urls function: %s", e)

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

    def level2_crawling(self, response: HtmlResponse):
        self.logger.info(f"Level 2 crawling on {response.url}")
        new_domains = self.get_new_domains(response)
        self.phoneNumberFieldDetectorFilter(response)
        self.saveNewDomains(new_domains)
        self.check_queue_size()

    def saveResponseToFile(self, response: HtmlResponse):
        url_hash = hashlib.md5(response.url.encode("utf-8")).hexdigest()
        directory = "responsestore"
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_path = os.path.join(directory, f"{url_hash}.html")
        with open(file_path, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved response to {file_path}")

    def updateVistStatus(self, link: str):
        session = get_session(self.engine)
        parsed_url = urlparse(link)
        clean_url = parsed_url.scheme + "://" + parsed_url.netloc + "/"
        try:
            record = (
                session.query(SearchEngineResponse).filter_by(url=clean_url).first()
            )
            if record:
                record.visited = True
                session.commit()
                self.logger.info(f"Updated UrlRecord: {record}")
            else:
                self.logger.info(f"No record found for URL: {clean_url}")
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Error updating UrlRecord: {e}")
        finally:
            session.close()

    def phoneNumberFieldDetectorFilter(self, response: HtmlResponse):
        telfield = response.xpath("//input[@type='tel']")
        if telfield:
            self.save_Goodurls(response.url)
            self.logger.info(f"Phone Number Field Found on: {response.url}")

    def get_new_domains(self, response: HtmlResponse):
        links = response.xpath("//a[contains(@href,'http')]/@href").getall()
        new_domains = set()
        for link in links:
            if get_domain_link(link) != get_domain_link(response.url):
                new_domains.add(get_domain_link(link))
        return list(new_domains)

    def visit_existing_links(self, response: HtmlResponse):
        same_domain_links = response.xpath(
            "//a[starts-with(@href, '/') or starts-with(@href, response.url)]/@href"
        ).getall()
        self.logger.info(f"[+] Links Count On Website: {len(same_domain_links)}")
        for link in same_domain_links:
            next_page = response.urljoin(link)
            if urlparse(next_page).scheme in ["http", "https"]:
                yield scrapy.Request(next_page, callback=self.level2_crawling)

    def saveNewDomains(self, urls: List[str]):
        self.logger.info(f"Saving new domains to database")
        self.save_urls(urls)

    def save_urls(self, urls: List[str]):
        session = get_session(self.engine)
        url_records = [CrawlerDiscovery(domain=url) for url in urls]
        newUrlCount = len(url_records)
        for url_record in url_records:
            try:
                session.add(url_record)
                session.commit()
            except IntegrityError:
                session.rollback()
                # self.logger.warning(f"Duplicate URL '{url_record.domain}' already exists in the database.")
                newUrlCount -= 1
            except Exception as e:
                session.rollback()
                self.logger.error(
                    f"Failed to save URL '{url_record.domain}' to the database: {e}"
                )
                raise e

        self.logger.info(f"{newUrlCount} new URLs saved to database.")
        session.close()

    def save_Goodurls(self, url):
        self.logger.info(f"Saving Good URL to database")
        session = get_session(self.engine)
        url_record = SitesWithTelField(domain=url)
        try:
            session.add(url_record)
            session.commit()
        except IntegrityError:
            session.rollback()
            # self.logger.warning(f"Duplicate URL '{url_record.domain}' already exists in the database.")
        except Exception as e:
            session.rollback()
            self.logger.error(
                f"Failed to save URL '{url_record.domain}' to the database: {e}"
            )
            raise e

        session.close()
