import asyncio
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from loggingConfig import setup_logging
from DuckDuckGo import DuckDuckGo
from GeminiQueryGenerator import Gemini
from crawler.spiders.master import MasterSpider
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Instantiate classes
gemini = Gemini()
duckDuckGo = DuckDuckGo()

# List to store links
LinksToVisit = []

def run_spider(urls):
    """
    Create a CrawlerProcess instance and start the spider with provided URLs.
    """
    logger.info("Starting the spider with URLs: %s", urls)
    
    # Create a CrawlerProcess instance with your project settings
    process = CrawlerProcess(get_project_settings())

    # Start the spider with the provided URLs
    process.crawl(MasterSpider, urls=urls)

    # Start the crawling process
    process.start()

async def main():
    """
    Main function to generate queries, fetch results and update LinksToVisit.
    """
    global LinksToVisit
    try:
        # Generate new queries
        newQueries = gemini.generate_queries()
        logger.info("Generated new queries: %s", newQueries)
        
        # Request results
        LinksToVisit = await duckDuckGo.requestResults(newQueries)
    except Exception as e:
        logger.error("An error occurred in main function: %s", e)

# Run the main function in a loop
while True:
    asyncio.run(main())
    logger.info("Links to visit: %s", LinksToVisit)
    run_spider(urls=LinksToVisit)

    
