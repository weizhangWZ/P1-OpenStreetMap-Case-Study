#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import json
import pprint


def get_db(db_name):
    from pymongo import MongoClient
    client = MongoClient('localhost:27017')
    db = client[db_name]
    return db


def make_pipeline():
    # complete the aggregation pipeline
    pipeline = [
                {"$group":{"_id":"$created.user",
                           "count":{"$sum":1}}},
                {"$sort":{"count":-1}},
                {"$limit":100}]
    return pipeline
    

def place_sources(db, pipeline):
    return [doc for doc in db.places.aggregate(pipeline)]

if __name__ == '__main__':
    db = get_db('shanghai_map')
    #pprint.pprint(db.places.find_one())
    pipeline = make_pipeline()
    result = place_sources(db, pipeline)
    pprint.pprint(result)

