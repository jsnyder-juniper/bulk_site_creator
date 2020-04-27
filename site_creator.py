#!/usr/bin/env python3

# Requirements:
#
# config.py file that contains a variable google_api_key
#   google_api_key needs access to googlemaps geocode api as well as the timezone functions
#
# sites.csv which contains the following headers:
#   site_name,site_address,site_groups,rf_template_id

import csv
import requests
import urllib.parse
import os
import config
import time
import json

os.environ['GOOGLE_API_KEY'] = config.google_api_key
# module import needs to occur after setting os.environ variable
import geocoder


class MistAPI(object):
    def __init__(self, host: str, org: str):
        self.host = host
        self.org = org
        self.header = ""


class MistAPIToken(MistAPI):
    def __init__(self, host: str, org: str, mist_api_token: str):
        """

        :param host: api host: ex api.mist.com
        :param org: org_id: example xxxxxxx-xxxx-xxx-xxxxxxxxx
        :param mist_api_token: mist API token "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        """
        super(MistAPIToken, self).__init__(host, org)
        self.mist_api_token = mist_api_token
        self.header = {"Authorization": f"Token {mist_api_token}"}


class Mist:
    def __init__(self, mist_api: MistAPI):
        """

        :param mist_api: MistAPI object or inherited method like MistAPIToken
        """
        self.mistAPI = mist_api

    def http_get(self, url):
        """

        :param url: url extension.  Example: /api/v1/self
        :return: requests response object
        """
        try:
            header = {**{"content-type": "application/json"}, **self.mistAPI.header}
            my_url = f"https://{self.mistAPI.host}{url}"
            response = requests.get(my_url, headers=header)
            return response
        except Exception as e:
            print(e)
            return None

    def http_post(self, url: str, body: dict):
        """

        :param url: url extension.  Example: /api/v1/self
        :param body: dictionary formatted body for a post
        :return:
        """
        response = None
        try:
            header = {**{"content-type": "application/json"}, **self.mistAPI.header}
            my_url = f"https://{self.mistAPI.host}{url}"
            response = requests.post(my_url, headers=header, data=json.dumps(body))
        except Exception as e:
            print(e)
        return response

    def verify_self(self):
        """

        :return: verifies that API credential successfully return a /api/v1/self
        """
        try:
            results = self.http_get("/api/v1/self")
            if results.status_code == 200:
                return True
        except Exception as e:
            print(e)
            return False

    def get_rf_templates(self):
        """

        :return: returns a list of dictionay rf_templates
        """
        rf_templates = None
        try:
            rf_templates = self.http_get(f"/api/v1/orgs/{self.mistAPI.org}/rftemplates").json()
        except Exception as e:
            print(e)
        return rf_templates

    def get_rftemplate_by_name(self, rf_template_name: str):
        """

        :param rf_template_name: Name of the RF Template
        :return: rf template dictionary
        """
        rf_templates = self.get_rf_templates()
        return next(item for item in rf_templates if item["name"] == rf_template_name)

    def create_site(self, body):
        """

        :param body: properly formatted body for a site creation
        :return: requests response object
        """
        response = self.http_post(f"/api/v1/orgs/{self.mistAPI.org}/sites", body)
        return response


def get_parser():
    """

    :return: parser for argparse
    """
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Mist site creation tool")
    parser.add_argument(
        "-k", "--key", dest="mist_api_key", help="Mist API Key", type=str, required=True
    )
    parser.add_argument(
        "-o", "--org", dest="mist_org", help="Mist Org ID", type=str, required=True
    )
    parser.add_argument(
        "-e", "--EU", dest="mist_europe", help="Mist EU Environment", required=False
    )
    return parser


def encode_address(address: str):
    """

    :param address: normally formatted address
    :return: url encoded string
    """
    return urllib.parse.quote(address)


def get_google_timezone(lat: float, lng: float):
    """
    :param lat: float lattitude
    :param lng: float longitdue
    :return: str with timezone
    """
    g_url = "https://maps.googleapis.com/maps/api/timezone/json?location="
    try:
        response = requests.get(
            f"{g_url}{lat},{lng}&timestamp={int(time.time())}&key={config.google_api_key}")
        data = response.json()
        results = data['timeZoneId']
        return results
    except Exception as e:
        print(e)
        return None


def get_google_geoinfo(address: str):
    """

    :param address: string with site address
    :return: dictionary with geocode info formatted for body
    """
    try:
        gaddr = geocoder.google(address)
        results = {
            'address': gaddr.address,
            'latlng': {
                'lat': gaddr.lat,
                'lng': gaddr.lng,
            },
            'country_code': gaddr.country
        }
        return results
    except Exception as e:
        print(e)
        return None


def main(argv):
    successful_sites = []
    failed_sites = []
    mist_api_key = argv.mist_api_key
    org = argv.mist_org
    if argv.mist_europe is not None:
        host = "api.eu.mist.com"
    else:
        host = "api.mist.com"
    site_data = read_csv("sites.csv")

    # mist_api = MistAPIToken(host, mist_api_key)
    mist_api = MistAPIToken(host, org, mist_api_key)
    mist_connector = Mist(mist_api)
    api_verify = False
    try:
        api_verify = mist_connector.verify_self()
    except Exception as e:
        print(e)
    if api_verify:

        for site in site_data:
            body = get_google_geoinfo(site['site_address'])
            body['name'] = site['site_name']
            body['timezone'] = get_google_timezone(body['latlng']['lat'], body['latlng']['lng'])
            if site['rf_template_name'] != "":
                body['rftemplate_id'] = mist_connector.get_rftemplate_by_name(site['rf_template_name'])['id']
            print(body)
            results = mist_connector.create_site(body)
            if results.status_code == 200:
                successful_sites.append(body)
            else:
                failed_sites.append(body)

        print("Successful sites: ")
        for site in successful_sites:
            print(site['name'])
        print("Failed Sites: ")
        for site in failed_sites:
            print(site['name'])


def read_csv(filename):
    """

    :param filename: string
    :return: list of site dictionaries
    """
    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file)
        site_data = [record for record in reader]
    print(site_data)
    return site_data


if __name__ == '__main__':
    my_parser = get_parser()
    my_args = my_parser.parse_args()
    print(my_args)
    print(type(my_args))
    main(my_args)
