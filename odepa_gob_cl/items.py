# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class odepa_gob_clItem(scrapy.Item):
	Title = scrapy.Field()
	Prod = scrapy.Field()
	Category = scrapy.Field()
	Price = scrapy.Field()
	url = scrapy.Field()
	City = scrapy.Field()
	Date = scrapy.Field()