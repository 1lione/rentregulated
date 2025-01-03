New York Rent Regulated Buildings 
---------------------------------

In New York, many privately-owned apartments are subject to limits on the rent landlords can ask. The vast majority of these apartments are called *rent stabilized*. An older program, *rent control*, has even stronger limits on rent increases and evictions.

Owners of buildings with rent-controlled and rent-stabilized apartments must register them with the state [Division of Housing and Community Renewal](http://www.nyshcr.org). This registry also includes information about housing subsidy programs that apply to these buildings. But be careful, quoth DHCR: "Inclusion on the list is not determinative of the building's current status."

You can [search the DHCR registry](https://apps.hcr.ny.gov/BuildingSearch/), but it's difficult to get complete data. This data set was compiled in mid-2016 using a [script](scrape.py) to methodically request all of data from the DCHR site.

The publically accessible dataset includes registrations going back to 1984. The dataset includes more than one entry for some buildings, reflecting registrations in different years.

The vast majority of properties are in the five boroughs, with a few properties in Nassau, Rockland and Westchester counties.

## Using the data

The data is included as a CSV file: [rentregulated.csv](rentregulated.csv). The file has 68,000 rows and is 6.1 MB.

The accompanying `Makefile` can be used to create an SQLite database or load the data into a MySQL database:
```
# create an SQLite db
make rentregulated.db
# load into a mysql database called rentregulated on localhost
make mysql USER=myusername PASS=mypassword HOST=localhost
```

Additionally, `[rentregulated.json](rentregulated.json) is a GeoJSON file with geocoded addresses. A mix of Google, Mapbox and Mapzen geocoders were used.

The `Makefile` also includes a script to download a new copy of the data. Note that the DHCR website is very slow and buggy, and download isn't a smooth process. The script requires Python 3.5 and two common prerequisites. Run `pip3.5 -r requirements.txt` to install the prerequisites. Remove `rentregulated.csv` then run `make` to download the data. Running multiple processes is not recommended.

## Caveats

Because of the aforementioned bugginess of the DCHR site, this data may not be complete. Pull requests with verified additions are welcome.

* DCHR has provided [basic information](https://apps.hcr.ny.gov/buildingsearch/popup.aspx) about the fields in the data set, but details about their methodology are missing.
* Some addresses are given as ranges ("6 TO 10 MAIN STREET").
* Some properties have "additional addresses". The significance of these addresses is unexplained. This data is available on the DHCR site, but requires an additional step to scrape, so only the note that an additional address exists is included.
* The `status` field includes a a space-separated of program or description that applies to a building. One or more status may be present. The exact wording of each status may differ slightly, so be careful with filtering. The statuses, with links to the best explanation available:
    * [MULTIPLE DWELLING A](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#DwellingA)
    * [MULTIPLE DWELLING B](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#DwellingB)
    * [HOTEL](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Hotel)
    * [SINGLE ROOM OCCUPANCY](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#SingleRoom)
    * [GARDEN APARTMENT COMPLEX](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Garden)
    * [NON-EVICT COOP/CONDO](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#NonEvict) (may include an effective date in parentheses)
    * [EVICT COOP/CONDO](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Evict) (may include an effective date in parentheses)
    * [COOP/CONDO PLAN FILED](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Coop) (may include a file date in parentheses)
    * [J-51](http://www1.nyc.gov/site/hpd/developers/tax-incentives-j51.page)
    * [421-A](http://www1.nyc.gov/site/hpd/developers/tax-incentives-421a.page)
    * [ARTICLE 11 OF PHFL](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Article11)
    * [ARTICLES 14 & 15 OF PHFL](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Article14and15)
    * [SEC 608 OF PHFL](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#Section608)
    * [Not Indicated by Owner](https://apps.hcr.ny.gov/buildingsearch/popup.aspx#NotIndicated)
    * RENT CONTROLLED APTS MAY EXIST
    * COLD WATER TENEMENT
    * [LIHTC](https://www.huduser.gov/portal/datasets/lihtc.html) (Low Income Housing Tax Credit, may be mis-coded as LITHC)
    * [421-G](http://www1.nyc.gov/site/hpd/developers/tax-incentives-421g.page)
    * HUD SECTION 8 or [SECTION 8](https://en.wikipedia.org/wiki/Section_8_%28housing%29)
    * [HDFC](http://www1.nyc.gov/site/hpd/owners/homeowner-hdfc.page) or HDFC COOP
    * [420C](http://www1.nyc.gov/site/hpd/developers/tax-incentives-420c.page)
    * MIRP - [Mixed Income Rental Program](http://furmancenter.org/institute/directory/entry/mixed-income-rental-program/)
    * HTF - [Housing Trust Fund](http://furmancenter.org/institute/directory/entry/new-york-city-housing-trust-fund)
    * BANK LOAN
    * IN RECEIVERSHIP
    * SECT 576 or PHF 576
    * various notes about building type and size, e.g. "3 FAMILY BROWNSTONE", "12 FAMILY UNIT"
