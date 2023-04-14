import datetime
import re
from .utils import *

class FacebookScraper:
    def __init__(self, mobile_soup, base_soup):
        self.mobile_soup = mobile_soup
        self.base_soup = base_soup

    def get_listing_price(self) -> str:
        spans = self.mobile_soup.find_all("span")

        free = [span.text for span in spans if "free" in span.text.lower()]
        if (free):
            return free

        price = [str(span.text) for span in spans if "$" in span.text][0]

        return price
    
    def get_listing_image(self) -> list[str]:
        images = self.mobile_soup.find_all("img")
        image = [image["src"] for image in images if "https://scontent" in image["src"]]

        return image

    def get_listing_title(self) -> str:
        title = self.base_soup.find("meta", {"name": "DC.title"})
        title_content = title["content"]

        return title_content
    
    def get_listing_date(self) -> tuple[int, int]:
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

    def get_listing_description(self) -> str:
        description = self.base_soup.find("meta", {"name": "DC.description"})
        description_content = description["content"]

        return clean_text(description_content)

    def is_listing_missing(self) -> bool:
        title_element = self.mobile_soup.find("title")
        title = title_element.get_text()

        text_to_find = "Buy and sell things locally on Facebook Marketplace."
        found = self.mobile_soup.find(string=text_to_find)

        if title.lower() == "page not found" or found:
            return True

        return False