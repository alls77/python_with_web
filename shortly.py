# -*- coding: utf-8 -*-
"""
    shortly
    ~~~~~~~

    A simple URL shortener using Werkzeug and redis.

    :copyright: 2007 Pallets
    :license: BSD-3-Clause
"""
import os

import redis

from db import get_url, insert_url, get_count, increment_url, get_url_list, get_user, insert_user
from utils import get_hostname, is_valid_url

from jinja2 import Environment, FileSystemLoader
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response
from werkzeug.security import generate_password_hash, check_password_hash


class Shortly(object):
    def __init__(self, config):
        self.redis = redis.Redis(config["redis_host"], config["redis_port"])
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_path), autoescape=True)
        self.jinja_env.filters["hostname"] = get_hostname

        self.url_map = Map(
            [
                Rule("/", endpoint="sign_up"),
                Rule("/home", endpoint="home"),
                Rule("/<short_id>_details", endpoint="short_link_details"),
                Rule("/create", endpoint="new_url"),
                Rule("/<short_id>", endpoint="follow_short_link"),
                Rule("/short_link_list", endpoint="list_url"),
                Rule("/sign_in", endpoint="sign_in"),
                Rule("/sign_out", endpoint="sign_out"),
            ]
        )

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype="text/html")

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, "on_" + endpoint)(request, **values)
        except NotFound:
            return self.error_404()
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def on_home(self, request):
        return self.render_template("homepage.html")

    def on_new_url(self, request):
        error = None
        url = ""
        if request.method == 'POST':
            url = request.form['url']
            if not is_valid_url(url):
                error = 'invalid url'
            else:
                id = insert_url(self.redis, url)
                return redirect(b'/%s_details' % id)

        return self.render_template("new_url.html", error=error, url=url)

    def on_follow_short_link(self, request, short_id):
        link_target = get_url(self.redis, short_id)
        if not link_target:
            return NotFound()

        increment_url(self.redis, short_id)
        return redirect(link_target)

    def on_short_link_details(self, request, short_id):
        url = get_url(self.redis, short_id)
        if not url:
            return NotFound()

        click_count = get_count(self.redis, short_id)
        return self.render_template(
            "short_link_details.html",
            link_target=url.decode('utf-8'),
            short_id=short_id,
            click_count=click_count,
        )

    def on_list_url(self, request):
        url_list = get_url_list(self.redis)
        return self.render_template('url_list.html', urls=url_list,)

    def on_sign_up(self, request):
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            insert_user(self.redis, username, email, generate_password_hash(password))
            return redirect('/sign_in')

        return self.render_template("sign_up.html")

    def on_sign_in(self, request):
        error = None
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user_password = get_user(self.redis, username)
            if user_password and check_password_hash(user_password, password):
                return redirect('/home')
            else:
                error = 'incorrect username or password'

        return self.render_template("sign_in.html", error=error)

    def on_sign_out(self, request):
        return redirect('/')

    def error_404(self):
        response = self.render_template("404.html")
        response.status_code = 404
        return response

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)
