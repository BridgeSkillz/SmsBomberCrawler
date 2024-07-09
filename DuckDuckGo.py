import asyncio
import logging
from duckduckgo_search import AsyncDDGS
from duckduckgo_search.exceptions import RatelimitException, DuckDuckGoSearchException
from Model import SearchEngineResponse, get_session, get_engine
from CommonMethods import get_domain_link
from typing import List, Dict
from sqlalchemy.exc import IntegrityError
import random

class DuckDuckGo:
    def __init__(self):
        self.Headers = {
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
        }
        self.engine = get_engine()
        self.logger = logging.getLogger(__name__)
    
    async def DuckDuckGoResponse(self, query: str):
        GotResponse = False
        time = 0
        Attempt = 1
        while not GotResponse:
            try:
                results = await AsyncDDGS(proxy=None).atext(query, max_results=100)
                GotResponse = True
                self.logger.info(f"Query '{query}' succeeded on attempt {Attempt}")
            except RatelimitException as rle:
                time += random.randint(10, 20)
                self.logger.warning(f"{Attempt} RatelimitException: Waiting for {time} sec")
                await asyncio.sleep(time)
            except DuckDuckGoSearchException as e:
                time += random.randint(10, 20)
                self.logger.warning(f"{Attempt} DuckDuckGoSearchException: Waiting for {time} sec")
                await asyncio.sleep(time)
            Attempt += 1
        return results
    
    async def requestResults(self, Queries: List[str]):
        tasks = [self.DuckDuckGoResponse(query) for query in Queries]
        result = await asyncio.gather(*tasks)
        ResultToStore = [post for resp in result for post in resp]
        LinksTovisit = self.StoreResultInDb(ResultToStore)
        return LinksTovisit
    
    def StoreResultInDb(self, Response: List[Dict]) -> List[str]:
        self.newQueries = []
        for post in Response:
            title = post.get("title", None)
            href = post.get("href", None)
            domain = get_domain_link(href)
            desc = post.get("body", None)
            self.saveSingleSearchQuery(title, domain, href, desc)
        
        return self.newQueries

    def saveSingleSearchQuery(self, title: str, domain: str, href: str, desc: str, comment: str = None):
        engine = get_engine()
        with get_session(engine) as session:
            try:
                new_query = SearchEngineResponse(
                    title=title,
                    domain=domain,
                    href=href,
                    desc=desc,
                    comment=comment
                )

                session.add(new_query)
                session.commit()
                self.newQueries.append(domain)
                self.logger.info(f"Saved query: {title} - {domain}")
            except IntegrityError as ie:
                session.rollback()
                self.logger.warning(f"IntegrityError: {ie}")
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error: {e}")

async def main():
    words = ["github", "stackoverflow"]
    se = DuckDuckGo()
    data = await se.requestResults(words)
    logging.info(f"Results: {data}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
