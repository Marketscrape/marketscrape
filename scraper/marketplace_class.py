import datetime
import re
import json
from .utils import *

class FacebookMarketplaceScraper:
    def __init__(self, mobile_soup, base_soup):
        self.mobile_soup = mobile_soup
        self.base_soup = base_soup

        script_tag = self.base_soup.find_all("script", {"type": "application/ld+json"})
        json_content = {}

        for script in script_tag:
            script_content=  script.string
            try:
                parsed_content = json.loads(script_content)
                json_content.update(parsed_content)
            except json.decoder.JSONDecodeError:
                pass
        
        self.json_content = json_content

    def get_listing_price(self) -> float:
        """
        Retrieves the price of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The price of the product listing as a float.
        """

        return self.json_content["offers"]["price"]

    def get_listing_title(self) -> str:
        """
        Retrieves the title of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The title of the product listing as a string.
        """

        return self.json_content["name"]
    
    def get_listing_description(self) -> str:
        """
        Retrieves the description of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The description of the product listing as a string.
        """

        return self.json_content['description']
    
    def get_listing_city(self) -> str:
        """
        Retrieves the city where a product is located.

        Args:
            self: The instance of the class.

        Returns:
            The city where the product is located as a string.
        """

        return self.json_content["itemListElement"][1]["name"]
    
    def get_listing_condition(self) -> str:
        """
        Retrieves the condition of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The condition of the product listing as a string.
        """

        # Item condition distribution based off of Mercari's dataset
        item_conditions = {
            "New": 43.21,
            "Used - Like New": 29.15,
            "Used - Good": 25.33,
            "Used - Fair": 2.16,
            "Refurbished": 0.15
        }

        schema = self.json_content["itemCondition"]
        if schema!= None and schema.replace("https://schema.org/", "") == "NewCondition":
            return "New"
        else:
            while True:
                condition = np.random.choice(list(item_conditions.keys()), p=[v/100 for v in item_conditions.values()])
                if condition != "New":
                    break
            return condition

    def get_listing_category(self) -> str:
        """
        Retrieves the category of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The category of the product listing as a string.
        """

        return self.json_content["itemListElement"][2]["name"]
    
    def get_listing_image(self) -> str:
        """
        Retrieves the image of a product listing.

        Args:
            self: The instance of the class.

        Returns:
            The URL of the image of the product listing as a string.
        """

        images = self.mobile_soup.find_all("img")
        image = [image["src"] for image in images if "https://scontent" in image["src"]]

        return image[0]
    
    def get_listing_date(self) -> tuple[int, int]:
        """
        Retrieves the listing date of a product.

        Args:
            self: The instance of the class.

        Returns:
            A tuple containing the number of days and hours since the listing was posted.
        """

        tag = self.mobile_soup.find('abbr')
        tag = tag.text.strip()

        try:
            month_str = re.search(r"[a-zA-Z]+", tag).group(0)
            month_num = datetime.datetime.strptime(month_str, '%B').month
        except ValueError:
            hour_str = re.search(r"[0-9]+", tag).group(0)
            return (0, int(hour_str))

        try:
            year_str = re.search(r"[0-9]{4}", tag).group(0)
        except AttributeError:
            year_str = datetime.datetime.now().year

        date_str = re.search(r"[0-9]+", tag).group(0)
        time_str = re.search(r"[0-9]+:[0-9]+", tag).group(0)
        am_pm_str = re.search(r"[A-Z]{2}", tag).group(0)

        formated_time = f'{time_str}:00 {am_pm_str}'
        formated_date = f'{year_str}-{month_num}-{date_str}'

        dt_str = f'{formated_date} {formated_time}'
        formated_dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %I:%M:%S %p')

        now = datetime.datetime.now()
        diff = now - formated_dt

        days = diff.days
        hours = diff.seconds // 3600

        return (days, hours)

    def is_listing_missing(self) -> bool:
        """
        Checks if a listing is missing.

        Args:
            self: The instance of the class.

        Returns:
            True if the listing is missing, otherwise False.
        """

        title_element = self.mobile_soup.find("title")
        title = title_element.get_text()

        text_to_find = "Buy and sell things locally on Facebook Marketplace."
        found = self.mobile_soup.find(string=text_to_find)

        if title.lower() == "page not found" or found:
            return True

        return False