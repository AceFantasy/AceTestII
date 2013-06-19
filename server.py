# -*- coding: utf-8 -*-

import logging
import uuid
import os
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape

from tornado.options import define, options

if __name__ == '__main__':
    define("port", default=8888, help=u"指定启动端口", type=int)

tornado.options.parse_command_line()
IL = tornado.ioloop.IOLoop.instance()

logger = logging.getLogger('AceTest')

logger.propagate = False
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(name)s|%(asctime)s|L%(lineno)s|%(levelname)s|%(message)s', '%m-%d %H:%M:%S')
stream_hd = logging.StreamHandler()
stream_hd.setFormatter(fmt)
stream_hd.setLevel(logging.DEBUG)
logger.addHandler(stream_hd)


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        _method = self.get_argument('_method', None)
        if _method is not None:
            self.request.method = _method.upper()
        self.uuid = uuid.uuid4().hex[:6]


class Handler(BaseHandler):
    SUPPORTED_METHODS = ('SUCCESS', 'ERROR', 
                         'GET', 'READ','CREATE', 'EXPORT')

    CASE_LIST = []

    def get(self):
        self.render('index.html')

    def export(self):
        import tornado.template
        s = '''
AceTestII文档导出


{% for o in obj_list %}
= {{ o['memo'] }} =

- 地址: {{ o['url'] }}
- 方法: {{ o['method'] }}
- 头:
{% for h in o['header'] %}
    - {{ h[0] }}: {{ h[1] }}
{% end %}
- 参数:
{% for p in o['params'] %}
    - {{ p[0] }}: {{ p[1] }}
{% end %}
- 响应:
{% if 'response' in o %}
```
{{ o['response'] }}
```
{% end %}
- 描述:
{% if 'description' in o %}
```
{{ o['description'] }}
```
{% end %}
{% end %}
        '''
        tpl = tornado.template.Template(s)
        obj_list = tornado.escape.json_decode(self.get_argument('obj_list', '[]'))

        s = tpl.generate(obj_list=obj_list)
        self.set_header('content-type', 'text/plain')
        self.write(s)

    def create(self):
        obj_list = tornado.escape.json_decode(self.request.body)
        fields = set(['id', 'url', 'method', 'params', 'header', 'memo', 'tags', 'create', 'description', 'response'])
        for o in obj_list:
            for k in o.keys():
                if k not in fields:
                    del o[k]
        self.__class__.CASE_LIST = obj_list
        self.write({'result': 0})

        import json
        with open('data.json', 'wb') as f:
            f.write(json.dumps(obj_list, indent=True, ensure_ascii=False).encode('utf8') + '\n')

    def read(self):
        obj_list = [
            {'id': 'a',
             'url': '/',
             'method': 'GET',
             'params': [['_method', 'success'], ['a', 'xxx']],
             'header': [['a', 'abc'], ['X-Sohu', '234']],
             'memo': '成功的请求',
             'tags': ['ok', 'abc'],
             'create': 0,
             'description': '',
             'response': '',
            },
        ]
        if os.access('data.json', os.F_OK):
            import json
            with open('data.json', 'rb') as f:
                data = f.read()

            self.__class__.CASE_LIST = json.loads(data.decode('utf8'))
        self.write({'result': 0, 'msg': '', 'obj_list': self.__class__.CASE_LIST})

    def success(self):
        self.write({'result': 0, 'msg': ''})

    def error(self):
        self.write({'result': 1, 'msg': u'错误信息'})



class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
            template_path = os.path.dirname(__file__),
            debug=True,
        )
        self.visit_logger = logging.getLogger('AceTest.Visit')
        tornado.web.Application.__init__(self, (('.*', Handler),), **settings)

    def log_request(self, handler):
        '记录一次请求'

        status = handler.get_status()
        if status < 400:
            log_method = self.visit_logger.info
        elif status < 500:
            log_method = self.visit_logger.warning
        else:
            log_method = self.visit_logger.error
        request_time = 1000.0 * handler.request.request_time()

        rq = handler.request
        h = rq.headers

        msg = '|'.join([getattr(handler, 'uuid', ''),
                        rq.remote_ip,
                        h.get('Referer', '(Ref)'),
                        rq.method,
                        str(rq.arguments),
                        str(handler.get_status()),
                        '%.2f' % request_time,
                       ])

        if status < 400:
            log_method(msg)
        else:
            log_method(msg, exc_info=True)


def main():
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port)
    print 'starting on %s ...' % options.port
    IL.start()
    

if __name__ == "__main__":
    main()
