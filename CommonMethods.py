from urllib.parse import urlparse

def get_domain_link(url: str) -> str:
    """
    Takes a URL as input and returns the domain link (scheme + netloc).
    
    Args:
    - url (str): The input URL.
    
    Returns:
    - str: The domain link.
    """
    parsed_url = urlparse(url)
    domain_link = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    return domain_link