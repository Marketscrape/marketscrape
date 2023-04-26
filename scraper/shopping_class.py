from .utils import *
from difflib import SequenceMatcher
import string

class GoogleShoppingScraper:
    def __init__(self):
        self.title = None 
        self.start = None
        self.soup = None

    def create_url(self):
        """
        Creates a URL to search for a product on Google Shopping and retrieves the corresponding page using BeautifulSoup.

        Args:
            self: The instance of the class.
            
        Returns:
            None
        """

        url = f"https://www.google.com/search?q={self.title}&tbs=vw:d&tbm=shop&sxsrf=APwXEdeCneQw6hWKHlHMJptjJHcIzqvmvw:1682209446957&ei=pnpEZILiOcmD0PEPifacgAw&start={self.start}&sa=N&ved=0ahUKEwiCzZfE3r7-AhXJATQIHQk7B8AQ8tMDCLEY&biw=1920&bih=927&dpr=1"
        headers = { 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
        }
        self.soup = create_soup(url, headers)

    def get_product_title(self) -> str:
        """
        Returns the product description in the soup.

        Args:
            soup: a BeautifulSoup object containing a product page

        Returns:
            The product description
        """

        description = self.soup.find_all("div", {"class": "rgHvZc"})

        return description

    def get_product_price(self) -> np.ndarray:
        """
        Extracts the price of each product from the HTML.

        Args:
            soup: The HTML to extract the price from.
            
        Returns:
            The price of each product. The price is represented as a
            NumPy array.
        """

        prices = self.soup.find_all("span", {"class": "HRLxBb"})

        values = []
        for price in prices:
            values.append(price.text)

        normalized = [re.sub("\$", "", price) for price in values]
        normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
        normalized = [float(price.replace(",", "")) for price in normalized]

        return normalized

    def get_product_url(self) -> str:
        """
        Returns the product URL in the soup.

        Args:
            soup: a BeautifulSoup object containing a product page

        Returns:
            The product URL
        """

        urls = self.soup.find_all("div", {"class": "rgHvZc"})

        values = []
        for url in urls:
            link = url.find('a', href=True)
            result = link['href'].replace('/url?url=', '')
            values.append(result)

        return values

    def get_similarity(self, string1: str, string2: str) -> float:
        """
        Compares two titles using the SequenceMatcher class from the difflib
        module. The similarity is returned as a float between 0 and 1.

        Args:
            string1: The first title.
            string2: The second title.

        Returns:
            The similarity between the two titles.
        """

        string1 = string1.lower().strip()
        string2 = string2.lower().strip()

        string1 = ' '.join(string1.split())
        string2 = ' '.join(string2.split())

        translator = str.maketrans('', '', string.punctuation)
        string1_clean = string1.translate(translator)
        string2_clean = string2.translate(translator)

        # Compute the similarity score using SequenceMatcher
        similarity = SequenceMatcher(None, string1_clean, string2_clean).ratio()

        return similarity
    
    def remove_outliers(self, titles: list[str], prices: list[float], urls: list[str]) -> tuple[list[str], list[float], list[str]]:
        """
        Removes outliers from a set of data consisting of titles, prices, and URLs.

        Args:
            titles (list[str]): A list of titles of the items.
            prices (list[float]): A list of prices of the items.
            urls (list[str]): A list of URLs of the items.

        Returns:
            A tuple of three lists: (1) titles with outliers removed, (2) prices with outliers removed, and (3) URLs with outliers removed.
        """

        outlier_indices = reject_outliers(np.array(prices), 1.25)

        titles = [title for i, title in enumerate(titles) if i not in outlier_indices]
        prices = [price for i, price in enumerate(prices) if i not in outlier_indices]
        urls = [url for i, url in enumerate(urls) if i not in outlier_indices]

        return titles, prices, urls

    def get_product_info(self):
        """
        Extracts product information from the page and returns a list of dictionaries.

        Each dictionary contains the following keys:
            - title: The title of the product.
            - description: The description of the product.
            - price: The price of the product.
            - url: The URL of the product.

        Args:
            soup (BeautifulSoup): The parsed HTML of the page.

        Returns:
            list: A list of dictionaries containing the product information.
        """

        titles = self.get_product_title()
        prices = self.get_product_price()
        urls = self.get_product_url()

        titles, prices, urls = self.remove_outliers(titles, prices, urls)

        product_info = []
        for title, price, url in zip(titles, prices, urls):
            product_info.append({
                'title': clean_text(title.text.lower()),
                'price': price,
                'url': url
            })

        return product_info

    def lowest_price_highest_similarity(self, filtered_prices_descriptions: dict) -> tuple[float, str, float]:
        """
        Finds the lowest price and the highest similarity of the filtered
        prices and descriptions.

        Args:
            filtered_prices_descriptions: The filtered prices and descriptions.

        Returns:
            The lowest price, the highest similarity, and the description
            associated with the highest similarity.
        """

        max_similarity_item = None
        min_price_item = None

        for _, item_details in filtered_prices_descriptions.items():
            if max_similarity_item is None and min_price_item is None:
                max_similarity_item = item_details
                min_price_item = item_details
            else:
                if item_details['similarity'] > max_similarity_item['similarity']:
                    max_similarity_item = item_details
                if item_details['price'] < min_price_item['price']:
                    min_price_item = item_details

        max_similar_items = [(item_name, item_details) for item_name, item_details in filtered_prices_descriptions.items() if item_details['similarity'] == max_similarity_item['similarity']]

        min_price_item = min(max_similar_items, key=lambda x: x[1]['price'])

        return min_price_item
        
    def construct_candidates(self, descriptions, prices, urls, similarities):
        """
        Constructs a list of candidates from the descriptions, prices, and
        urls.

        Args:
            descriptions: The descriptions of the products.
            prices: The prices of the products.
            urls: The urls of the products.

        Returns:
            The list of candidates.
        """

        candidates = {}
        for i in range(len(descriptions)):
            candidates[descriptions[i]] = {
                "price": prices[i],
                "url": urls[i],
                "similarity": similarities[i]
            }

        return candidates

    def find_viable_product(self, title: str, ramp_down: float) -> tuple[list[str], list[str], list[str], list[float]]:
        """
        Finds viable products based on the title of the Marketplace listing,
        and utilizes the ramp down of the previous product in the sequence, to 
        find the descriptions, prices, and urls of the prices of the product.

        Args:
            title: The title of the product.
            ramp_down: The ramp down of the previous product in the
                sequence.

        Returns:
            The descriptions, prices and urls the viable products.
        """

        descriptions = []
        prices = []
        urls = []
        similarities = []

        for page_number in range(5):
            start = page_number * 60
            similarity_threshold = 0.25
            self.title = title
            self.start = start
            self.create_url()

            try:
                filtered_prices_descriptions = self.listing_product_similarity(title, similarity_threshold)
                if not filtered_prices_descriptions:
                    raise NoProductsFound("No similar products found")
            except NoProductsFound:
                consecutively_empty = 0
                while not filtered_prices_descriptions:
                    ramp_down += 0.05
                    filtered_prices_descriptions = self.listing_product_similarity(title, similarity_threshold - ramp_down)
                    if consecutively_empty == 5:
                        break 

                    if filtered_prices_descriptions:
                        consecutively_empty = 0
                    else:
                        consecutively_empty +=1

            descriptions += list(filtered_prices_descriptions.keys())
            prices += [f"{product['price']:,.2f}" for product in filtered_prices_descriptions.values()]
            urls += [product['url'] for product in filtered_prices_descriptions.values()]
            similarities += [product['similarity'] for product in filtered_prices_descriptions.values()]

        return descriptions, prices, urls, similarities

    def filter_products_by_similarity(self, product_info: list, target_title: str, similarity_threshold: float):
        """
        Filters a list of products based on their similarity to a target product title.

        Args:
            product_info (list): A list of product dictionaries.
            target_title (str): The target product title to compare against.
            similarity_threshold (float): The minimum similarity ratio to consider a product similar.

        Returns:
            dict: A dictionary mapping the product ID to the product title.
        """
        filtered_products = {}
        for product in product_info:
            try:
                similarity = self.get_similarity(product['title'], target_title)
                if similarity < 0:
                    raise InvalidSimilarityThreshold("Similarity threshold must be between 0 and 1.")

                if similarity >= similarity_threshold:
                    filtered_products[product['title']] = {
                        'price': product['price'],
                        'url': product['url'],
                        'similarity': similarity
                    }
            except InvalidSimilarityThreshold:
                return filtered_products

        return filtered_products

    def listing_product_similarity(self, title: str, similarity_threshold: float) -> dict:
        """
        Returns a dictionary of all products listed on the page that are similar to the given title.

        Args:
            soup (BeautifulSoup): The parsed HTML of the page.
            title (str): The title of the product to compare against.
            similarity_threshold (float): The minimum similarity ratio to consider a product similar.

        Returns:
            dict: A dictionary mapping the product ID to the product title.
        """
        product_info = self.get_product_info()
        filtered_products = self.filter_products_by_similarity(product_info, title.lower(), similarity_threshold)

        return filtered_products