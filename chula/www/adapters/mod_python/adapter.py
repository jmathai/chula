"""
Chula mod_python adapter
"""

import time
from copy import deepcopy

from mod_python import apache as APACHE

import chula
from chula import collection, error, guid
from chula.www import cookie
from chula.www.adapters.mod_python import env
from chula.www.mapper.standard import StandardMapper

def _handler(req, config):
    if config.add_timer:
        TIME_start = time.time()

    #if not environ['wsgi.input'] is None:
    #    raise Exception(str(environ['wsgi.input']))

    # Create a fake request object and start using it over mod_python
    # in adapters.apache
    buffer = []

    # Create objects required by the controller(s)
    _env = env.Environment(req)
    _env.headers = []

    received_cookies = _env.HTTP_COOKIE
    _env.cookies = cookie.CookieCollection()
    _env.cookies.load(received_cookies)

    _env.cookies.timeout = config.session_timeout
    _env.cookies.key = config.session_encryption_key

    # Fetch any cookes we were given (we add ours at the end)
    #raise Exception(str(environ['HTTP_COOKIE']))

    
    # Fetch the controller via the configured url-mapper
    mapper = StandardMapper(config, _env)
    controller = mapper.map()
    controller.env.route = mapper.route


    # Call the controller method and if an exception is raised, use
    # the configured e500 controller.  If that breaks, it's up to your
    # web server custom 500 handler to handle things.
    try:
        html = controller.execute()
    except Exception, ex:
        if config.debug:
            raise
        else:
            # Prepare a collection to hold exception context
            context = collection.Collection()
            context.exception = ex
            context.env = deepcopy(controller.env)
            context.form = deepcopy(controller.form)

            # Try the error controller (and set an exception attribute in
            # the model)
            controller = mapper.map(500)
            controller.model.exception = context
            html = controller.execute()

    # Persist session and perform garbage collection
    try:
        controller._pre_session_persist()
        controller.session.persist()
    except error.SessionUnableToPersistError():
        # Need to assign an error controller method to call here
        raise
    except Exception:
        # This is a downstream exception, let them handle it
        raise
    finally:
        controller._gc()

    # Write the returned html to the request object.
    # We're manually casting the view as a string because Cheetah
    # templates seem to require it.  If you're not using Cheetah,
    # sorry... str() is cheap  :)
    if not html is None:
        html = str(html)

        # Add info about server info and processing time
        written = False
        if config.add_timer:
            end = html[-8:].strip()
            for node in ('</html>', '</HTML>'):
                if end == node:
                    cost = (time.time() - TIME_start) * 1000
                    try:
                        buffer.append(html.replace(node, """
                            <div style="display:none;">
                                <div id="CHULA_SERVER">%s</div>
                                <div id="CHULA_COST">%f ms</div>
                            </div>
                            """ % (controller.env.HTTP_HOST, cost)))
                        buffer.append(node)
                        written = True
                    except IOError:
                        if config.debug:
                            raise
                    finally:
                        break

        if not written:
            try:
                buffer.append(html)
            except IOError:
                if config.debug:
                    raise
    else:
        raise error.ControllerMethodReturnError()

    # Set HTTP headers set by the controller
    req.content_type = controller.content_type
    _env.headers.append(_env.cookies.headers())
    for header in _env.headers:
        req.headers_out.add(header[0], header[1])

    # Set the HTTP status
    req.status = _env.status

    # If we got here, all is well
    for chunk in buffer:
        req.write(chunk)

    return APACHE.OK

def handler(fcn):
    def wrapper(req):
        config = fcn()
        return _handler(req, config)

    return wrapper