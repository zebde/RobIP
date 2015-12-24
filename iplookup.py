#!/usr/bin/env python
"""This script performs basic enrichment on a given IP"""

import dns.resolver
from geoip import geolite2
import mmap
import socket
import csv
import os
import urllib
import argparse
from netaddr import IPSet, AddrFormatError
# import json


PARSER = argparse.ArgumentParser()
PARSER.add_argument("-t",
                    choices=('single', 'batch'),
                    required="true",
                    metavar="request-type",
                    help="Either single or batch request")
PARSER.add_argument("-v",
                    required="true",
                    metavar="value",
                    help="The value of the request")
ARGS = PARSER.parse_args()
TORCSV = 'Tor_ip_list_ALL.csv'
# SECCSV = csv.reader(open('idLookup.csv', 'rb'), delimiter=',', quotechar="\"")
SUBNET = 0
INPUTDICT = {}
RTNDICT = []
OUTFILE = 'IP-lookup-output-22.csv'
CSVCOLS = ["ip-address", "asn", "as-name", "isp", "abuse-1", "abuse-2",
           "abuse-3", "domain", "reverse-dns", "type", "country", "lat",
           "long", "tor-node", "location", "abuse-contacts"]


def identify(value):
    """This function returns a value based on the value given"""
    if ("ac.uk") in value:
        category = 'Academia'
    elif (".edu") in value:
        category = "Academia"
    elif ".gov.uk" in value:
        category = "Government"
    elif ".gov" in value:
        category = "Government"
    elif "council" in value:
        category = "Local Government"
    elif "School" in value:
        category = "Academia"
    elif ".mil" in value:
        category = "Military"
    elif ".mod.uk" in value:
        category = "Military"
    elif ".nhs.uk" in value:
        category = "NHS"
    elif ".nhs.net" in value:
        category = "NHS"
    elif ".sch.uk" in value:
        category = "Academia"
    elif "hmrc" in value:
        category = "HMRC"
    else:
        category = 'Other'
    return category


def lookup(value):
    """Performs a dns request on the given value"""
    try:
        answers = dns.resolver.query(value, 'TXT')
        for rdata in answers:
            for txt_string in rdata.strings:
                value = txt_string.replace(" | ", "|")
                value = value.replace(" |", "|").split("|")
    except dns.resolver.NXDOMAIN:
        value = "-"
    return value


def flookup(value, fname):
    """Looks up a value in a file"""
    try:
        fhandle = open(fname)
    except IOError:
        testfile = urllib.URLopener()
        testfile.retrieve(
            "http://torstatus.blutmagie.de/ip_list_all.php/Tor_ip_list_ALL.csv",
            "Tor_ip_list_ALL.csv")
        fhandle = open(fname)
    search = mmap.mmap(fhandle.fileno(), 0, access=mmap.ACCESS_READ)
    if search.find(value) != -1:
        return 'true'
    else:
        return 'false'


# def func1(vara):
#     print "selector: " + vara
#     x = 0
#     for row in SECCSV:
#         value = row[0]
#         print value
#         if value == vara:
#             rv = row[1]
#             return rv
#         else:
#             return "Other"
#         x = x + 1


# def slookup(vara):
#     print "selector: " + vara
#     x = 0
#     for row in SECCSV:
#         print x
#         value = row[0]
#         if value == vara:
#             print "result: " + value
#             return row[1]
#         else:
#             print "result: Other"
#             return "Other"
#         x = x + 1


def iprange(sample, sub):
    """Identifies if the given ip address is in the previous range"""
    # print "'" + str(sample) + "' -- '" + str(sub) + "'"
    if sub is not 0 and not '212.219.0.0/16':
        try:
            ipset = IPSet([sub])
            if sample in ipset:
                return True
        except AddrFormatError:
            return False
    else:
        return False


def mainlookup(var):
    """Wraps the main lookup and generated the dictionary"""
    global SUBNET
    global INPUTDICT
    var = ''.join(var.split())
    # print(INPUTDICT.get("ip-address"))
    if iprange(var, SUBNET) is True:
        print SUBNET
        # try:
        #     rdns = socket.gethostbyaddr(var)
        # except socket.herror:
        #     rdns = "-"
        # print 'Found in previous range'
        print
    elif INPUTDICT.get("ip-address") == var:
        print 'Found in previous lookup'
    else:
        print 'Full lookup ahoy!'
        try:
            socket.inet_aton(var)
        except socket.error:
            var = socket.gethostbyname(var)
        contactlist = []
        rvar = '.'.join(reversed(str(var).split(".")))

        origin = lookup(rvar + '.origin.asn.shadowserver.org')
        SUBNET = origin[1]

        contact = lookup(rvar + '.abuse-contacts.abusix.org')
        contactlist = str(contact[0]).split(",")

        contactlist.extend(["-"] * (4 - len(contactlist)))
        try:
            rdns = socket.gethostbyaddr(var)
        except socket.herror:
            rdns = "-"

        match = geolite2.lookup(var)
        if match is None or match.location is None:
            country = ''
            location = ["", ""]
        else:
            country = match.country
            location = match.location

        tor = flookup(var, TORCSV)

        # print slookup("BT")
        # print func1("BT")
        # category = slookup(origin[4])
        # if category is "Other":
        #     category = slookup(str(origin[5]))

        # print sector

        # category = identify(origin[4])
        # if category is "Other":
        #     category = identify(str(rdns[0]))
        category = 'blank'
        INPUTDICT = {
            'ip-address': var,
            'asn': origin[0],
            'tor-node': tor,
            'abuse-1': contactlist[0],
            'abuse-2': contactlist[1],
            'abuse-3': contactlist[2],
            'as-name': origin[2],
            'isp': origin[5],
            'domain': origin[4],
            'reverse-dns': str(rdns[0]),
            'type': category,
            'country': country,
            'lat': location[0],
            'long': location[1]
        }
    INPUTDICT['ip-address'] = var

    # print json.dumps(INPUTDICT, sort_keys=True, indent=4, ensure_ascii=False)
    RTNDICT.append(INPUTDICT)
    # csvout(INPUTDICT)


def batch(inputfile):
    """Handles batch lookups using file based input"""
    tcount = 0
    lcount = 0
    if os.path.isfile("IP-lookup-output.csv"):
        os.remove("IP-lookup-output.csv")

    with open(inputfile) as fhandlea:
        for line in fhandlea:
            if line.strip():
                tcount += 1

    with open(inputfile) as fhandle:
        for line in fhandle:
            lcount += 1
            print "Processing line " + str(lcount) + " of " + str(tcount)
            mainlookup(line.rstrip('\n'))
        writedicttocsv(OUTFILE, CSVCOLS, RTNDICT)


def single(lookupvar):
    """Caries out a single IP lookup"""
    mainlookup(lookupvar)


def writedicttocsv(csv_file, csv_columns, dict_data):
    try:
        with open(csv_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in dict_data:
                writer.writerow(data)
    except IOError as (errno, strerror):
        print("I/O error({0}): {1}".format(errno, strerror))
    return


def csvout(inputdict):
    """Generates a CSV file from the output inputdict"""
    fhandle = open("IP-lookup-output.csv", "a+")
    try:
        csv.Sniffer().has_header(fhandle.read())
    except csv.Error:
        writer = csv.writer(fhandle, quoting=csv.QUOTE_ALL)
        writer.writerow((
            "AddrIP",
            "ASN",
            "AS Name",
            "ISP",
            "Abuse-1",
            "Abuse-2",
            "Abuse-3",
            "Domain",
            "Reverse DNS",
            "Type",
            "Country",
            "Lat",
            "Long",
            "TOR"))
    try:
        writer = csv.writer(fhandle, quoting=csv.QUOTE_ALL)
        writer.writerow((
            inputdict[0]['ip-address'],
            inputdict[0]['asn'],
            inputdict[0]['as-name'],
            inputdict[0]['isp'],
            inputdict[0]['abuse-contacts']['abuse-1'],
            inputdict[0]['abuse-contacts']['abuse-2'],
            inputdict[0]['abuse-contacts']['abuse-3'],
            inputdict[0]['domain'],
            inputdict[0]['reverse-dns'],
            inputdict[0]['type'],
            inputdict[0]['country'],
            inputdict[0]['location']['coordinates']['lat'],
            inputdict[0]['location']['coordinates']['long'],
            inputdict[0]['tor-node']))
    finally:
        fhandle.close()

# OPTIONS = {'single': single, 'batch': batch}

# OPTIONS[OPT](IP)

if ARGS.t == "single":
    single(ARGS.v)
elif ARGS.t == "batch":
    batch(ARGS.v)
else:
    PARSER.print_help()
