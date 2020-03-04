# -*- coding: utf-8 -*-
import scrapy
import re
from soufangwang.items import NewHouseItem,ESFHouseItem


class SfwSpider(scrapy.Spider):
    name = 'sfw'
    allowed_domains = ['fang.com']
    start_urls = ['https://www.fang.com/SoufunFamily.htm']

    def parse(self, response):
        trs = response.xpath('//div[@class="outCont"]//tr')
        province = None
        for tr in trs:
            tds = tr.xpath('.//td[not(@class)]')
            province_td = tds[0]
            province_text = province_td.xpath('.//text()').get()
            province_text = re.sub(r'\s', '', province_text)
            if province_text:
                province = province_text
            # 不爬取海外城市
            if province == '其它':
                continue
            city_td = tds[1]
            city_links = city_td.xpath('.//a')
            for city_link in city_links:
                city = city_link.xpath('.//text()').get()
                city_uri = city_link.xpath('.//@href').get()
                # 构建新房的url链接
                url_module = city_uri.split('//')
                scheme = url_module[0]
                domain = url_module[1]
                if 'bj.' in domain:
                    newhouse_url = 'https://newhouse.fang.com/house/s/'
                    esf_url = 'https://esf.fang.com/'
                else:

                    newhouse_url = scheme + '//' + 'newhouse.' + domain + 'house/s/'
                    # 构建二手房链接
                    esf_url = scheme + '//' + 'esf.' + domain
                yield scrapy.Request(url=newhouse_url, callback=self.parse_newhouse, meta={'info': (province, city)})
                yield  scrapy.Request(url=esf_url, callback=self.parse_esf, meta={'info': (province, city)})
            #     break
            # break

    def parse_newhouse(self, response):
        province,city = response.meta.get('info')
        lis = response.xpath('//div[contains(@class, "nl_con")]/ul/li')
        for li in lis:
            name = li.xpath('.//div[@class="nlcd_name"]/a/text()').get()
            if name is not None:
                name = name.strip()
            house_type_list = li.xpath('.//div[contains(@class, "house_type")]/a/text()').getall()
            # print(house_type_text)
            house_type_list = list(map(lambda x:re.sub(r'\s', '', x), house_type_list))
            rooms = list(filter(lambda x:x.endswith('居'), house_type_list))
            area = ''.join(li.xpath('.//div[contains(@class, "house_type")]/text()').getall())
            area = re.sub(r'\s|－|/', '', area)
            address = li.xpath('.//div[@class="address"]/a/@title').get()
            district_text = ''.join(li.xpath('.//div[@class="address"]/a//text()').getall())
            district = ''.join(re.findall(r'.*\[(.+)\].*', district_text))
            sale = li.xpath('.//div[contains(@class,"fangyuan")]/span/text()').get()
            price = ''.join(li.xpath('.//div[@class="nhouse_price"]//text()').getall())
            price = re.sub(r'\s|广告', '', price)
            origin_url = li.xpath('.//div[@class="nlcd_name"]/a/@href').get()
            origin_url = response.urljoin(origin_url)
            item = NewHouseItem(name=name, rooms=rooms, area=area, address=address, district=district, sale=sale, price=price,
                                origin_url=origin_url, province=province, city=city)
            yield item

        next_url = response.xpath('//div[@class="page"]//a[@class="next"]/@href').get()
        # print(next_url)
        if next_url:
            yield scrapy.Request(url=response.urljoin(next_url), callback=self.parse_newhouse, meta={'info': (province, city)})


    def parse_esf(self, response):
        # print(response.url)
        province,city = response.meta.get('info')
        item = ESFHouseItem(province=province, city=city)
        dls = response.xpath('//div/dl[contains(@id, "list")]')
        for dl in dls:
            name = ''.join(dl.xpath('./dd/p[@class="add_shop"]/a/text()').get())
            infos = dl.xpath('./dd/p[@class="tel_shop"]/text()').getall()
            infos = list(map(lambda x:re.sub(r'\s', '', x), infos))
            for info in infos:
                if '厅' in info:
                    item['rooms'] = info
                elif '向' in info:
                    item['toward'] = info
                elif '层' in info:
                    item['floor'] = info
                elif '㎡' in info:
                    item['area'] = info
                else:
                    item['year'] = info.replace('建筑年代：', '')
            address = dl.xpath('./dd/p[@class="add_shop"]/span/text()').get()
            item['address'] = address
            price = ''.join(dl.xpath('./dd[@class="price_right"]/span[@class="red"]//text()').getall())
            item['price'] = price
            unit = dl.xpath('./dd[@class="price_right"]/span[not(@class)]/text()').get()
            item['unit'] = unit
            origin_url = dl.xpath('./dd/h4[@class="clearfix"]/a/@href').get()
            item['origin_url'] = origin_url
            origin_url = response.urljoin(origin_url)
            yield item

        next_url = response.xpath('//div[@class="page_al"]/p[last()-2]/a/@href').get()
        yield scrapy.Request(url=response.urljoin(next_url), callback=self.parse_esf, meta={'info': (province, city)})


