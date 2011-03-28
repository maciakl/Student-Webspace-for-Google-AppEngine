Student Webspace

This project is a Google App Engine application. It provides a web interface for uploading
small files into Google's Blobstore database and retrieving them using unique human readable
URI's.

It can be used to allow users to host their own webpages using the service as easy file manager.

For example a user can upload file foo.html into the service, and it can be viewed using a URL
like /pub/username/foo.html

The project uses GAE Sessions instead of Google's user management in order to allow anyone sign
up for the service (not only users with Google accounts).
