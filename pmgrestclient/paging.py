from itertools import count

def get_all_from_pages(next_page):
    all_items = []
    for page_number in count(1):
        page, cont = next_page(page_number)
        all_items += page
        if not cont:
            return all_items
        
class Cache(object):
    def __init__(self, loader):
        self.cached_items = None
        self.loader = loader

    @property
    def items(self):
        if not self.cached_items:
            self.cached_items = self.loader()
        return self.cached_items

    def append(self, item):
        if self.cached_items:
            self.cached_items.append(item)




