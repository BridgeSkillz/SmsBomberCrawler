# import google.generativeai as genai
from rich import print

# genai.configure(api_key="AIzaSyA3CX_64j_C4AUAPH8BJL_GTyqLlNYDnOw")

# model = genai.GenerativeModel(model_name="gemini-1.5-flash",system_instruction="your taskis to take information from user and genrate multiple querie which are used to validate these facts on internet")
# response = model.generate_content("porshe accident in pune")
# print(response.text)

from duckduckgo_search import DDGS

results = DDGS().text("Reports of Porsche accidents in Pune", max_results=5)
print(results)