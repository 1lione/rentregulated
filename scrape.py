#!/usr/bin/env python3.5
import sys
import csv
import re
import argparse
import random
import time
import requests
from bs4 import BeautifulSoup

LIB = 'html.parser'
ENDPOINT = 'https://apps.hcr.ny.gov/buildingsearch/'
AJAX_HEAD = {
    'X-MicrosoftAjax': 'Delta=true',
    'X-Requested-With': 'XMLHttpRequest'
}


def sleep():
    time.sleep(random.uniform(0.1, 1.0))


def dumb_params(soup):
    '''Find these params in a blob of digusting aspx'''
    fields = '__VIEWSTATE', '__EVENTVALIDATION', '__VIEWSTATEGENERATOR', '__VIEWSTATEENCRYPTED'
    params = {f: soup.find(attrs={'name': f}).attrs['value'] for f in fields}

    params['__EVENTARGUMENT'] = ''
    params['__LASTFOCUS'] = ''

    return params


def construct_soup(text):
    '''Hackily construct HTML from the joke pipe-delimited XHR'''
    fields = 'VIEWSTATE', 'EVENTVALIDATION', 'VIEWSTATEGENERATOR', 'VIEWSTATEENCRYPTED'
    vals = dict()

    for f in fields:
        match = re.search(r'__' + f + r'\|([^|]*)\|', text)
        vals[f] = match.groups()[0] if match else ''

    document = '''{} <input value="{VIEWSTATE}" name="__VIEWSTATE" />
        <input value="{EVENTVALIDATION}" name="__EVENTVALIDATION" />
        <input value="{VIEWSTATEGENERATOR}" name="__VIEWSTATEGENERATOR" />
        <input value="{VIEWSTATEENCRYPTED}" name="__VIEWSTATEENCRYPTED" />'''

    html = document.format(text, **vals)
    return BeautifulSoup(html, LIB)


def writerows(writer, soup):
    '''Extract fields from "table.grid" in soup and write to writer.'''
    table = soup.find('table', attrs={'class': 'grid'})

    if table is None:
        raise RuntimeError('Missing table')

    for tr in table.find_all('tr'):
        if tr.td is None or tr.td.attrs.get('colspan') == 7:
            continue

        if 'Displaying buildings ' in str(tr):
            continue

        writer.writerow([
            re.sub(r'\s+', ' ', td.text.strip(' \r\n')) for td in tr.find_all('td')
        ])


def prepare(session):
    '''Make initial page requests, establishing session.'''
    session.headers.update({
        'User-Agent': "Mozilla (scraper bike) Gecko Chrome Safari",
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Origin': 'https://apps.hcr.ny.gov',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://apps.hcr.ny.gov/buildingsearch/default.aspx',
    })

    # request page, get session cookie
    r = session.get(ENDPOINT)
    soup = BeautifulSoup(r.text, LIB)
    session.headers.update({
        'Cookie': 'ASP.NET_SessionId=' + session.cookies['ASP.NET_SessionId']
    })
    sleep()

    # poke zip code button
    param = dumb_params(soup)
    param.update({
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$zipCodeSearchLinkButton',
        'ctl00$ContentPlaceHolder1$countyDropDown': '',
    })
    sleep()

    r = session.post(ENDPOINT, data=param)

    if len(r.history) > 1:
        print('history too long (1)', file=sys.stderr)
        r = session.post(ENDPOINT, data=param)

    return BeautifulSoup(r.text, LIB)


def firstpage(session, county, zipcode):
    '''Get the first page of results.'''
    basic = {
        'ctl00$ContentPlaceHolder1$countyListDropDown': county,
        'ctl00$ContentPlaceHolder1$zipCodesDropDown': zipcode,
        '__EVENTTARGET': '',
    }
    county_params = {
        'ctl00$ContentPlaceHolder1$countyListDropDown': county,
        'ctl00$ContentPlaceHolder1$zipCodesDropDown': '',
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$countyListDropDown',
        '__ASYNCPOST': 'true',
        'ctl00$ContentPlaceHolder1$ScriptManager1': (
            'ctl00$ContentPlaceHolder1$ScriptManager1|'
            'ctl00$ContentPlaceHolder1$countyListDropDown'
        ),
    }
    zip_params = {
        'ctl00$ContentPlaceHolder1$submitZipCodeButton': 'Submit',
    }

    zip_params.update(basic)

    print('starting', zipcode, file=sys.stderr)
    soup = prepare(session)

    # select county from dropdown list
    county_params.update(dumb_params(soup))
    print('selecting county:', county, file=sys.stderr)
    request = session.post(ENDPOINT, data=county_params, headers=AJAX_HEAD)

    if len(request.history) > 1:
        print('history too long (2)', file=sys.stderr)
        request = session.post(ENDPOINT, data=county_params, headers=AJAX_HEAD)

    # decode parameters out of nasty nonsense
    # easiest way is to make another soup object
    soup = construct_soup(request.text)

    print('getting initial results', file=sys.stderr)
    zip_params.update(dumb_params(soup))
    request = session.post(ENDPOINT, data=zip_params)

    # Sometimes page errs, sets of a chain of redirects that end nowhere interesting.
    if len(request.history) > 1:
        print('history too long (3)', file=sys.stderr)
        request = session.post(ENDPOINT, data=zip_params)

    return request.text


def count(session, county, zipcode):
    '''Extract the count of results in a ZIP code from the first results page.'''
    text = firstpage(session, county, zipcode)

    if re.search('0 results found', text):
        buildings = 0

    else:
        match = re.search(r'Displaying buildings \d+ - \d+ of (\d+)', text)
        buildings = match.groups()[0]

    print('{},{},{}'.format(county, zipcode, buildings))


def scrape(session, county, zipcode):
    '''Iterate through results, saving them.'''
    next_params = {
        "ctl00$ContentPlaceHolder1$ScriptManager1": (
            "ctl00$ContentPlaceHolder1$gridUpdatePanel|"
            'ctl00$ContentPlaceHolder1$buildingsGridView$ctl54$btnNext'
        ),
        'ctl00$ContentPlaceHolder1$buildingsGridView$ctl54$btnNext': "Next",
        '__ASYNCPOST': 'true',
        'ctl00$ContentPlaceHolder1$countyListDropDown': county,
        'ctl00$ContentPlaceHolder1$zipCodesDropDown': zipcode,
        '__EVENTTARGET': '',
    }

    # get first page of results
    text = firstpage(session, county, zipcode)

    if re.search('0 results found', text):
        print('0 buildings found in', zipcode, file=sys.stderr)
        return

    match = re.search(r'Displaying buildings \d+ - \d+ of (\d+)', text)
    print(match.groups()[0], 'buildings found in', zipcode, file=sys.stderr)

    soup = BeautifulSoup(text, LIB)

    writer = csv.writer(sys.stdout, lineterminator='\n')

    # Write first page of results
    writerows(writer, soup)

    # get further results for zip code
    next_button = re.search(r'value="Next"', text)

    sleep()

    while next_button:
        next_params.update(dumb_params(soup))

        request = session.post(ENDPOINT, data=next_params, headers=AJAX_HEAD)
        soup = construct_soup(request.text)

        try:
            writerows(writer, soup)

        except RuntimeError:
            # Redo the request and try again (once)
            request = session.post(ENDPOINT, data=next_params, headers=AJAX_HEAD)
            soup = construct_soup(request.text)
            writerows(writer, soup)

        next_button = re.search(r'value="Next"', request.text)
        sleep()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('county', type=str)
    parser.add_argument('zipcode', type=str)
    parser.add_argument('--action', default='scrape', choices=('scrape', 'count'))

    args = parser.parse_args()

    county = args.county.replace('NEWYORK', 'NEW YORK')

    with requests.Session() as session:
        if args.action == 'scrape':
            scrape(session, county, args.zipcode)

        elif args.action == 'count':
            count(session, county, args.zipcode)

if __name__ == '__main__':
    main()
