from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.common.action_chains import ActionChains
import selenium.common.exceptions
import json
import csv
import time
import re
import numpy as np
import pymysql.cursors
from functools import reduce
import traceback

def str2int(s):
    def fn(x,y):
        return x*10+y
    def char2num(s):
        return {'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9}[s]
    return reduce(fn,map(char2num,s))
class JdSpider():
    def open_browser(self):
        self.browser = webdriver.Chrome()
        self.browser.implicitly_wait(10)
        self.wait = WebDriverWait(self.browser,10)

    def init_variable(self):
        
        self.isLast = False
        self.beginpage=''
        self.endpage=''
    def parse_shop(self,link):
        js='window.open'+"('"+link+"')"
        self.browser.execute_script(js)#打开新窗口
        self.browser.switch_to.window(self.browser.window_handles[-1])#切换到新的标签页


        idlist=re.findall(r'\b\d+\b',link)
        id=str(idlist[0])+'/'+str(idlist[1])#根据链接提取datas后的id

        print('正在爬取ID为'+id+'商品的数据')

        name=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//h1[@class="fl"]')))#爬名称
        name=[item.text for item in name]
        name=name[0]
        newprice={}
        try:
            price=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//span[@class="price-num"]')))
            price=[item.get_attribute('innerText') for item in price]#忽略不可见，爬全部价格
            price=[item for item in price]
            if(price[0]=='免费'):#免费的商品一般会有次数限制
                num=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//span[@class="mianfei-tag"]')))
                num=[item.text for item in num]
                newprice={price[0]:num[0]}
            else:
                num=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[contains(@class,"price-times one-item")]')))
                num=[item.text for item in num]
                newnum=[]
                for item in num:#爬多少钱可以买多少
                    if(re.search(r'\d',item)):
                        newnum.append(re.search(r"\d+\.?\d*",str(item)).group())#不看后面的约等于，只取前面的
                        if("万" in item):
                            newnum[-1]+='0000'#把汉字万换成10000乘上去
                    else:
                        newnum.append(item)#不含数字，/周/月这样的
                num=newnum
                index=0
                for item in price:
                    newprice[str(re.search(r'\d+',item).group())]=str(num[index])
                    index-=-1
        except selenium.common.exceptions.TimeoutException:#遇到特殊商品了，此时商品规格就是价格
            num=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[contains(@class,"price-times one-item")]')))
            num=[item.text for item in num]
            newnum=[]
            
            for item in num:#爬多少钱可以买多少
                if(re.search(r'\d',item)):
                    newnum.append(re.search(r"\d+\.?\d*",str(item)).group())#不看后面的约等于，只取前面的
                    if("万" in item):
                        newnum[-1]+='0000'#把汉字万换成10000乘上去
                else:
                    newnum.append(item)#不含数字，/周/月这样的
            num=newnum
            for item in newnum:
                newprice[item]=str(item)
            
        
        jprice=json.dumps(newprice)#将dic转化为json格式的数据
        company=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//span[@class="blue"]')))
        company=[item.text for item in company]
        company=company[0]
        view=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//ul[@class="operation-list"]/li[1]')))
        view=[item.text for item in view]
        #views.append(re.search(r'\d+',view[0]).group())#爬浏览
        view=str2int(re.search(r'\d+',view[0]).group())
        buy=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//ul[@class="operation-list"]/li[2]')))
        buy=[item.text for item in buy]
        #buys.append(re.search(r'\d+',buy[0]).group())#爬购买次数
        buy=str2int(re.search(r'\d+',buy[0]).group())
        collection=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[@id="add-fav"]/a/li')))
        collection=[item.text for item in collection]
        #collections.append(re.search(r'\d+',collection[0]).group())#爬收藏
        collection=str2int(re.search(r'\d+',collection[0]).group())
        tag=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//ul[@class="info-list cl"]/li[2]')))
        tag=[item.text for item in tag]
        tag=tag[0]
        flag=0;
        newword=''
        newtag=[]

        for word in tag:
            if(flag==1):
                if(word!='\u2003'):
                    newword=newword+word
                else:
                    flag=0
                    newtag.append(newword)
                    newword=''
            if(flag==0):
                if(word=='\n'or word==' '):
                    flag=1;

        newtag.append(newword)#将tag储存在list中
        jtag=json.dumps(newtag,ensure_ascii=False)#list转json
        shop=[link,name,jprice,company,view,buy,collection,jtag]
        if(SQLOS.InsertShop(shop)==0):
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            return 1
        
        ishistorylast=0
        try:
            self.wait.until(EC.element_to_be_clickable((By.XPATH,'//li[@id="detailTab6"]'))).click()

        except selenium.common.exceptions.NoSuchElementException:
            print('id为'+id+'的商品无购买记录')
            ishistorylast=1
        except selenium.common.exceptions.TimeoutException:
            print('id为'+id+'的商品无购买记录')
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            return 0
        customers=[]
        dates=[]
        types=[]
        newid=[]
        count=0
        while (ishistorylast!=1):

            try:
                time.sleep(1)
                customer=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[@class="order-lst script-order-list"]/table/tbody/tr/td[1]')))
                customer=[item.text for item in customer]
                date=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[@class="order-lst script-order-list"]/table/tbody/tr/td[2]')))
                date=[item.text for item in date]
                typess=self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[@class="order-lst script-order-list"]/table/tbody/tr/td[3]')))
                typess=[item.text for item in typess]
                customers+=customer
                dates+=date
                types+=typess
                count-=-1
                print('    正在爬取 '+name+' 的第 '+str(count)+' 页订单记录')
                for i in range(0,len(customer)):
                    newid.append(id)


            except selenium.common.exceptions.NoSuchElementException:
                ishistorylast=1
            except selenium.common.exceptions.TimeoutException:
                ishistorylast=1
            except selenium.common.exceptions.StaleElementReferenceException:
                self.wait.until(EC.element_to_be_clickable((By.XPATH,'//li[@id="detailTab6"]'))).click()

            try:
                time.sleep(1)
                self.wait.until(EC.element_to_be_clickable((By.XPATH,'//a[@title="下一页"]'))).click()
            except selenium.common.exceptions.NoSuchElementException:
                print(1)
                ishistorylast=1
            except selenium.common.exceptions.TimeoutException:
                print(2)
                ishistorylast=1
        history=zip(newid,customers,dates,types)
        SQLOS.InsertHistory(list(history))
        
        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[0])

    def parse_page(self):
        try:
            time.sleep(1)
            skus = self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//li[@class="boder_v1"]')))
            skus = [item.find_element_by_css_selector('a').get_attribute('href') for item in skus]
            links = skus#首页商品链接
            for link in links:
                self.parse_shop(link)
                
        except selenium.common.exceptions.TimeoutException:
            print('parse_page: TimeoutException')
            self.parse_page()
        except selenium.common.exceptions.StaleElementReferenceException:
            print('parse_page: StaleElementReferenceException')
            self.browser.refresh()

    def turn_page(self):
        try:
            next_btn=self.wait.until(EC.element_to_be_clickable((By.XPATH,'//a[@title="下一页"]')))
            self.browser.execute_script("arguments[0].click();", next_btn)
            time.sleep(1)
            self.browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(2)
        except selenium.common.exceptions.NoSuchElementException:
            self.isLast = True
        except selenium.common.exceptions.TimeoutException:
            print('turn_page: TimeoutException')
            self.isLast = True
        except selenium.common.exceptions.StaleElementReferenceException:
            print('turn_page: StaleElementReferenceException')
            self.browser.refresh()
    
 
    def close_browser(self):
        self.browser.quit()

    
    def crawl(self):
        self.open_browser()
        self.init_variable()
        print('请输入起始页码')
        self.beginpage=input()
        print('请输入终止页码')
        self.endpage=input()
        print('开始爬取')
        self.browser.get('https://wx.jdcloud.com/api/2_0/'+str(self.beginpage))
        time.sleep(1)
        self.browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        time.sleep(2)
        count =str2int(self.beginpage)
        while not (count==self.endpage or self.isLast==True):
            count += 1
            print('正在爬取第 ' + str(count) + ' 页......')
            self.parse_page()
            self.turn_page()
        self.close_browser()
        print('结束爬取')

class SQLOS():
    def __init__(self):
        pass
    
    def Connect_to_DB():
        connection = pymysql.connect(host='rm-bp10wr08s7nl319dcyo.mysql.rds.aliyuncs.com',
                        user='jdwx_user',
                        password='5^5*RUhD0QyQopX6',
                        db='jdwxasset',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor)
        return connection#链接服务器 返回一个connect
    def InsertShop(shop):
        db=SQLOS.Connect_to_DB()
        cursor=db.cursor()
        if cursor.execute("SELECT * from d_shoppinglist WHERE `link`=%s",shop[0]):#已经有了该商品的记录
            db.close()
            print('商品链接为'+shop[0]+'的商品已有记录')
            return 0
        else:
            try:
                cursor.execute("INSERT INTO d_shoppinglist (`link`,`name`,`price`,`company`,`view`,`buy`,`collection`,`tag`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(shop[0],shop[1],shop[2],shop[3],shop[4],shop[5],shop[6],shop[7]))
                print("INSERT INTO d_shoppinglist (`link`,`name`,`price`,`company`,`view`,`buy`,`collection`,`tag`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(shop[0],shop[1],shop[2],shop[3],shop[4],shop[5],shop[6],shop[7]))

                db.commit()
                db.close()
                return 1
            except Exception as e:
                print(str(e))
                print(e.message)
                print('traceback.print_exc():',traceback.print_exc())
                
                print(1)
                db.rollback()
                db.close()
                return 0
    def InsertHistory(history):
        db=SQLOS.Connect_to_DB()
        cursor=db.cursor()
        if cursor.execute("SELECT * from d_historylist WHERE `shopid`=%s",history[0][0]):#已经有了该商品的记录
            db.close()
            print('商品ID为'+history[0][0]+'的商品已有记录')
            return 0
        else:
            try:
                for item in history:
                    print("INSERT INTO d_historylist(`shopid`,`customer`,`dates`,`type`) VALUES(%s,%s,%s,%s)",(item[0],item[1],item[2],item[3]))
                    cursor.execute("INSERT INTO d_historylist(`shopid`,`customer`,`dates`,`type`) VALUES(%s,%s,%s,%s)",(item[0],item[1],item[2],item[3]))
                    
                db.commit()
                db.close()
                return 1
            except Exception as e:
                print(str(e))
                print(e.message)
                print('traceback.print_exc():',traceback.print_exc())
                
                print(2)
                db.rollback()
                db.close()
                return 0
            
if __name__ == '__main__':
    spider = JdSpider()
    spider.crawl()
