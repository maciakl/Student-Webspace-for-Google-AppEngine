Student Webspace for AppEngine
=======================

What is Student Webspace?
----------------------------

In a nutshell, Student Webspace is a minimalistic hosting platform running on top of Google App Engine. I created it to allow my students to have some place to upload and host their assignments.

The app is designed to give you control over the user registration. New users must register using a valid secret Course ID code. Once they register they can upload any files into their account. Each file gets a unique URL such as:

    http://yourapp.appspot.com/pub/username/foo.html

How does it work?
--------------------

The files are uploaded to Google's Blobstore database and the username and file name are used to find and retrieve them. I wrote a lengthy [blog post](http://www.terminally-incoherent.com/blog/2011/03/28/student-webspace-in-the-cloud-google-app-engine/) explaining the nature of the app, it's specifications and development details.

Please note that you may need to enable billing to use Bloblstore.

The project uses [GAE Sessions](https://github.com/dound/gae-sessions) instead of Google's user management in order to allow anyone sign up for the service (not only users with Google accounts).

Known Issues
---------------

This app is provided as is, without any warranty. There are some serious bugs in it, and I haven't really got around to fix them. If you managed to iron these out, please let me know.

#### Registering without Course ID 

When you run the app for the first time, there is no defined CourseID. Thing is one of the few caveats of the application. I simply did not bother making a proper "first-run" script. 

The easy workaround is this:

  1. Change the FIRST_RUN constant defined in line 6 to True
  1. Deploy the app and register first account
  1. Change FIRST_RUN to False
  1. Redeploy

There will eventually be an easier way to do this.

#### Creating Admin Account 

All accounts start as "student" accounts. So once you have your first account, you will want to go to the AppEngine console DataStore viewer, find the WebSpaceUser value that was just created and manually change its "type" to "admin". There is no UI for this yet.

