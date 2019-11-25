from utils import base36_encode


def insert_url(redis, url):
    short_id = redis.get("reverse-url:" + url)
    if short_id is not None:
        return short_id
    url_num = redis.incr("last-url-id")
    short_id = base36_encode(url_num)
    redis.set("url-target:" + short_id, url)
    redis.set("reverse-url:" + url, short_id)
    return short_id


def get_url(redis, short_id):
    return redis.get("url-target:" + short_id)


def increment_url(redis, short_id):
    redis.incr("click-count:" + short_id)


def get_count(redis, short_id):
    return int(redis.get("click-count:" + short_id) or 0)


def get_url_list(redis):
    urls = {}
    for id in range(int(redis.get("last-url-id")), 0, -1):
        urls[id] = get_url(redis, str(id)).decode('utf-8')
    return urls


def insert_user(redis, username, email, password):
    redis.set(username, password)
    redis.set("email:" + username, email)


def get_user(redis, username):
    if redis.exists(username):
        return redis.get(username).decode('utf-8')
