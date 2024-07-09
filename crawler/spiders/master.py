import scrapy
from sqlalchemy.orm import sessionmaker
from scrapy.http import HtmlResponse
from urllib.parse import urlparse
import logging
from Model import SearchEngineResponse, CrawlerDiscovery, SitesWithTelField, get_session, get_engine
from typing import List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import hashlib
import os
from CommonMethods import get_domain_link

class MasterSpider(scrapy.Spider):
    name = "master"

    def __init__(self, urls=None, *args, **kwargs):
        super(MasterSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []
        self.engine = get_engine()

    def parse(self, response: HtmlResponse):
        self.logger.info(f"Parsing response from {response.url}")
        new_domains = self.get_new_domains(response)
        self.phoneNumberFieldDetectorFilter(response)
        self.saveNewDomains(new_domains)
        yield from self.visit_existing_links(response)

    def level2_crawling(self, response: HtmlResponse):
        self.logger.info(f"Level 2 crawling on {response.url}")
        new_domains = self.get_new_domains(response)
        self.phoneNumberFieldDetectorFilter(response)
        self.saveNewDomains(new_domains)

    def saveResponseToFile(self, response: HtmlResponse):
        url_hash = hashlib.md5(response.url.encode('utf-8')).hexdigest()
        directory = "responsestore"
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_path = os.path.join(directory, f"{url_hash}.html")
        with open(file_path, 'wb') as f:
            f.write(response.body)

        self.logger.info(f"Saved response to {file_path}")

    def updateVistStatus(self, link: str):
        session = get_session(self.engine)
        parsed_url = urlparse(link)
        clean_url = parsed_url.scheme + "://" + parsed_url.netloc + "/"
        try:
            record = session.query(SearchEngineResponse).filter_by(url=clean_url).first()
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
        same_domain_links = response.xpath("//a[starts-with(@href, '/') or starts-with(@href, response.url)]/@href").getall()
        self.logger.info(f"[+] Links Count On Website: {len(same_domain_links)}")
        for link in same_domain_links:
            next_page = response.urljoin(link)
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
                self.logger.error(f"Failed to save URL '{url_record.domain}' to the database: {e}")
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
            self.logger.error(f"Failed to save URL '{url_record.domain}' to the database: {e}")
            raise e

        session.close()
