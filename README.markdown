Student Webspace for AppEngine
==============================

What is Student Webspace?
-------------------------

In a nutshell, *Student Webspace* is a minimalistic hosting platform running on top of *Google App Engine*. I created it to allow my students to have some place to upload and host their assignments.

The app is designed to give you control over the user registration. New users must register using a valid secret `CourseID` code. Once they register they can upload any files into their account. Each file gets a unique URL such as:

    http://yourapp.appspot.com/pub/username/foo.html

How does it work?
-----------------

The files are uploaded to Google's Blobstore database and the username and file name are used to find and retrieve them. I wrote a lengthy [blog post](http://www.terminally-incoherent.com/blog/2011/03/28/student-webspace-in-the-cloud-google-app-engine/) explaining the nature of the app, it's specifications and development details.

Please note that you may need to enable billing to use Bloblstore.

The project uses [GAE Sessions](https://github.com/dound/gae-sessions) instead of Google's user management in order to allow anyone sign up for the service (not only users with Google accounts).

Disclaimer
----------

This app is provided as is, without any warranty. There are some serious bugs in it, and I haven't really got around to fix them. If you managed to iron these out, please let me know.

Deploying Student Webspace
--------------------------

Here are the steps you should take to successfully deploy your own version of *Student Webspace*:

  1. Open `appengine_config.py` and generate your own security key. You can use mine, but you probably would want your own. See the comments in the file for instructions.
  1. Deploy your app to *Google AppEngine*
  1. Navigate your browser to `http://yourapp.example.com/init` to configure your first account
  1. Choose a password
  1. You will be automatically logged in as admin with that password.

Once you log in, you will notice that there is already a `CourseID` in the system. It will be something like `ADMIN_XXXX` where `XXXX` is a randomly generated number. You can use this `CourseID` to register new users, but I recommend creating a new one from the admin panel when you introduce this app to the class.

Note that this procedure won't work in ver 0.2 or lower. If you are running earlier version please upgrade.

Promoting a user to Admin Status
--------------------------------

All accounts start as `student` accounts. Running the init procedure (see above) will create your first `admin` account. If you need more admins, you will want to add them manually. 

  1. Go to the *AppEngine* console 
  1. Click on *DataStore* viewer 
  1. Find the `WebSpaceUser` value for the specific user 
  1. Manually Change its `type` to `admin`. 

There is no UI for this yet but I expect to have one ready in version 0.4.
