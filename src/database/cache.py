#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - cache.py


import logging

import fakeredis
import redis

from config import REDIS_HOST


class Redis:
    def __init__(self):
        self.using_fake_redis = False
        try:
            self.r = redis.StrictRedis(host=REDIS_HOST, db=1, decode_responses=True)
            self.r.ping()
        except Exception:
            logging.warning("Redis connection failed, using fake redis instead.")
            self.r = fakeredis.FakeStrictRedis(host=REDIS_HOST, db=1, decode_responses=True)
            self.using_fake_redis = True

    def __del__(self):
        self.r.close()

    def add_cache(self, key, mapping):
        # Don't cache when using fake redis to prevent URL corruption
        if self.using_fake_redis:
            logging.debug("Skipping cache write due to fake redis")
            return
        self.r.hset(key, mapping=mapping)

    def get_cache(self, k: str):
        # Don't use cache when using fake redis to prevent URL corruption
        if self.using_fake_redis:
            logging.debug("Skipping cache read due to fake redis")
            return {}
        return self.r.hgetall(k)
