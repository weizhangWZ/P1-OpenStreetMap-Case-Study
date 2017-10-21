#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This document is used for extracting a json document
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
import sys
import pypinyin

# some information is written in chinese
reload(sys)
sys.setdefaultencoding('utf-8')

#json tree
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
POS = ["lat","lon"]
OTHER = ["amenity","cuisine","name","phone","id","type","visible"]
ADDRESS = ["addr:housenumber","addr:postcode","addr:street"]

# street clean
num = ['0','1','2','3','4','5','6','7','8','9','(',')','-']
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons","Highway"]
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

def shape_element(element):
    node =  {}
    node["created"]={}
    set_pos = 0
    if element.tag == "node" or element.tag == "way":
        # node the information from node and way line
        position = {}
        keys = element.keys()
        node["type"] = element.tag
        for k in keys:
            value = element.attrib[k]
            if k in CREATED:
                if k == "user":
                    value= update_chinese(value)
                node["created"][k]=value
            elif k in POS:
                if set_pos == 0:
                    node["pos"] = [0.0,0.0]
                    set_pos=1
                if k == 'lat':
                    node["pos"][0] = float(value)
                else:
                    node["pos"][1] = float(value)
            else:
                node[k]=value
        # try to know the child information
        set_add = 0
        set_noteref = 0
        for child in element:   
            if child.tag == 'tag':
                value = child.attrib['v']
                if child.attrib['k'] in ADDRESS:
                    if set_add == 0:
                        node["address"] = {}
                        set_add = 1
                    #if housenumber
                    if child.attrib['k']=="addr:housenumber":
                        value = update_housenumber(value)
                        if value == "Invalid":
                            return None
                        node["address"]["housenumber"]=value
                    #if street and verify
                    if child.attrib['k'] == "addr:street":
                        value = audit_street(value)
                        if value == "Invalid typing":
                            return None
                        node["address"]["street"]=value
                    # if postcode
                    if child.attrib['k'] == "addr:postcode":
                        if len(value) != 6 or value[0] == '3':
                            return None
                        node["address"]["postcode"]=value
                if child.attrib['k'] in OTHER:
                    if child.attrib['k'] == "name":
                        value = update_chinese(value)
                    node[child.attrib['k']]=value
            if child.tag == 'nd':
                if set_noteref == 0:
                    set_noteref=1
                    node['node_refs'] = []
                node['node_refs'].append(child.get("ref"))
                
        #pprint.pprint(node)
        return node
    else:
        return None

def update_chinese(name):
    new_name = ""
    uni_str = name.decode('utf-8')
    pinyinlist = pypinyin.pinyin(uni_str,style=pypinyin.NORMAL)
    for i in pinyinlist:
        new_name = new_name + i[0]
    return new_name
        

def update_housenumber(housenum):
    house_num = ""
    for i in housenum:
        if i is num:
            house_num = house_num + i
    if house_num =="":
        return "Invalid"
    return house_num

def update_chinese_address(street_name):
    new_name = ""
    #unicode for chinese road
    uni_str = street_name.decode('utf-8')
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
    return new_name

def audit_street(street_name):
    # search for type infomation of roads
    street_name = update_chinese_address(street_name)
    street_type_charaters = street_type_re.search(street_name)
    # audit street_name 
    if street_type_charaters:
        street_type = street_type_charaters.group()
        if street_type not in expected:
            street_name = update_street_info(street_name,mapping)
    return street_name


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

# for street information is within the content
def type_involved(name, noun):
    new_name = ""
    for i in name:
        if new_name.find(noun) != -1:
            return new_name
        if i not in num:
            new_name = new_name + i
        else:
            new_name = ""

# the road information is at the begining
def wrong_type(name, noun):
    location = name.find(noun)
    if noun != "Dadao":
        return name[:location-1]+" Road"
    else:
        return name[:location-1]+" Street"
    
def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):

            el = shape_element(element)
            
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

def test():
    data = process_map('shanghai_china.osm', True)

if __name__ == "__main__":
    test()
