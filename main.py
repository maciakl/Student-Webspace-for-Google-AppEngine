#!/usr/bin/env python

import os
import md5
import urllib
import logging
import random

from google.appengine.ext import db
from gaesessions import get_current_session

from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

"""
	Here is what we are doing: we are implementing a filesystem... In the cloud. Users can upload their files,
	which get stored in AppEngine's BlobStore as blobs. Then they can be served with an appropriately formatted
	url. For example, lets say the user jsmith1 uploads file foo.html to the blobstore. This file should be now available
	at:

	http://thisap/pub/jsmith1/foo.html

	How do we do this? We store the file in blobstore, grab the key and save the key in DataStore along with the
	username, and the file name.

	When someone visits /pub/xxx/zzz we interpret it as a request to fetch file zzz uploaded by xxx from the blobstore.

	There is a catch - xxx and zzz are not unique. But we get around this:

	When user uploads a file, we query the Datastore and if an entry with the same xxx and zzz exists we delete it.

	# I'm using gaesessions because I want to use this for my CMPT109 lab excercise and having students sign up for
	Gmail would be too much hassle. So this app includes custom session handling crap.

	See https://github.com/dound/gae-sessions
	
"""


## HTML Stuff

HEADER = '''
<html>
	<head>
		<title>Student Webspace</title>
		<style type="text/css">

		body {

			font-size: 12px;
			font-family: Verdana, Arial, SunSans-Regular, Sans-Serif;
  			color:#564b47;  
			padding:0px;
			margin:0px;
		}
		

		#content {
			
			margin: 20px;
			padding: 50px 50px 100px 50px;

			border: 1px solid gray;

			-moz-border-radius:50px;
			-webkit-border-radius:50px;
			border-radius:50px;
		
			min-height: 350px;
			height:auto !important;
			height:350px;
			
		}

		#footer {

			margin: 20px;
			padding: 0px 0px 0px 50px;
		}

		h2 {
			padding: 10px 10px 10px 35px;
			border: 1px solid gray;
			background: lightGray;

			-moz-border-radius:50px;
			-webkit-border-radius:50px;
			border-radius:50px;
		}

		#navbar {

			float: right;
			width: 300px;

			min-height: 200px;
			height:auto !important;
			height:200px;
			

			background: lightGray;
			padding: 10px;

			margin-right: 10px;

			text-align: center;

			-moz-border-radius:20px;
			-webkit-border-radius:20px;
			border-radius:20px;

			border: 1px solid gray;
		}

		#navbar a {

			display: block;
			padding: 5px;
			margin-bottom: 10px;


			background: lightYellow;

			-moz-border-radius:10px;
			-webkit-border-radius:10px;
			border-radius:10px;

			border: 1px solid gray;

			text-decoration: none;
		}

		#navbar a:hover {
			background: yellow;
		}

		form {
			margin-left: 20px;
		}

		p {
			margin-left: 20px;
		}

		#iediss {
			margin-left: 100px;

			background: red;
			color: white;
			padding: 10px;
			width: 50%;
		}

		</style>
	</head>
	<body>
		<div id='content'>'''

ADMIN_LINK = '<a href="/admin">admin panel</a>'

FOOTER = '''
		</div>

		<div id="footer"><small>Student Webspace &copy; Luke Maciak. See the <a href="https://github.com/maciakl/Student-Webspace-for-Google-AppEngine">Source Code</a></div>
	
	</body>
</html>'''

class MyBlobFile(db.Model):
    netID = db.StringProperty()
    fileName = db.StringProperty()
    blobstoreKey = blobstore.BlobReferenceProperty()

class CourseID(db.Model):
    courseID = db.StringProperty()
    active = db.BooleanProperty()

class WebspaceUser(db.Model):
    username = db.StringProperty()
    password = db.StringProperty()
    type = db.StringProperty(choices=set(["admin", "student", "inactive"]))
    course = db.StringProperty()

    
# this is the upload frm
class MainHandler(webapp.RequestHandler):
    def get(self):

	session = get_current_session()
	
	if(session.is_active()):
		netID = session.get('netID')
		logging.debug("SESSION netID: %s" % str(netID))
	else:
		netID =''
		logging.debug("SESSION NOT ACTIVE")
		self.redirect('/login')

	adm = ADMIN_LINK if checkAdmin(netID) else ''


        upload_url = blobstore.create_upload_url('/upload')
        
	self.response.out.write(HEADER)
	self.response.out.write('<h2>Student Webspace: File Upload</h2>')
	self.response.out.write('<div id="navbar">%s <a href="/list">view uploaded files</a> <a href="/password">change password</a> <a href="/logout">log out</a></div><br>' % adm)

        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
	self.response.out.write('<input type="hidden" name="netid" value="%s"><br>' % netID)

        self.response.out.write("""
		 
		Upload File: <input type="file" name="file"> 
		<input type="submit" name="submit" value="Submit">
		
		</form>""") 
		
	self.response.out.write(FOOTER)

class LoginHandler(webapp.RequestHandler):

	def get(self):
		self.response.out.write(HEADER)
		self.response.out.write('<h2>Student Webspace: Log In</h2>')
		self.response.out.write('<div id="navbar"><a href="/register">register</a></div>')
        	self.response.out.write('<form action="/login" method="POST">')
		self.response.out.write('Username:<br> <input type="text" name="netid" ><br>')
		self.response.out.write('Password:<br> <input type="password" name="password"><br>')
		self.response.out.write('<input type="submit" name="submit" value="Submit">') 
		self.response.out.write('</form>')
		self.response.out.write(FOOTER)

	def post(self):

		netid = urllib.unquote(self.request.get('netid'))
		password = self.request.get('password')

		# check username and password

		q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", netid)
		results = q.get()

		if(results == None):
			errorMsg(self, "Sorry, such user does not exist. Please register");
			return
		else:
			if(results.password == md5.new(password).hexdigest()):

				session = get_current_session()
				session.regenerate_id()
				session.set_quick('netID', netid)

				self.redirect('/')
			else:
				errorMsg(self, "Sorry, the password was incorrect")
				return


class RegisterHandler(webapp.RequestHandler):

	def get(self):
		self.response.out.write(HEADER)
		self.response.out.write('<h2>Student Webspace: Registration</h2>')
		self.response.out.write('<div id="navbar"><a href="/login">log in</a></div>')
        	self.response.out.write('<form action="/register" method="POST">')
		self.response.out.write('Username:<br> <input type="text" name="netid" ><br>')
		self.response.out.write('Password:<br> <input type="password" name="password"><br>')
		self.response.out.write('Retype Password:<br> <input type="password" name="password2"><br>')
		self.response.out.write('Valid CourseID:<br> <input type="text" name="courseID"><br>')
		self.response.out.write('<input type="submit" name="submit" value="Submit">') 
		self.response.out.write('</form>')
		self.response.out.write(FOOTER)

	def post(self):

		username = self.request.get("netid")
		password1 = self.request.get("password")
		password2 = self.request.get("password2")

		# check if passwords are matching

		if(password1 != password2):
			errorMsg(self, "Passwords did not match")
			return

		password = md5.new(password1).hexdigest()

		course = self.request.get("courseID")
				
		# check courseID

		q = db.GqlQuery("SELECT * FROM CourseID WHERE courseID =:1", course)
		results = q.get()

		if(results == None):
			errorMsg(self, "Sorry, the Course ID you entered is invalid")
			return


		# check if username is already in datastore

		q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", username)
		results = q.get()

		if(not results == None):
			errorMsg(self, "Sorry, this username is already taken")
		else:
			u = WebspaceUser()
			u.type = "student"
		
			u.username = username
			u.password = password
			u.course = course
		
			u.put()

			session = get_current_session()
			session.set_quick('netID', username)
	
			self.redirect('/')


# method for displaying error messages. Note that this is a bit of a python hack
# this is declared outside of any of the classes. Any class can use it though by
# passing itself as the first argument
def errorMsg(self, message):

	self.response.out.write(HEADER)
	self.response.out.write('<h2>Student Webspace: Error</h2>')
	self.response.out.write('<div id="navbar"><a href="/list">back</a></div>')
	self.response.out.write('<p>%s.</p>' % message)
	self.response.out.write(FOOTER)


class PasswordResetHandler(webapp.RequestHandler):

	def get(self):

			session = get_current_session()

			if(not session.is_active()):
				self.redirect('/login')
		
			self.response.out.write(HEADER)
			self.response.out.write('<h2>Student Webspace: Password Reset</h2>')
			self.response.out.write('<div id="navbar"><a href="/">back</a></div>')
			self.response.out.write('<form action="/password" method="POST">')
			self.response.out.write('New password:<br> <input type="password" name="password"><br>')
			self.response.out.write('Retype Password:<br> <input type="password" name="password2"><br>')
			self.response.out.write('<input type="submit" name="submit" value="Submit">') 
			self.response.out.write('</form>')
			self.response.out.write(FOOTER)

	def post(self):

			session = get_current_session()

			if(not session.is_active()):
				self.redirect('/login')

			netid = session.get('netID')
			password1 = self.request.get("password")
			password2 = self.request.get("password2")

			if(password1 != password2):
				errorMsg(self, "Passwords did not match")
				return

			password = md5.new(password1).hexdigest()

			q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", netid)
			results = q.get()

			#self.response.out.write(results.password)
			
			results.password = password
			results.put()

			self.redirect("/")


class InitHandler(webapp.RequestHandler):

	def get(self):
            
                netid = "admin"
		q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", netid)
		results = q.get()

		if(results == None):

			self.response.out.write(HEADER)
			self.response.out.write('<h2>Student Webspace: Initialization</h2>')
			self.response.out.write('<div id="navbar"><a href="/">back</a></div>')
			self.response.out.write('<p>We are going to set up a default admin account for you. The username will be admin. Please choose a strong password:</p>')
			self.response.out.write('<form action="/init" method="POST">')
			self.response.out.write('Admin password:<br> <input type="password" name="password"><br>')
			self.response.out.write('Retype Password:<br> <input type="password" name="password2"><br>')
			self.response.out.write('<input type="submit" name="submit" value="Submit">') 
			self.response.out.write('</form>')
			self.response.out.write('<p>Next time, log in as admin with this password.</p>')
			self.response.out.write(FOOTER)
		else:
			self.redirect('/')

	def post(self):

		netid = "admin"
		q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", netid)
		results = q.get()

		if(results == None):

			password1 = self.request.get("password")
			password2 = self.request.get("password2")

			if(password1 != password2):
				errorMsg(self, "Passwords did not match")
				return

			password = md5.new(password1).hexdigest()

			course = "ADMIN_" + str(random.randint(1000,9999))
	
			u = WebspaceUser()
			u.type = "admin"
		
			u.username = "admin"
			u.password = password
			u.course = course
		
			u.put() 


			q = db.GqlQuery("SELECT * FROM CourseID WHERE courseID =:1", course)
			results = q.get()

			if(not results == None):
				errorMsg(self, "Sorry, this CoruseID already exists")
			else:
				u = CourseID()
				u.status = "active"
				u.courseID = course

				u.put()

			session = get_current_session()
			session.set_quick('netID', "admin")
	
			self.redirect('/')


class LogoutHandler(webapp.RequestHandler):

	def get(self):

		session = get_current_session()
		session.terminate()

		self.redirect('/login')

class ListHandler(webapp.RequestHandler):

	def get(self):

		session = get_current_session()

		if(not session.is_active()):
			self.redirect('/login')
		
		netid = session.get('netID')

		adm = ADMIN_LINK if checkAdmin(netid) else ''
		
		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: File List</h2>")
		self.response.out.write('<div id="navbar">%s <a href="/">upload new file</a> <a href="/password">change password</a> <a href="/logout">log out</a></div><br>' % adm)

		q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID =:1", netid)
		results = q.fetch(100)

		self.response.out.write('<p>Uploaded files</p><ul>')

		for p in results:
			self.response.out.write('<li><a href="/pub/%s">%s</a> <small><small><a href="/delete/%s">[delete]</a></small></small>' % (netid+"/"+p.fileName, p.fileName, p.fileName))

		self.response.out.write('</ul>')

		self.response.out.write(FOOTER)

class AdminListHandler(webapp.RequestHandler):

	def get(self, student):

		if(not loggedInAsAdmin(self)):
			return
		
		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: File List for %s</h2>" % student)
		self.response.out.write('<div id="navbar"><a href="/">upload new file</a> <a href="/logout">log out</a></div><br>')

		q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID =:1", student)
		results = q.fetch(100)

		self.response.out.write('<p>Uploaded files</p><ul>')

		for p in results:
			self.response.out.write('<li><a href="/pub/%s">%s</a> <small><small><a href="/admindelete/%s/%s">[delete]</a></small></small>' % (student+"/"+p.fileName, p.fileName, student, p.fileName))

		self.response.out.write('</ul>')

		self.response.out.write(FOOTER)



class AdminHandler(webapp.RequestHandler):

	def get(self):

		if(not loggedInAsAdmin(self)):
			return
	
		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: Admin Page</h2>")
		self.response.out.write('<div id="navbar"><a href="/list">exit admin page</a></div><br>')
		
		self.response.out.write('<p>Admin Options:</p><ul>')
	
		self.response.out.write('<li><a href="/newcourse">Create a new Course ID</a></li>')
		self.response.out.write('<li><a href="/courses">List all Course ID\'s</a></li>')

		self.response.out.write('</ul>')


        	
		self.response.out.write(FOOTER)



class CourseHandler(webapp.RequestHandler):

	def get(self):

	
		if(not loggedInAsAdmin(self)):
			return

		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: New Course</h2>")
		self.response.out.write('<div id="navbar"><a href="/admin">back to admin page</a></div><br>')
		
        	self.response.out.write('<form action="/newcourse" method="POST">')
		self.response.out.write('New CourseID:<br> <input type="text" name="courseID" ><br>')
		self.response.out.write('<input type="submit" name="submit" value="Submit">') 
		self.response.out.write('</form>')

		self.response.out.write(FOOTER)

	def post(self):

		if(not loggedInAsAdmin(self)):
			return

		courseID = self.request.get("courseID")

		q = db.GqlQuery("SELECT * FROM CourseID WHERE courseID =:1", courseID)
		results = q.get()

		if(not results == None):
			errorMsg(self, "Sorry, this CoruseID already exists")
		else:
			u = CourseID()
			u.status = "active"
			u.courseID = courseID

			u.put()

			self.redirect("/courses")

class CourseListHandler(webapp.RequestHandler):

	def get(self):

		if(not loggedInAsAdmin(self)):
			return

		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: Course List</h2>")
		self.response.out.write('<div id="navbar"><a href="/admin">back to admin page</a></div><br>')

		self.response.out.write('<p>Course List:</p><ul>')

		q = db.GqlQuery("SELECT * FROM CourseID")
		results = q.fetch(100)
	
		for c in results:
			self.response.out.write('<li><a href="/students/%s">%s</a></li>' % (c.courseID, c.courseID))

		self.response.out.write(FOOTER)



class StudentListHandler(webapp.RequestHandler):

	def get(self, course):

		if(not loggedInAsAdmin(self)):
			return

		self.response.out.write(HEADER)
		self.response.out.write("<h2>Student Webspace: Student List for %s</h2>" % course)
		self.response.out.write('<div id="navbar"><a href="/admin">back to admin page</a></div><br>')

		self.response.out.write('<p>Student List for %s:</p><ul>' % course)

		q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE course = :1", course)
		results = q.fetch(100)
	
		for s in results:
			self.response.out.write('<li><a href="/adminview/%s">%s</a></li>' % (s.username, s.username))

		self.response.out.write(FOOTER)


class DeleteHandler(webapp.RequestHandler):

	def get(self, filename):

		session = get_current_session()

		if(not session.is_active()):
			self.redirect('/login')
		
		netid = session.get('netID')
		
		logging.debug("Checked for login")
		logging.debug("NetID: %s" % netid)
		logging.debug("Filename: %s" % filename)

		
		q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID =:1 AND fileName =:2", netid, urllib.unquote(filename))
		results = q.get()

		logging.debug("Past the query. Result: %s" % str(results))

		# if it exists, delete it

		if(results != None):
			resource = results.blobstoreKey
			blobstore.delete(resource.key())
			db.delete(results)

			self.redirect("/list")
		else:
			errorMsg(self, "Sorry, this file does not seem to exist or you don't have permission to delete it")
			return

class AdminDeleteHandler(webapp.RequestHandler):

	def get(self, student, filename):

		session = get_current_session()

		if(not loggedInAsAdmin(self)):
			return
		
		netid = session.get('netID')
		
		logging.debug("Checked for login")
		logging.debug("NetID: %s" % netid)
		logging.debug("Filename: %s" % filename)

		
		q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID = :1 AND fileName =:2", student, urllib.unquote(filename))
		results = q.get()

		logging.debug("Past the query. Result: %s" % str(results))

		# if it exists, delete it

		if(results != None):
			resource = results.blobstoreKey
			blobstore.delete(resource.key())
			db.delete(results)

			self.redirect("/adminview/%s" % student)
		else:
			errorMsg(self, "Sorry, this file does not seem to exist or you don't have permission to delete it")
			return


		
def loggedInAsAdmin(self):

	session = get_current_session()

	if(not session.is_active()):
		return False;

	username = session.get("netID")

	if(not checkAdmin(username)):
		errorMsg(self, "Sorry, you are not allowed to view this page")
		return False

	return True

def checkAdmin(username):

	q = db.GqlQuery("SELECT * FROM WebspaceUser WHERE username =:1", username)
	results = q.get()

	if(results == None):
		return False

	logging.debug("username: %s" % results.username)
	logging.debug('type: "%s"' % results.type)

	if(results.type == 'admin'):
		return True

	return False


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
		
        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        blob_info = upload_files[0]

	session = get_current_session()

	if(not session.is_active()):
		blob_info.delete()
		self.redirect("/login")

	mynetid = self.request.get("netid")
	myfilename = str(blob_info.filename)

	# let's check if the file reference already exists in datastore
	q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID =:1 AND fileName =:2", mynetid, myfilename)
	results = q.get()

	# if it exists, delete the blob and then delete the datastore entry
	if(results != None):
		resource = results.blobstoreKey
		blobstore.delete(resource.key())
		db.delete(results)

	# now upload the new file

	f = MyBlobFile()
	f.netID= mynetid
	f.fileName= myfilename
	f.blobstoreKey =  blob_info.key()

	f.put()

        #self.redirect('/pub/%s' % (mynetid+"/"+myfilename))
	self.redirect('/list')


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, ffolder, ffile):
	
    	logging.debug("FOLDER: " + str(ffolder))
	logging.debug("FILE: " + urllib.unquote(str(ffile)))

	# get the blob key from the blobstore
	
	q = db.GqlQuery("SELECT * FROM MyBlobFile WHERE netID =:1 AND fileName =:2", str(ffolder), urllib.unquote(str(ffile)))
	results = q.get()
	
	resource = results.blobstoreKey
	self.send_blob(resource)

def main():

    logging.getLogger().setLevel(logging.DEBUG)
    
    application = webapp.WSGIApplication(
          [('/', MainHandler),
	   ('/init', InitHandler),
	   ('/password', PasswordResetHandler),
	   ('/login', LoginHandler),
	   ('/logout', LogoutHandler),
	   ('/register', RegisterHandler),
           ('/upload', UploadHandler),
	   ('/list', ListHandler),
	   ('/admin', AdminHandler),
	   ('/newcourse', CourseHandler),
	   ('/courses', CourseListHandler),
	   ('/delete/([^/]+)?', DeleteHandler),
	   ('/admindelete/([^/]+)/([^/]+)?', AdminDeleteHandler),
	   ('/students/([^/]+)?', StudentListHandler),
	   ('/adminview/([^/]+)?', AdminListHandler),
           ('/pub/([^/]+)/([^/]+)?', ServeHandler),
          ], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
  main()

