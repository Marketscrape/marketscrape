from .utils import *
from difflib import SequenceMatcher
import string

class EbayScraper:
    def __init__(self):
        self.title = None 
        self.start = None
        self.soup = None

    def create_url(self):
        """
        Creates a URL to search for a product on Ebay and retrieves the corresponding page using BeautifulSoup.

        Args:
            self: The instance of the class.
            
        Returns:
            None
        """

        url = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={self.title}&_sacat=0&_ipg=240&_pgn={self.start}"
        headers = { 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582",
            "Referer": "https://www.google.com/"
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

        description = self.soup.find_all('div', class_='s-item__title')

        return description

    def get_product_price(self) -> list[float]:
        """
        Extracts the price of each product from the HTML.

        Args:
            soup: The HTML to extract the price from.
            
        Returns:
            The price of each product. 
        """

        prices = self.soup.find_all('span', class_='s-item__price')

        values = []
        for price in prices:
            values.append(price.text)

        cleansed = [re.search(r"([0-9]+\.[0-9]+)|([0-9]+,[0-9]+)", price).group(0) for price in values]
        cleansed = [price.replace(",", "") for price in cleansed]
        cleansed = [float(price) for price in cleansed]

        return cleansed
    
    def get_product_condition(self) -> list[str]:
        """
        Extracts the conditions of each product from the HTML

        Args:
            soup: The HTML to extract the condition from.

        Returns:
            The condition of each product. The conditions is represented as a
        """

        conditions = self.soup.find_all('span', class_='SECONDARY_INFO')

        values = []
        for condition in conditions:
            values.append(condition.text)

        return values
    
    def get_product_shipping(self) -> list[float]:
        """
        Extracts the shipping cost of each product from the HTML.

        Args:
            soup: The HTML to extract the shipping cost from.
            
        Returns:
            The shipping cost of each product.
        """

        shipping = self.soup.find_all('span', class_='s-item__shipping s-item__logisticsCost')

        values = []
        for ship in shipping:
            values.append(ship.text)
        
        cleansed = [re.search(r"([0-9]+\.[0-9]+)|(Free)|(not specified)", ship).group(0) for ship in values]
        cleansed = [float(ship) if ship not in ["Free", "not specified"] else 0.0 for ship in cleansed]

        return cleansed

    def get_product_country(self) -> str:
        """
        Returns the product country in the soup.

        Args:
            soup: a BeautifulSoup object containing a product page

        Returns:
            The product country
        """

        countries = self.soup.find_all('span', class_='s-item__location s-item__itemLocation')

        values = []
        for country in countries:
            result = country.text.replace("from ", "")
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
    
    def remove_outliers(self, titles: list[str], prices: list[float], shipping: list[float], countries: list[str], conditions: list[str]) -> tuple[list[str], list[float], list[float], list[str]]:
        """
        Removes outliers from a set of data consisting of titles, prices, and countries.

        Args:
            titles (list[str]): A list of titles of the items.
            prices (list[float]): A list of prices of the items.
            shipping (list[float]): A list of shipping costs of the items.
            countries (list[str]): A list of countries of the items.

        Returns:
            A tuple of three lists: (1) titles with outliers removed, (2) prices with outliers removed, and (3) countries with outliers removed.
        """

        # Minimum number of items required to start removing outliers
        removal_threshold = 100

        if len(titles) >= removal_threshold:
            outlier_indices = reject_outliers(np.array(prices), m=1.5)

            titles = [title for i, title in enumerate(titles) if i not in outlier_indices]
            prices = [price for i, price in enumerate(prices) if i not in outlier_indices]
            shipping = [ship for i, ship in enumerate(shipping) if i not in outlier_indices]
            countries = [country for i, country in enumerate(countries) if i not in outlier_indices]
            conditions = [condition for i, condition in enumerate(conditions) if i not in outlier_indices]

        return titles, prices, shipping, countries, conditions

    def get_product_info(self):
        """
        Extracts product information from the page and returns a list of dictionaries.

        Each dictionary contains the following keys:
            - title: The title of the product.
            - description: The description of the product.
            - price: The price of the product.
            - country: The country of the product.

        Args:
            soup (BeautifulSoup): The parsed HTML of the page.

        Returns:
            list: A list of dictionaries containing the product information.
        """

        titles = self.get_product_title()
        prices = self.get_product_price()
        shipping = self.get_product_shipping()
        countries = self.get_product_country()
        conditions = self.get_product_condition()

        titles, prices, shipping, countries, conditions = self.remove_outliers(titles, prices, shipping, countries, conditions)

        product_info = []
        for title, price, ship, country, condition in zip(titles, prices, shipping, countries, conditions):
            product_info.append({
                'title': clean_text(title.text.lower()),
                'price': price,
                'shipping': ship,
                'country': country,
                'condition': condition
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
        
    def construct_candidates(self, descriptions, prices, shipping, countries, conditions, similarities):
        """
        Constructs a list of candidates from the descriptions, prices, and
        countries.

        Args:
            descriptions: The descriptions of the products.
            prices: The prices of the products.
            shipping: The shipping costs of the products.
            countries: The countries of the products.

        Returns:
            The list of candidates.
        """

        candidates = {}
        for i in range(len(descriptions)):
            candidates[descriptions[i]] = {
                "price": prices[i],
                "shipping": shipping[i],
                "country": countries[i],
                "condition": conditions[i],
                "similarity": similarities[i]
            }

        return candidates

    def find_viable_product(self, title: str, ramp_down: float) -> tuple[list[str], list[str], list[str], list[float]]:
        """
        Finds viable products based on the title of the Marketplace listing,
        and utilizes the ramp down of the previous product in the sequence, to 
        find the descriptions, prices, and countries of the prices of the product.

        Args:
            title: The title of the product.
            ramp_down: The ramp down of the previous product in the
                sequence.

        Returns:
            The descriptions, prices and countries the viable products.
        """

        descriptions = []
        prices = []
        shipping = []
        countries = []
        conditions = []
        similarities = []

        for page_number in range(5):
            similarity_threshold = 0.35
            self.title = title
            self.start = page_number
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
                    if consecutively_empty == 2:
                        break 

                    if filtered_prices_descriptions:
                        consecutively_empty = 0
                    else:
                        consecutively_empty += 1

            descriptions += list(filtered_prices_descriptions.keys())
            prices += [f"{product['price']:,.2f}" for product in filtered_prices_descriptions.values()]
            shipping += [f"{product['shipping']:,.2f}" for product in filtered_prices_descriptions.values()]
            countries += [product['country'] for product in filtered_prices_descriptions.values()]
            conditions += [product['condition'] for product in filtered_prices_descriptions.values()]
            similarities += [product['similarity'] for product in filtered_prices_descriptions.values()]

        return descriptions, prices, shipping, countries, conditions, similarities

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
                        'shipping': product['shipping'],
                        'country': product['country'],
                        'condition': product['condition'],
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