== Description == 

`gphoto2-timelapse` allows you to create timelapse photography using a supported DSLR camera 
connected via USB (http://gphoto.org/proj/libgphoto2/support.php), and the gphoto2 unix tool 
(http://www.gphoto.org/).

== Installation == 

You will need to install python to run the intervalometer (timelapse) scripts. - http://www.python.org/getit/

You can use the install scripts - gphoto2-install / install

It's a great idea to install gphoto2 from source as the pre-built libraries are generally old. 
The gphoto2-install script does just this.

== Use == 

Once everything is installed, you need to tweak the script and the XML configuration file a bit to get 
it to work with your own camera. Once you have the camera specific parameters and functions in place, 
you can use the python scripts to start taking images:

  python timelapse.py test.xml

== Credits == 

This code originated from the following python script by dwiel:

  http://dwiel.net/blog/raspberry-pi-timelapse-camera/

Thank you for the inspiration!