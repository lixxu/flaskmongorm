#!/usr/bin/env python3
# -*- coding=utf-8 -*-

import textwrap
from bson.objectid import ObjectId
from bson.codec_options import CodecOptions
from flask import current_app, request
from pymongo import ASCENDING, DESCENDING, TEXT

__version__ = "0.1.1"

INDEX_NAMES = dict(
    asc=ASCENDING,
    ascending=ASCENDING,
    desc=DESCENDING,
    descending=DESCENDING,
    text=TEXT,
)

wrapper = textwrap.TextWrapper(break_long_words=False)


def get_sort(sort):
    if sort is None or isinstance(sort, list):
        return sort

    sorts = []
    for items in sort.strip().split(";"):  # ; for many indexes
        items = items.strip()
        if items:
            lst = []
            for item in items.split(","):
                item = item.strip()
                if item:
                    if " " in item:
                        field, _sort = item.replace("  ", " ").split(" ")[:2]
                        lst.append((field, INDEX_NAMES[_sort.lower()]))
                    else:
                        lst.append((item, INDEX_NAMES["asc"]))

            if lst:
                sorts.append(lst)

    return sorts[0] if len(sorts) == 1 else sorts


def get_uniq_spec(fields=[], doc={}):
    specs = []
    for field in fields:
        spec = {}
        for k in [f.strip() for f in field.split(",") if f.strip()]:
            if k in doc:
                spec[k] = doc[k]

        if spec:
            specs.append(spec)

    return {"$or": specs} if specs else None


class BaseModel:
    __collection__ = None
    __unique_fields__ = []
    __mongo__ = None
    __paginatecls__ = None
    __timezone__ = None

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def get_wrap_text(self, text, width=50):
        wrapper.width = width
        return "<br />".join(wrapper.wrap(text))

    @property
    def id(self):
        return self["_id"]

    @classmethod
    def is_valid_oid(cls, oid):
        return ObjectId.is_valid(oid)

    @classmethod
    def new_id(cls):
        return ObjectId()

    @classmethod
    def get_oid(cls, _id, allow_invalid=True):
        if cls.is_valid_oid(_id):
            return ObjectId(_id)

        return _id if allow_invalid else None

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __repr__(self):
        return "{}".format(self.__dict__)

    def __getattr__(self, key):
        """just return None instead of key error"""
        return None

    @classmethod
    def get_collection(cls):
        return cls.__mongo__.db[cls.__dict__["__collection__"]]

    @classmethod
    def is_unique(cls, fields=[], doc={}, id=None, dbdoc={}, *args, **kwargs):
        spec = cls.get_uniq_spec(fields, doc)
        if spec:
            if id:
                spec["_id"] = {"$ne": id}

            kwargs.setdefault("as_raw", True)
            found_doc = cls.find_one(spec, *args, **kwargs)
            if found_doc:
                dbdoc.update(found_doc)
                return False

            return True

        return True

    @classmethod
    def get_tzinfo(cls, **kwargs):
        timezone = current_app.config.get("TIMEZONE")
        if not timezone:
            timezone = cls.__timezone__

        if timezone:
            if isinstance(timezone, str):
                try:
                    import pytz

                    return pytz.timezone(timezone)
                except ImportError:
                    return None

            return timezone

        return None

    @classmethod
    def wrap_coll_tzinfo(cls, coll, tzinfo=None):
        if tzinfo:
            return coll.with_options(
                codec_options=CodecOptions(tz_aware=True, tzinfo=tzinfo)
            )

        return coll

    @classmethod
    def get_page_args(cls, page_name=None, per_page_name=None, **kwargs):
        if not (page_name and per_page_name):
            return 0, 0, 0

        page = kwargs.get(page_name)
        per_page = kwargs.get(per_page_name)
        if request:
            if not page:
                page = request.args.get(page_name, 1)

            if not per_page:
                per_page = request.args.get(per_page_name, 10)

        if not (page and per_page):
            return 0, 0, 0

        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10

        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1

        return page, per_page, per_page * (page - 1)

    @classmethod
    def find(cls, *args, **kwargs):
        paginate = kwargs.pop("paginate", False)
        page_name = kwargs.pop("page_name", None)
        per_page_name = kwargs.pop("per_page_name", None)
        page = per_page = skip = None
        if paginate and cls.__paginatecls__:
            page_name = page_name or "page"
            per_page_name = per_page_name or "per_page"

            page, per_page, skip = cls.__paginatecls__.get_page_args(
                page_name, per_page_name
            )

        if per_page:
            kwargs.setdefault("limit", per_page)

        if skip:
            kwargs.setdefault("skip", skip)

        kwargs.pop(page_name, None)
        kwargs.pop(per_page_name, None)

        # convert to object or keep dict format
        as_raw = kwargs.pop("as_raw", False)
        kwargs.update(sort=get_sort(kwargs.get("sort")))

        tzinfo = cls.get_tzinfo(**kwargs)
        kwargs.pop("timezone", None)

        coll = cls.wrap_coll_tzinfo(cls.get_collection(), tzinfo)
        cur = coll.find(*args, **kwargs)
        if as_raw:
            cur.objects = [doc for doc in cur]
        else:
            cur.objects = [cls(**doc) for doc in cur]

        return cur

    @classmethod
    def find_one(cls, filter=None, *args, **kwargs):
        if isinstance(filter, (str, ObjectId)):
            filter = dict(_id=cls.get_oid(filter))

        as_raw = kwargs.pop("as_raw", False)
        tzinfo = cls.get_tzinfo(**kwargs)
        kwargs.pop("timezone", None)

        coll = cls.wrap_coll_tzinfo(cls.get_collection(), tzinfo)
        doc = coll.find_one(filter, *args, **kwargs)
        return (doc if as_raw else cls(**doc)) if doc else None

    @classmethod
    def insert_one(cls, doc, **kwargs):
        return cls.get_collection().insert_one(doc, **kwargs)

    def save(self, *args, **kwargs):
        if self.id:
            return self.__class__.update_one(
                dict(_id=self.id), *args, **kwargs
            )

        return self.__class__.insert_one(self.__dict__, **kwargs)

    @classmethod
    def insert_many(cls, *args, **kwargs):
        return cls.get_collection().insert_many(*args, **kwargs)

    @classmethod
    def update_one(cls, *args, **kwargs):
        return cls.get_collection().update_one(*args, **kwargs)

    @classmethod
    def update_many(cls, *args, **kwargs):
        return cls.get_collection().update_many(*args, **kwargs)

    @classmethod
    def replace_one(cls, *args, **kwargs):
        return cls.get_collection().replace_one(*args, **kwargs)

    @classmethod
    def delete_one(cls, filter, **kwargs):
        return cls.get_collection().delete_one(filter, **kwargs)

    @classmethod
    def delete_many(cls, filter, **kwargs):
        return cls.get_collection().delete_many(filter, **kwargs)

    def destroy(self, **kwargs):
        return self.__class__.delete_one(dict(_id=self.id), **kwargs)

    @classmethod
    def aggregate(cls, pipeline, **kwargs):
        docs = []
        for doc in cls.get_collection().aggregate(pipeline, **kwargs):
            docs.append(doc)

        return docs

    @classmethod
    def bulk_write(cls, requests, **kwargs):
        return cls.get_collection().bulk_write(requests, **kwargs)

    @classmethod
    def create_index(cls, keys, **kwargs):
        keys = get_sort(keys)
        coll = cls.get_collection()
        if keys and isinstance(keys, list):
            if isinstance(keys[0], list):  # [[(...), (...)], [(...)]]
                for key in keys:
                    coll.create_index(key, **kwargs)

            else:  # [(), ()]
                coll.create_index(keys, **kwargs)

    @classmethod
    def create_indexes(cls, indexes, **kwargs):
        return cls.get_collection().create_indexes(indexes)

    @classmethod
    def count(cls, *args, **kwargs):
        return cls.get_collection().count(*args, **kwargs)

    @classmethod
    def distinct(cls, key, *args, **kwargs):
        return cls.get_collection().distinct(key, *args, **kwargs)

    @classmethod
    def drop_index(cls, index_or_name, **kwargs):
        return cls.get_collection().drop_index(index_or_name)

    @classmethod
    def drop_indexes(cls):
        return cls.get_collection().drop_indexes()

    @classmethod
    def find_one_and_delete(cls, *args, **kwargs):
        kwargs.update(sort=get_sort(kwargs.pop("sort", None)))
        return cls.get_collection().find_one_and_delete(*args, **kwargs)

    @classmethod
    def find_one_and_replace(cls, *args, **kwargs):
        kwargs.update(sort=get_sort(kwargs.pop("sort", None)))
        return cls.get_collection().find_one_and_replace(*args, **kwargs)

    @classmethod
    def find_one_and_update(cls, *args, **kwargs):
        kwargs.update(sort=get_sort(kwargs.pop("sort", None)))
        return cls.get_collection().find_one_and_update(*args, **kwargs)

    @classmethod
    def group(cls, *args, **kwargs):
        return cls.get_collection().group(*args, **kwargs)

    @classmethod
    def index_information(cls):
        return cls.get_collection().index_information()

    @classmethod
    def list_indexes(cls):
        return cls.get_collection().list_indexes()

    @classmethod
    def map_reduce(cls, *args, **kwargs):
        return cls.get_collection().map_reduce(*args, **kwargs)

    @classmethod
    def options(cls):
        return cls.get_collection().options()

    @classmethod
    def parallel_scan(cls, *args, **kwargs):
        return cls.get_collection().parallel_scan(*args, **kwargs)

    @classmethod
    def reindex(cls):
        return cls.get_collection().reindex()

    @classmethod
    def with_options(cls, *args, **kwargs):
        return cls.get_collection().with_options(*args, **kwargs)

    @classmethod
    def get_sort(cls, sort):
        return get_sort(sort)

    @classmethod
    def get_uniq_spec(cls, fields=[], doc={}):
        return get_uniq_spec(fields or cls.__unique_fields__, doc)

    def clean_for_dirty(self, doc={}, keys=[]):
        """Remove non-changed items."""
        dct = self.__dict__
        for k in keys or list(doc.keys()):
            if k == "_id":
                return

            if k in doc and k in dct and doc[k] == dct[k]:
                doc.pop(k)
