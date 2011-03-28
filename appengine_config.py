from gaesessions import SessionMiddleware

# suggestion: generate your own random key using os.urandom(64)
# WARNING: Make sure you run os.urandom(64) OFFLINE and copy/paste the output to
# this file.  If you use os.urandom() to *dynamically* generate your key at
# runtime then any existing sessions will become junk every time you start,
# deploy, or update your app!
import os
COOKIE_KEY = '[-\x8d=oT\x98\xf1\xdba\xdd\x13\x11\x04\xf0\x8c\xfb\x1ef]\x021\xed\x18{\x10\x02\x89yYC\xfbJP\xeb\xb2B\xf5#`\xba\xff0\x06n\xe5\xc5\xc2\x0b\xc5\x84\x9e\x7f\xb1\x08Z\x03\xf0a\xd4\\5p]'

def webapp_add_wsgi_middleware(app):
  from google.appengine.ext.appstats import recording
  app = SessionMiddleware(app, cookie_key=COOKIE_KEY)
  app = recording.appstats_wsgi_middleware(app)
  return app
