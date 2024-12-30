#!/usr/bin/env python3

import sys
import re
import csv
import time
import random
import argparse

# Dependency installation function
def install_dependencies():
    try:
        import subprocess
        print("Installing required dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "requests"])
    except subprocess.CalledProcessError:
        print("Failed to install dependencies. Please install them manually.")
        sys.exit(1)

# Check for required dependencies
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing required dependencies. Attempting to install them...")
    install_dependencies()
    import requests
    from bs4 import BeautifulSoup

LIB = 'html.parser'
ENDPOINT = 'https://apps.hcr.ny.gov/buildingsearch/'
AJAX_HEAD = {
    'X-MicrosoftAjax': 'Delta=true',
    'X-Requested-With': 'XMLHttpRequest'
}

def sleep():
    """Pause for a random interval to avoid detection."""
    time.sleep(random.uniform(0.1, 1.0))

def dumb_params(soup):
    """Extract parameters from the HTML form."""
    fields = ['__VIEWSTATE', '__EVENTVALIDATION', '__VIEWSTATEGENERATOR', '__VIEWSTATEENCRYPTED']
    params = {f: soup.find(attrs={'name': f}).attrs.get('value', '') for f in fields}
    params['__EVENTARGUMENT'] = ''
    params['__LASTFOCUS'] = ''
    return params

def construct_soup(text):
    """Construct a BeautifulSoup object from the response text."""
    fields = ['VIEWSTATE', 'EVENTVALIDATION', 'VIEWSTATEGENERATOR', 'VIEWSTATEENCRYPTED']
    vals = {}
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
    """Write rows from the extracted table to a CSV writer."""
    table = soup.find('table', attrs={'class': 'grid'})
    if table is None:
        raise RuntimeError('Missing table')
    for tr in table.find_all('tr'):
        if tr.td is None or tr.td.attrs.get('colspan') == 7:
            continue
        if 'Displaying buildings ' in str(tr):
            continue
        writer.writerow([
            re.sub(r'\s+', ' ', td.text.strip()) for td in tr.find_all('td')
        ])

def prepare(session):
    """Prepare the session by making initial requests."""
    session.headers.update({
        'User-Agent': "Mozilla (scraper bike) Gecko Chrome Safari",
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Origin': 'https://apps.hcr.ny.gov',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://apps.hcr.ny.gov/buildingsearch/default.aspx',
    })
    r = session.get(ENDPOINT)
    soup = BeautifulSoup(r.text, LIB)
    session.headers.update({
        'Cookie': 'ASP.NET_SessionId=' + session.cookies['ASP.NET_SessionId']
    })
    sleep()
    param = dumb_params(soup)
    param.update({
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$zipCodeSearchLinkButton',
        'ctl00$ContentPlaceHolder1$countyDropDown': '',
    })
    sleep()
    r = session.post(ENDPOINT, data=param)
    return BeautifulSoup(r.text, LIB)

def firstpage(session, county, zipcode):
    """Get the first page of results for a given county and zip code."""
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
    soup = prepare(session)
    county_params.update(dumb_params(soup))
    request = session.post(ENDPOINT, data=county_params, headers=AJAX_HEAD)
    soup = construct_soup(request.text)
    zip_params.update(dumb_params(soup))
    request = session.post(ENDPOINT, data=zip_params)
    return request.text

def count(session, county, zipcode):
    """Count the number of results for a given county and zip code."""
    text = firstpage(session, county, zipcode)
    if re.search('0 results found', text):
        buildings = 0
    else:
        match = re.search(r'Displaying buildings \d+ - \d+ of (\d+)', text)
        buildings = match.groups()[0]
    print('{},{},{}'.format(county, zipcode, buildings))

def scrape(session, county, zipcode):
    """Scrape the results for a given county and zip code."""
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
    text = firstpage(session, county, zipcode)
    if re.search('0 results found', text):
        print('0 buildings found in', zipcode, file=sys.stderr)
        return
    match = re.search(r'Displaying buildings \d+ - \d+ of (\d+)', text)
    print(match.groups()[0], 'buildings found in', zipcode, file=sys.stderr)
    soup = BeautifulSoup(text, LIB)
    writer = csv.writer(sys.stdout, lineterminator='\n')
    writerows(writer, soup)
    next_button = re.search(r'value="Next"', text)
    sleep()
    while next_button:
        next_params.update(dumb_params(soup))
        request = session.post(ENDPOINT, data=next_params, headers=AJAX_HEAD)
        soup = construct_soup(request.text)
        try:
            writerows(writer, soup)
        except RuntimeError:
            request = session.post(ENDPOINT, data=next_params, headers=AJAX_HEAD)
            soup = construct_soup(request.text)
            writerows(writer, soup)
        next_button = re.search(r'value="Next"', request.text)
        sleep()

def main():
    parser = argparse.ArgumentParser(description="Scrape building data from HCR NY.")
    parser.add_argument('county', type=str, help="County name")
    parser.add_argument('zipcode', type=str, help="Zip code to search")
    parser.add_argument('--action', default='scrape', choices=('scrape', 'count'), help="Action to perform")

    args = parser.parse_args()
    county = args.county.replace('NEWYORK', 'NEW YORK')

    with requests.Session() as session:
        try:
            print(f"Starting action: {args.action} for county: {county}, zipcode: {args.zipcode}")
            if args.action == 'scrape':
                scrape(session, county, args.zipcode)
            elif args.action == 'count':
                count(session, county, args.zipcode)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
