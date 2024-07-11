import time
import json
import logging
from typing import Dict, List
from Model import get_engine, get_session, SearchQuery
import google.generativeai as genai
import typing_extensions as typing
from sqlalchemy.exc import IntegrityError

genai.configure(api_key="AIzaSyA3CX_64j_C4AUAPH8BJL_GTyqLlNYDnOw")

# Setting up logging


class GeneratedQuery(typing.TypedDict):
    category: str
    subcategory: str
    query: str

# Decorator function for timing execution
def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"Execution time of {func.__name__}: {execution_time:.2f} seconds")
        return result
    return wrapper

class Gemini:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": list[GeneratedQuery]
            },
            system_instruction=""" 
        Your task is to generate queries that, when used on Google, primarily lead to websites that list or compare others within the same niche. Strictly provide output in the specified JSON format without any additional information or explanation.

        Using this JSON schema:
            GeneratedQuery = {
                "category": "category in which query lies",
                "subcategory": "subcategory for niche identification",
                "query": "generated query"
            }
        Return a `list[GeneratedQuery]`
        """
        )
        self.lastSeen = None
        self.logger = logging.getLogger(__name__)

    def generate_queries(self):
        self.newQueries = []
        self.chat = self.model.start_chat(history=[])
        queries = self.getResponseFromGemini("Generate 2 Query") #reduced it due to rate limit error
        self.QueryDuplicateValidation(queries)
        return self.newQueries

    def QueryDuplicateValidation(self, queries: List[Dict]):
        duplicateQueryList = []

        for data in queries:
            category = data.get('category', None)
            subcategory = data.get('subcategory', None)
            query = data.get('query', None)
            duplicate = self.saveSingleSearchQuery(category=category, subcategory=subcategory, query=query)
            if duplicate:
                duplicateQueryList.append(query)
        
        if duplicateQueryList:
            if len(self.newQueries) < 5:
                self.followup(duplicateQueryList)
            else:
                self.logger.warning(f"Requirement achieved, dropping {len(duplicateQueryList)} duplicate queries")

    def followup(self, duplicateQueryList):
        dup = ", ".join([f"'{query}'" for query in duplicateQueryList])
        prompt = f'{dup} these {len(duplicateQueryList)} I already have in my database, now strictly generate only {len(duplicateQueryList)} queries to complete the list of 5 unique queries'
        queries = self.getResponseFromGemini(prompt)
        self.logger.info(f"Response Count: {len(queries)}")
        
        if len(queries) > len(duplicateQueryList):
            queries = self.findNewQueriesFromResponse(queries, duplicateQueryList)
            self.logger.info(f"Processed Response: {queries}")
            self.logger.info(f"Processed Response Count: {len(queries)}")
        
        self.QueryDuplicateValidation(queries)

    def findNewQueriesFromResponse(self, newQueries: List[Dict], duplicateQueryList: List[str]):
        newQuery = []
        for data in newQueries:
            query = data.get('query', None)
            if query not in self.newQueries:
                newQuery.append(data)
        return newQuery

    @timeit
    def getResponseFromGemini(self, prompt: str):
        self.logger.info(f"Query: '{prompt}'")
        response = self.chat.send_message(prompt)
        queries = json.loads(response.text)
        self.logger.info(f"Response: {queries}")
        self.lastSeen = time.time()
        return queries

    def saveSingleSearchQuery(self, category: str, subcategory: str, query: str, comment: str = None):
        engine = get_engine()
        with get_session(engine) as session:
            try:
                new_query = SearchQuery(
                    category=category,
                    subcategory=subcategory,
                    query=query,
                    comment=comment
                )

                session.add(new_query)
                session.commit()
                self.newQueries.append(query)
            except IntegrityError as ie:
                session.rollback()
                self.logger.error(f"IntegrityError: {ie}")
                return True
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error: {e}")
                return True
        return False

# Instantiate Gemini class and run the process
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gemini = Gemini()
    newQueries = gemini.generate_queries()
    logging.info("_" * 200)
