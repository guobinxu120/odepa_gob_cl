# -*- coding: utf-8 -*-
import scrapy
import csv
import re
import sys

from collections import OrderedDict
# reload(sys)
# sys.setdefaultencoding('utf8')

from odepa_gob_cl import settings
from odepa_gob_cl.items import odepa_gob_clItem

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.utils.response import open_in_browser
import datetime

class odepa_gob_clSpider(scrapy.Spider):
	name = "odepa_gob_cl_monthly"
	start_urls = ["https://www.profeco.gob.mx/precios/canasta/homer.aspx"]

	def __init__(self, *args, **kwargs):
		super(odepa_gob_clSpider, self).__init__(*args, **kwargs)

	def start_requests(self):
		form_data = {"tipoSerie":{"glosa":"Mensual","code":"MONTH"},
					 "agno":{"glosa":2019,"code":2019},
					 "semanaInicio":{"glosa":6,"code":6},
					 "semanaTermino":{"glosa":6,"code":6},
					 "fechaInicio":"2013-12-31T16:00:00.000Z",
					 "fechaTermino":"2018-12-31T16:00:00.000Z",
					 "region":{"id":13,"glosa":"Región Metropolitana de Santiago","glosaCorta":"Metropolitana","region":None,"orden":7},
					 "sector":{"value":-2,"glosa":"Todos (agrupado)","id":None,"tooltip":"Todos (agrupado)","valor":None},
					 "tipoProducto":{"id":11,"glosa":"Aceite"},
					 "producto":[{"id":349,"label":"Maravilla"}],
					 "tipoPuntoMonitoreo":[{"id":1,"label":"Supermercado"}],
					 "tipoPeso":"reales","ipc":{"valor":"6084","glosa":"12/2018"},
					 "tipoProductoCalibreSegunda":True,"tipoProductoCalibrePrimera":True}


		yield scrapy.FormRequest('https://aplicativos.odepa.gob.cl/precio-consumidor/serie-precio/find-serie-precio', self.parse, formdata=form_data)

	def parse(self, response):
		cities = ['141401','150901','212101']
		view = response.xpath('//*[@id="__VIEWSTATE"]/@value').extract_first()
		validate = response.xpath('//*[@id="__EVENTVALIDATION"]/@value').extract_first()
		for city in cities:
			rq = scrapy.FormRequest.from_response(
				response,
					formdata={
						'__EVENTTARGET':'cmbCiudad',
						'__EVENTARGUMENT':'',
						'__LASTFOCUS':'',
						'__VIEWSTATE':view,
						'__VIEWSTATEGENERATOR':'3850611A',
						'__EVENTVALIDATION':validate,
						'cmbCiudad':city,
						}, method='POST',
						callback=self.parse_municipalities, dont_filter=True
				)
			rq.meta['city'] = city
			yield rq
			
	def parse_municipalities(self, response):
		city = response.meta['city']
		view = response.xpath('//*[@id="__VIEWSTATE"]/@value').extract_first()
		validate = response.xpath('//*[@id="__EVENTVALIDATION"]/@value').extract_first()
		yield scrapy.FormRequest(
			response.url,
				formdata={
					'__EVENTTARGET':'',
					'__EVENTARGUMENT':'',
					'__LASTFOCUS':'',
					'__VIEWSTATE':view,
					'__VIEWSTATEGENERATOR':'3850611A',
					'__EVENTVALIDATION':validate,
					'cmbCiudad':city,
					'listaMunicipios':city + '0',
					'ImageButton1.x':'51',
					'ImageButton1.y':'8',
					},
					callback=self.parse_category, dont_filter=True, meta={'city': city}
			)
			
	def parse_category(self, response):
		headers = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"}
		yield scrapy.Request('https://www.profeco.gob.mx/precios/canasta/arbol_frame.aspx', headers=headers, callback=self.parse_category_again, dont_filter=True, meta=response.meta)
		
	def parse_category_again(self, response):
		numbers = ['1','2','3','5']
		for i in numbers:
			for sel in response.xpath('//*[@id="Arbol"]'):
				for Category in sel.xpath('./table[' + i + ']//tr/td[2]/span/text()').extract():
					pass
					# print 'cccccccccccc', Category
			for cat in response.xpath('//*[@id="Arbol"]/table[' + i + ']/following-sibling::div[1]/table'):
				for Sub_Category in cat.xpath('.//tr/td[@class="textos_nodos Arbol_2"]/span/text()').extract():
					# print 'ssssssssssss', Sub_Category
					for Sub_Category1 in cat.xpath('./following-sibling::div[1]/table//tr/td[last()]/span/text()').extract():
						# print '11111111111', Sub_Category1
						for Product_Name in response.xpath('//span[contains(.,"' + str(Sub_Category1) + '")]/following::div[1]/table//tr/td[last()]/a'):
							url = Product_Name.xpath('./@href').extract_first()
							Sub_Category2 = Product_Name.xpath('./text()').extract_first()
							# print 'PPppppppppppp', Product_Name.encode('utf-8')
							rq = scrapy.Request(response.urljoin(url), callback=self.parse_Prod, dont_filter=True, )
							rq.meta['Category'] = Category
							rq.meta['Sub_Category'] = Sub_Category
							rq.meta['Sub_Category1'] = Sub_Category1
							rq.meta['Sub_Category2'] = Sub_Category2
							rq.meta['city'] = response.meta['city']
							yield rq
							
	def parse_Prod(self, response):

		Category = response.meta['Category']
		Sub_Category = response.meta['Sub_Category']
		Sub_Category1 = response.meta['Sub_Category1']
		Sub_Category2 = response.meta['Sub_Category2']
		Prod = response.xpath('//*[@id="lbltitulo2"]/text()').extract_first()
		result_list = []
		total_price = 0.0
		count = 0
		for i, sel in enumerate(response.xpath('//*[@id="GridView1"]//tr')):
			if i == 0: continue
			items = OrderedDict()
			items['Prod'] = Prod
			items['Category'] = Category + '>' + Sub_Category + '>' + Sub_Category1 + '>' + Sub_Category2
			Title = sel.xpath('./td[3]/a/text()').extract_first()
			items['Title'] = Title
			Price = sel.xpath('./td[last()]/text()').extract_first()
			items['Price'] = Price.replace('$','').replace(',','')
			total_price += float(items['Price'])
			items['Average'] = ''
			url = response.url
			items['url'] = url
			city = response.meta['city']
			if city == '141401':
				items['City'] = 'Guadalajara'
			elif city == '150901':
				items['City'] = 'Ciudad de Mexico y Area Metropolitana'
			elif city == '212101':
				items['City'] = 'Puebla'

			items['Date'] = datetime.datetime.today().strftime('%Y-%m-%d')
			count+=1
			result_list.append(items)

		average_price = round(total_price / (count), 2)
		for item in result_list:
			item['Average'] = average_price
			yield item


		# Title = response.xpath('//*[@id="GridView1"]//tr/td[3]/a/text()').extract_first()
		# items['Title'] = Title
		# Price = response.xpath('//*[@id="GridView1"]//tr/td[last()]/text()').extract_first()
		# items['Price'] = Price
		# url = response.url
		# items['url'] = url
		# city = response.meta
		# yield items
			