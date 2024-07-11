import scrapy
from scrapy.http import HtmlResponse
from urllib.parse import urlparse

URLS_TO_TEST = [
    "https://www.boat-lifestyle.com/",
    # "https://classplusapp.com/",
    # "https://paytm.com/",
    # "https://apna.co",
    # "https://razorpay.com/",
    # "https://upgrad.com",
    # "https://www.delhivery.com",
    # "https://www.1mg.com/",
    # "https://gomechanic.in/",
]

class MasterSpider(scrapy.Spider):
    name = "Test"
    domains_with_mobile_field = set()

    def __init__(self, urls=None, *args, **kwargs):
        super(MasterSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else URLS_TO_TEST

    def start_requests(self):
        for url in self.start_urls:
            if urlparse(url).scheme == "https":
                domain = urlparse(url).netloc
                if domain not in self.domains_with_mobile_field:
                    yield scrapy.Request(url, callback=self.parse)

    def parse(self, response: HtmlResponse):
        domain = urlparse(response.url).netloc
        if domain in self.domains_with_mobile_field :
            self.logger.info(f"Skipping {response.url} as it has a detected field")
            return

        self.field_detector(response)
        self.logger.info(f"Parsing response from {response.url}")

        same_domain_links = self.get_same_domain_links(response)
        
        for link in same_domain_links:
            next_page = response.urljoin(link)
            print(next_page)
            if urlparse(next_page).netloc not in self.domains_with_mobile_field:
                yield scrapy.Request(next_page, callback=self.parse)

    def get_same_domain_links(self, response: HtmlResponse):
        domain = urlparse(response.url).netloc
        links = response.xpath("//a[starts-with(@href, '/') or starts-with(@href, response.url)]/@href").getall()
        same_domain_links = [link for link in links if urlparse(link).netloc in [domain, '']]
        self.logger.info(f"[+] Links Count On Website: {len(same_domain_links)}")

        return same_domain_links
 
    def field_detector(self, response):
        if (self.phone_number_field_detector(response) or
            self.tel_field_detector(response) or
            self.input_field_detector(response) or
            self.number_field_detector(response)):
            
            domain = urlparse(response.url).netloc
            self.logger.info(f"Detected field at {response.url}")
            self.domains_with_mobile_field.add(domain)
            print("DETECTED on" + domain)


    def phone_number_field_detector(self, response: HtmlResponse):
        return response.xpath("//input[@type='tel']").get() is not None

    def tel_field_detector(self, response: HtmlResponse):
        return response.xpath("//a[contains(@href, 'tel:')]").get() is not None

    def input_field_detector(self, response: HtmlResponse):
        return response.xpath("//input[contains(@name, 'phone') or contains(@name, 'mobile')]").get() is not None

    def number_field_detector(self, response: HtmlResponse):
        return response.xpath("//input[@type='number' and @max and @min and @pattern='[0-9]*']").get() is not None

    # def is_valid_link(self, link, domain):
    #     parsed_link = urlparse(link)
    #     # Valid schemes are empty, 'http', or 'https'
    #     if parsed_link.scheme not in ['http', 'https']:
    #         return False
    #     # Ensure the link is within the same domain or is a relative link
    #     if parsed_link.netloc and parsed_link.netloc != domain:
    #         return False
    #     # Check if the link starts with 'javascript:'
    #     if parsed_link.scheme == 'javascript':
    #         return False
    #     return True