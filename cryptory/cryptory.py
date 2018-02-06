

# python 2
try:
    from urllib.request import Request, urlopen  
# Python 3
except ImportError:
    from urllib2 import Request, urlopen

import pandas as pd
import time
import datetime
import numpy as np
import re
import json
from bs4 import BeautifulSoup
from pytrends.request import TrendReq

class Cryptory():
    
    def __init__(self, from_date, to_date=None, ascending=False, 
                 fillgaps=True, timeout=10.0):
        """Initialise cryptory class
        
        Parameters
        ----------
        from_date : the starting date (as string) for the returned data;
            required format is %Y-%m-%d (e.g. "2017-06-21")
        to_date : the end date (as string) for the returned data;
            required format is %Y-%m-%d (e.g. "2017-06-21")
            Optional. If unspecified, it will default to the current day
        to_date : binary. Determines whether the returned dataframes are
            ordered by date in ascending or descending order 
            (defaults to False i.e. most recent first)
        fillgaps : binary. When data does not exist (e.g. weekends for stocks)
            should the rows be filled in with the previous available data
            (defaults to True e.g. Saturday stock price will be same as Friday)
        fillgaps : float. The max time allowed (in seconds) to pull data from a website
            If exceeded, an timeout error is returned. Default is 10 seconds.
        """
        
        self.from_date = from_date
        # if to_date provided, defaults to current date
        if to_date is None:
            self.to_date = datetime.date.today().strftime("%Y-%m-%d")
        else:
            self.to_date = to_date
        self.ascending = ascending
        self.fillgaps = fillgaps
        self.timeout = timeout
        self._df = pd.DataFrame({'date':pd.date_range(start=self.from_date, end=self.to_date)})
        
    def extract_reddit_metrics(self, subreddit, metric, col_label="", sub_col=False):
        """Retrieve daily subscriber data for a specific subreddit scraped from redditmetrics.com
        
        Parameters
        ----------
        subreddit : the name of subreddit (e.g. "python", "learnpython")
        metric : the particular subscriber information to be retrieved
            (options are limited to "subscriber-growth" (daily change), 
            'total-subscribers' (total subscribers on a given day) and 
            'rankData' (the position of the subreddit on reddit overall)
            'subscriber-growth-perc' (daily percentage change in subscribers))
        col_label : specify the title of the value column
            (it will default to the metric name with hyphens replacing underscores)
        sub_col : whether to include the subreddit name as a column
            (default is False i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        """
        if metric not in ['subscriber-growth', 'total-subscribers', 'rankData', 'subscriber-growth-perc']:
            raise ValueError(
                "Invalid metric: must be one of 'subscriber-growth', " + 
                "'total-subscribers', 'subscriber-growth-perc', 'rankData'")
        url = "http://redditmetrics.com/r/" + subreddit
        if metric == 'subscriber-growth-perc':
            metric_name = 'total-subscribers'
        else:
            metric_name = metric
        try: 
            parsed_page = urlopen(url, timeout=self.timeout).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        if metric == 'rankData':
            start_segment = parsed_page.find(metric)
        else:
            start_segment = parsed_page.find("element: '"+metric_name+"'")
        if start_segment != -1:
            start_list = parsed_page.find("[", start_segment)
            end_list = parsed_page.find("]", start_list)
            parsed_page = parsed_page[start_list:end_list + 1]
        else:
            return pd.DataFrame({"error":"Could not find that subreddit"}, index=[0])
        parsed_page = parsed_page.replace("'", '"')
        parsed_page = parsed_page.replace('a', '\"subscriber_count\"')
        parsed_page = parsed_page.replace('y', '\"date\"')
        output = json.loads(parsed_page)
        output = pd.DataFrame(output)
        output['date'] = pd.to_datetime(output['date'], format="%Y-%m-%d")
        if metric == 'subscriber-growth-perc':
            output['subscriber_count'] = output['subscriber_count'].pct_change()
        output = output[(output['date']>=self.from_date) & (output['date']<=self.to_date)]
        output = output.sort_values(by='date', ascending=self.ascending).reset_index(drop=True)
        if sub_col:
            output['subreddit'] = subreddit
        if col_label != "":
            output = output.rename(columns={'subscriber_count': label})
        else:
            output = output.rename(columns={'subscriber_count': metric.replace("-","_")})
        return output
        
    def extract_coinmarketcap(self, coin, coin_col=False):
        """Retrieve basic historical information for a specific cryptocurrency from coinmarketcap.com
        
        Parameters
        ----------
        coin : the name of the cryptocurrency (e.g. 'bitcoin', 'ethereum', 'dentacoin')
        coin_col : whether to include the coin name as a column
            (default is False i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        """
        try:
            output = pd.read_html("https://coinmarketcap.com/currencies/{}/historical-data/?start={}&end={}".format(
                coin, self.from_date.replace("-", ""), self.to_date.replace("-", "")))[0]
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        output = output.assign(Date=pd.to_datetime(output['Date']))
        for col in output.columns:
            if output[col].dtype == np.dtype('O'):
                output.loc[output[col]=="-",col]=0
                output[col] = output[col].astype('int64')
        output.columns = [col.lower() for col in output.columns]
        if coin_col:
            output['coin'] = coin
        return output
    
    def extract_bitinfocharts(self, coin, metric="price", coin_col=False, metric_col=False):
        """Retrieve historical data for a specific cyrptocurrency scraped from bitinfocharts.com
        
        Parameters
        ----------
        coin : the code of the cryptocurrency (e.g. 'btc' for bitcoin)
            full range of available coins can be found on bitinfocharts.com
        metric : the particular coin information to be retrieved
            (options are limited to those listed on bitinfocharts.com
            including 'price', 'marketcap', 'transactions' and 'sentinusd'
        coin_col : whether to include the coin name as a column
            (default is False i.e. the column is not included)
        metric_col : whether to include the metric name as a column
            (default is False i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        """
        if coin not in ['btc', 'eth', 'xrp', 'bch', 'ltc', 'dash', 'xmr', 'btg', 'etc', 'zec', 
                        'doge', 'rdd', 'vtc', 'ppc', 'ftc', 'nmc', 'blk', 'aur', 'nvc', 'qrk', 'nec']:
            raise ValueError("Not a valid coin")
        if metric not in ['transactions', 'size', 'sentbyaddress', 'difficulty', 'hashrate', 'price', 
                          'mining_profitability', 'sentinusd', 'transactionfees', 'median_transaction_fee', 
                        'confirmationtime', 'marketcap', 'transactionvalue', 'mediantransactionvalue',
                         'tweets', 'activeaddresses', 'top100cap']:
            raise ValueError("Not a valid bitinfocharts metric")
        new_col_name = "_".join([coin, metric])
        parsed_page = Request("https://bitinfocharts.com/comparison/{}-{}.html".format(metric, coin),
                            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'})
        try: 
            parsed_page = urlopen(parsed_page, timeout=self.timeout).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        start_segment = parsed_page.find("new Dygraph")
        if start_segment != -1:
            start_list = parsed_page.find('[[', start_segment)
            end_list = parsed_page.find(']]', start_list)
            parsed_page = parsed_page[start_list:end_list]
        else:
            return pd.DataFrame({"error":"Could not find the appropriate text tag"}, index=[0])
        parsed_page = parsed_page.replace('new Date(', '')
        parsed_page = parsed_page.replace(')', '')
        parsed_page = parsed_page.replace('null', '0')
        parsed_page = parsed_page.replace('["', '{"date":"')
        parsed_page = parsed_page.replace('",', '","{}":'.format(new_col_name))
        parsed_page = parsed_page.replace('],', '},')
        parsed_page = parsed_page + '}]'
        output = json.loads(parsed_page)
        output = pd.DataFrame(output)
        output['date'] = pd.to_datetime(output['date'], format="%Y-%m-%d")
        output = output[(output['date']>=self.from_date) & (output['date']<=self.to_date)]
        # for consistency, put date column first
        output = output[['date', new_col_name]]
        if coin_col:
            output['coin'] = coin
        if metric_col:
            output['metric'] = metric
        return output.sort_values(by='date', ascending=self.ascending).reset_index(drop=True)
    
    def extract_poloniex(self, coin1, coin2, coin1_col=False, coin2_col=False):
        """Retrieve the historical price of one coin relative to another (currency pair) from poloniex
        
        Parameters
        ----------
        coin1 : the code of the denomination cryptocurrency 
            (e.g. 'btc' for prices in bitcoin)
        coin2 : the code for the coin for which prices are retrieved
            (e.g. 'eth' for ethereum)
        coin1_col : whether to include the coin1 code as a column
            (default is False i.e. the column is not included)
        coin2_col : whether to include the coin2 code as a column
            (default is False i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        """
            
        from_date = int(time.mktime(time.strptime(self.from_date, "%Y-%m-%d")))
        to_date = int(time.mktime(time.strptime(self.to_date, "%Y-%m-%d")))
        url = "https://poloniex.com/public?command=returnChartData&currencyPair={}_{}&start={}&end={}&period=86400".format(
                coin1.upper(), coin2.upper(), from_date, to_date)
        try: 
            parsed_page = urlopen(url, timeout=self.timeout).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        output = json.loads(parsed_page)
        if isinstance(output, dict):
            if 'error' in list(output.keys()):
                return pd.DataFrame(output, index=[0])
        output = pd.DataFrame(output)
        # more intuitive column order
        output = output[['date', 'close', 'open', 'high', 'low', 
                        'weightedAverage', 'quoteVolume', 'volume']]
        output['date'] = pd.to_datetime(output['date'], unit='s')
        output = output.sort_values(by='date', ascending=self.ascending).reset_index(drop=True)
        if coin1_col:
            output['coin1'] = coin1
        if coin2_col:
            output['coin2'] = coin2
        return output
    
    def get_exchange_rates(self, from_currency="USD", to_currency="EUR", 
                                 from_col=False, to_col=False):
        """Retrieve the historical exchange rate between two (fiat) currencies
        
        Parameters
        ----------
        from_currency : the from currency or the currency of denomination (e.g. 'USD')
        to_currency : the currency to which you wish to exchange (e.g. 'EUR')
        from_col : whether to include the from_currency code as a column
            (default is False i.e. the column is not included)
        to_col : whether to include the to_currency code as a column
            (default is False i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        """
        n_days = (datetime.date.today() - 
                  datetime.datetime.strptime(self.from_date, "%Y-%m-%d").date()).days + 1
        url = "https://www.indexmundi.com/xrates/graph.aspx?c1={}&c2={}&days={}".format(
            from_currency, to_currency, n_days)
        try: 
            parsed_page = urlopen(url, timeout=self.timeout).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        start_segment = parsed_page.find("chart xAxisName")
        if start_segment != -1:
            start_list = parsed_page.find("<", start_segment)
            end_list = parsed_page.find("/></chart>", start_list)
            parsed_page = parsed_page[start_list:end_list]
        else:
            return pd.DataFrame({"error":"Could not find the appropriate text tag"}, index=[0])
        parsed_page = re.sub(r" showLabel='[0-9]'", "", parsed_page)
        parsed_page = parsed_page.replace("'", '"')
        parsed_page = parsed_page.replace("set ", '')
        parsed_page = parsed_page.replace("<", "{")
        parsed_page = parsed_page.replace("/>", "},")
        parsed_page = parsed_page.replace('label', '\"date\"')
        parsed_page = parsed_page.replace('value', '\"exch_rate\"')
        parsed_page = parsed_page.replace('=', ':')
        parsed_page = parsed_page.replace(' ', ',')
        output = json.loads('[' + parsed_page + '}]')
        output = pd.DataFrame(output)
        output['date'] = pd.to_datetime(output['date'], format="%m/%d/%Y")
        output['exch_rate'] = pd.to_numeric(output['exch_rate'], errors='coerce')
        if from_col:
            output['from_currency'] = from_currency
        if to_col:
            output['to_currency'] = to_currency
        output = self._merge_fill_filter(output)
        return output
    
    def get_stock_prices(self, market, market_name=None):
        """Retrieve the historical price (or value) of a publically listed stock or index
        
        Parameters
        ----------
        market : the code of the stock or index (see yahoo finance for examples)
            ('%5EDJI' refers to the Dow Jones and '%5EIXIC' pulls the Nasdaq index)
        market_name : specify an appropriate market name or label (under the market_name column)
            the default is None (default is None i.e. the column is not included)
            
        Returns
        -------
        pandas Dataframe
        
        Notes
        -----
        This method scrapes data from yahoo finance, so it only works when the historical
        data is presented on the site (which is not the case for a large number of stocks/indices).
        """
        from_date = int(time.mktime(time.strptime(self.from_date, "%Y-%m-%d")))
        # we want the daily data
        # this site works off unix time (86400 seconds = 1 day)
        to_date = int(time.mktime(time.strptime(self.to_date, "%Y-%m-%d"))) + 86400
        url = "https://finance.yahoo.com/quote/{}/history?period1={}&period2={}&interval=1d&filter=history&frequency=1d".format(
        market, from_date,  to_date)
        try: 
            parsed_page = urlopen(url, timeout=1).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        start_segment = parsed_page.find('{\"prices\":')
        if start_segment != -1:
            start_list = parsed_page.find("[", start_segment)
            end_list = parsed_page.find("]", start_list)
            parsed_page = parsed_page[start_list:end_list+1]
        else:
            return pd.DataFrame({"error":"Could not find the appropriate text tag"}, index=[0])
        output = json.loads(parsed_page)
        output = pd.DataFrame(output)
        output['date'] = pd.to_datetime(output['date'],unit='s').apply(lambda x: x.date())
        output['date'] = pd.to_datetime(output['date'])
        if market_name is not None:
            output['market_name'] = market_name
        output = self._merge_fill_filter(output)
        return output
    
    def get_oil_prices(self):
        """Retrieve the historical oil price (London Brent crude)
        
        Parameters
        ----------
            
        Returns
        -------
        pandas Dataframe
        
        Notes
        -----
        This site seems to take significantly longer than the others to scrape
        If you get timeout errors, then increase the timeout argument when
        you initalise the cryptory class
        """
        try: 
            parsed_page = urlopen("https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=D",
                                          timeout=self.timeout).read()
            parsed_page = parsed_page.decode("utf8")
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        souped_page = BeautifulSoup(parsed_page, 'html.parser')
        souped_values = [soups.text for soups in souped_page.findAll("td", {"class": "B3"})]
        souped_dates = [datetime.datetime.strptime(
                re.sub('\xa0\xa0| to .*','', soups.text), '%Y %b-%d') 
                        for soups in souped_page.findAll("td", {"class": "B6"})]
        output = []
        for i in range(5):
            output.append(pd.DataFrame({"date":[date + datetime.timedelta(days=i) 
                                                for date in souped_dates],
                           "oil_price":souped_values[i::5]}))
        output = pd.concat(output)
        output.loc[output['oil_price']=="",'oil_price']=np.nan
        output['oil_price'] = pd.to_numeric(output['oil_price'])
        output = self._merge_fill_filter(output)
        return output
    
    def get_metal_prices(self):
        """Retrieve the historical price of gold, silver, platinum and palladium
        
        Parameters
        ----------
            
        Returns
        -------
        pandas Dataframe
        """
            
        current_year = datetime.datetime.now().year
        from_year = datetime.datetime.strptime(self.from_date, "%Y-%m-%d").year
        to_year = datetime.datetime.strptime(self.to_date, "%Y-%m-%d").year
        if to_year is None:
            to_year = current_year
        output = []
        for i in range(from_year, to_year+1):
            if i==current_year:
                output.append(pd.read_html("http://www.kitco.com/gold.londonfix.html")[-1])
            else:
                output.append(pd.read_html("http://www.kitco.com/londonfix/gold.londonfix"+
                                       str(i)[-2:]+".html")[-1])
        output = pd.concat(output).dropna()
        output.columns = ['date', 'gold_am', 'gold_pm','silver', 'platinum_am', 
                          'platinum_pm', 'palladium_am', 'palladium_pm']
        output = output.assign(date=pd.to_datetime(output['date']))
        for col in output.select_dtypes(include=['object']):
            output.loc[output[col]=="-",col]=np.nan
            output[col] = output[col].astype('float64')
        output = pd.merge(self._df, output, on="date", how="left")
        if self.fillgaps:
            for old_val, new_val in zip(['gold_am', 'gold_pm', 'platinum_am', 'platinum_pm',
                                         'palladium_am', 'palladium_pm'],
                                       ['gold_pm', 'gold_am', 'platinum_pm', 'platinum_am',
                                         'palladium_pm', 'palladium_am']):
                output.loc[output[old_val].isnull(), old_val]= output.loc[output[old_val].isnull(), 
                                                                          new_val]
            output = output.fillna(method='ffill')
        output = output.sort_values(by='date', ascending=self.ascending).reset_index(drop=True)
        output = output[(output['date']>=self.from_date) & (output['date']<=self.to_date)]
        return output
    
    def get_google_trends(self, kw_list, trdays=250, overlap=100, 
                          cat=0, geo='', tz=360, gprop='', hl='en-US',
                          sleeptime=1, isPartial_col=False, 
                          from_start=False, scale_cols=True):
        """Retrieve daily google trends data for a list of search terms
        
        Parameters
        ----------
        kw_list : list of search terms (max 5)- see pyTrends for more details
        trdays : the number of days to pull data for in a search
            (the max is around 270, though the website seems to indicate 90)
        overlap : the number of overlapped days when stitching two searches together
        cat : category to narrow results - see pyTrends for more details
        geo : two letter country abbreviation (e.g 'US', 'UK') 
            default is '', which returns global results - see pyTrends for more details
        tz : timezone offset
            (default is 360, which corresponds to US CST - see pyTrends for more details)
        grop : filter results to specific google property
            available options are 'images', 'news', 'youtube' or 'froogle'
            default is '', which refers to web searches - see pyTrends for more details
        hl : language (e.g. 'en-US' (default), 'es') - see pyTrends for more details
        sleeptime : when stiching multiple searches, this sets the period between each
        isPartial_col : remove the isPartial column 
            (default is True i.e. column is removed)
        from_start : when stitching multiple results, this determines whether searches
            are combined going forward or backwards in time
            (default is False, meaning searches are stitched with the most recent first)
        scale_cols : google trend searches traditionally returns scores between 0 and 100
            stitching could produce values greater than 100
            by setting this to True (default), the values will range between 0 and 100
        
        Returns
        -------
        pandas Dataframe
        
        Notes
        -----
        This method is essentially a highly restricted wrapper for the pytrends package
        Any issues/questions related to its use would probably be more likely resolved
        by consulting the pytrends github page
        https://github.com/GeneralMills/pytrends
        """
        
        if len(kw_list)>5 or len(kw_list)==0:
            raise ValueError("The keyword list can contain at most 5 words")
        if trdays>270:
            raise ValueError("trdays must not exceed 270")
        if overlap>=trdays:
            raise ValueError("Overlap can't exceed search days")
        stich_overlap = trdays - overlap
        from_date = datetime.datetime.strptime(self.from_date, '%Y-%m-%d')
        to_date = datetime.datetime.strptime(self.to_date, '%Y-%m-%d')
        n_days = (to_date - from_date).days
        # launch pytrends request
        _pytrends = TrendReq(hl=hl, tz=tz)
        # get the dates for each search
        if n_days <= trdays:
            trend_dates = [' '.join([self.from_date, self.to_date])]
        else:
            trend_dates = ['{} {}'.format(
            (to_date - datetime.timedelta(i+trdays)).strftime("%Y-%m-%d"),
            (to_date - datetime.timedelta(i)).strftime("%Y-%m-%d")) 
                           for i in range(0,n_days-trdays+stich_overlap,
                                          stich_overlap)]
        if from_start:
            trend_dates = trend_dates[::-1]
        try:
            _pytrends.build_payload(kw_list, cat=cat, timeframe=trend_dates[0], 
                                   geo=geo, gprop=gprop)
        except Exception as e:
            return pd.DataFrame({"error":e}, index=[0])
        output = _pytrends.interest_over_time().reset_index()
        if len(output)==0:
            return pd.DataFrame({"error":'search term returned no results (insufficient data)'}, index=[0])
        for date in trend_dates[1:]:
            time.sleep(sleeptime)
            try:
                _pytrends.build_payload(kw_list, cat=cat, timeframe=date, 
                                         geo=geo, gprop=gprop)
            except Exception as e:
                return pd.DataFrame({"error":e}, index=[0])
            temp_trend = _pytrends.interest_over_time().reset_index()
            temp_trend = temp_trend.merge(output, on="date", how="left")
            # it's ugly but we'll exploit the common column names
            # and then rename the underscore containing column names
            for kw in kw_list:
                norm_factor = np.ma.masked_invalid(temp_trend[kw+'_y']/temp_trend[kw+'_x']).mean()
                temp_trend[kw] = temp_trend[kw+'_x'] * norm_factor
            temp_trend =  temp_trend[temp_trend.isnull().any(axis=1)]
            temp_trend['isPartial'] = temp_trend['isPartial_x']
            output = pd.concat([output, temp_trend[['date', 'isPartial'] + kw_list]], axis=0)
        
        # reorder columns in alphabetical order
        output = output[['date', 'isPartial']+kw_list]
        
        if not isPartial_col:
            output = output.drop('isPartial', axis=1)
        output = output[output['date']>=self.from_date]
        if scale_cols:
            # the values in each column are relative to other columns
            # so we need to get the maximum value across the search columns
            max_val = float(output[kw_list].values.max())
            for col in kw_list:
                output[col] = 100.0*output[col]/max_val
        output = output.sort_values('date', ascending=self.ascending).reset_index(drop=True)
        return output

    
    def _merge_fill_filter(self, other_df):
        output = pd.merge(self._df, other_df, on="date", how="left")
        output = output.sort_values(by='date', ascending=self.ascending).reset_index(drop=True)
        if self.fillgaps:
            if self.ascending:
                output = output.fillna(method='ffill')
            else:
                output = output.fillna(method='bfill')
        output = output[(output['date']>=self.from_date) & (output['date']<=self.to_date)]
        return output
