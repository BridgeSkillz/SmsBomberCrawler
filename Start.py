import logging
from scrapy.crawler import CrawlerProcess
from loggingConfig import setup_logging
from crawler.spiders.UpdatedSuperCrawler import SuperSpider
from twisted.internet import reactor
from scrapy.utils.project import get_project_settings
# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create a CrawlerRunner instance
process = CrawlerProcess(get_project_settings())

# Run the spider
process.crawl(SuperSpider)

process.start()
