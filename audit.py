#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
this document is aim to audit and clean the sample osm
"""
import xml.etree.cElementTree as ET
from collections import defaultdict
import pprint
import re
import sys
import pypinyin

# some information is written in chinese
reload(sys)
sys.setdefaultencoding('utf-8')

# set global data
# for testing keys type
keys_correction = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
num = ['0','1','2','3','4','5','6','7','8','9','(',')']
keys_type = {}
# tags_type 
tags = {'bounds': 0,
        'member': 0,
        'nd': 0,
        'node': 0,
        'osm': 0,
        'relation': 0,
        'tag': 0,
        'way': 0}
# uid storage
users = set()
# street audit
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons","Highway"]
street_types = defaultdict(set)
#postcode audit
postcode_info = set()
#housenumber audit
housenumber_info = set()

# street clean
mapping = { 
            "Jie":"Street",
            "Rd":"Road","rd":"Road","Rd,":"Road","Rd.":"Road",
            "road":"Road","raod":"Road","Raod":"Road","Rode":"Road",
            "avenue":"Avenue","Ave.":"Avenue","Dadao":"Avenue",
            "Hwy.":"Highway",
            "lu":"Road","Lu":"Road",
            "Gonglu":"Road","Gong lu":"Road",
            "Xiang":"Alley"
            }
#json preparation
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
POS = ["lat","lon"]
ADDRESS = ["housenumber","postcode","street"]
OTHER = ["amenity","cuisine","name","phone","id","type","visible","node_refs"]
    
def key_type(element, keys):
    # element analyze(keys_type_infomation)
    if element.tag == "tag":
        value = element.attrib['k']
        # judge whether store the keys_type
        if not keys_type.get(value):
            keys_type[value] = 1
        else:
            keys_type[value] +=1
        # audit keys type
        '''
        if lower_colon.search(value):
            keys["lower_colon"]+=1
        elif lower.search(value):
            keys["lower"]+=1
        elif problemchars.search(value):
            keys["problemchars"]+=1
        else:
            keys["other"]+=1
        '''
    return keys

def get_uid(element):
    if element.tag in ["node","way","relation"]:
        uid = element.attrib['uid']
        users.add(uid)
    return users

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def is_postcode(elem):
    return (elem.attrib['k'] == "addr:postcode")

def is_housenumber(elem):
    return (elem.attrib['k'] == "addr:housenumber")


def audit_street(element):
    # search for type infomation of roads
    valid_flag = True
    street_name = element.attrib['v']
    street_type_charaters = street_type_re.search(street_name)
    # audit street_name 
    if street_type_charaters:
        street_type = street_type_charaters.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)
    return street_types

def audit_housenumber(element):
    number = element.attrib['v']
    housenumber_info.add(number)
    return housenumber_info
    
def audit_postcode(element):
    postcode = element.attrib['v']
    valid_flag = True
    # if the code in more than 6 digit, it is wrong code
    if len(postcode) != 6:
        valid_flag = False
    if postcode[0] == '3':
        valid_flag = False
    if valid_flag:
        postcode_info.add(postcode)
    
    return postcode_info, valid_flag

def process_map(filename):
    
    for event, element in ET.iterparse(filename,events = ("start","end")):
        if event == 'end':
            keys = key_type(element, keys_correction)
            tags[element.tag] += 1
            users = get_uid(element)
        else:
            if element.tag == "node" or element.tag == "way":
                for tag in element.iter("tag"):
                    '''
                    #audit street
                    if is_street_name(tag):
                        street_types = audit_street(tag)
                    
                    #audit postcode
                    if is_postcode(tag):
                        postcode_info,valid_postcode = audit_postcode(tag)
                    '''    
                    if is_housenumber(tag):
                        house = audit_housenumber(tag)
                        
    return keys,tags,users,street_types,postcode_info

def update_street_info(name, mapping):
    street_type_charaters = street_type_re.search(name)
    street_type = street_type_charaters.group()
    if not mapping.get(street_type):
        name = chinese_correction(name)
    else:
        street_type_right = mapping[street_type]
        location = name.find(street_type)
        name = name[:location] + street_type_right
    return name

def chinese_correction(name):
    new_name = ""
    #unicode for chinese road
    uni_str = name.decode('utf-8')
    pinyinlist = pypinyin.pinyin(uni_str,style=pypinyin.NORMAL)
    #all pinyin style
    for i in pinyinlist:
        if i[0] == 'lu':
            new_name = new_name + " Road"
            return new_name
        if i[0] == 'jie':
            new_name = new_name + " Street"
            return new_name
        if i[0] == 'cun':
            new_name = new_name + " Community"
            return new_name
        elif i[0] == 'qu':
            new_name = ""
        else:
            address = i[0].decode('utf-8')
            count = 0
            tmp = ""
            for character in address:
                if count == 0:
                    character = character.upper()
                count = 1
                tmp = tmp + character
            new_name = new_name + tmp

    # all pinyin style or already include road information with other information
    if name.find("Road") != -1:
        return type_involved(name, "Road")
    if name.find("Street") != -1:
        return type_involved(name, "Street")
    if name.find("rd") != -1:
        return type_involved(name, "rd")
    if name.find("Rd.") !=-1:
        return wrong_type(name, "Rd.")
    if name.find("lu")!=-1:
        return wrong_type(name, "lu")
    if name.find("rd")!=-1:
        return wrong_type(name, "rd")
    if name.find("Lu")!=-1:
        return wrong_type(name, "Lu")
    if name.find("Gong Lu")!=-1:
        return wrong_type(name, "Gong Lu")
    if name.find("Dadao")!=-1:
        return wrong_type(name, "Dadao")
    if name.find("road") != -1:
        return type_involved(name, "road")

    name = "Invalid typing"    
    return name

def type_involved(name, noun):
    new_name = ""
 
    for i in name:
        if new_name.find(noun) != -1:
            return new_name
        if i not in num:
            new_name = new_name + i
        else:
            new_name = ""

def wrong_type(name, noun):
    location = name.find(noun)
    if noun != "Dadao":
        return name[:location-1]+" Road"
    else:
        return name[:location-1]+" Street"

def restult():
    # print and count tags and keys type
    keys,tags,users,street_types,postcode_info = process_map('shanghai_china.osm')
    #pprint.pprint(postcode_info)
    #pprint.pprint(housenumber_info)
    #pprint.pprint(dict(street_types))
    #pprint.pprint(tags)

    '''
    with open("correction.txt","w") as out:
        for street_type, ways in street_types.iteritems():
            for name in ways:
                better_name = update_street_info(name, mapping)
                out.write(name+"=>"+better_name)
                out.write("\n")
 '''          
    '''
    #write to a txt to see much more clearly without extra run 
    with open("street_types_shanghai.txt","w") as out:
        for road_name in street_types:
            out.write(road_name)
            for value in street_types[road_name]:
                 out.write('\t')
                 out.write(value+'\t')
                 out.write('\n')
    '''
    #print keys,'\n',users
    pprint.pprint(keys_type)
    
if __name__ == "__main__":
    restult()
