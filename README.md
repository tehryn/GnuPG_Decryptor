# GPG Encrypted Web Pages
The digital outcome of the thesis

##Content
* **GnuPG Decryptor** - Contains the web browser extension
* **GnuPG Decryptor Prototypes** - Contains all prototypes of GnuPG Decryptor extension (Iterations 2 - 5)
* **Keys** - Contains all public and private keys used for testing
* **Native Application** - Contains native application for GnuPG Decryptor extension
* **Test pages** - Contains implemented HTML pages, CSS styles, JavaScripts and images used for testing
* **Thesis - LaTeX** - Contains LaTeX source codes of the thesis
* **Thesis - PDF** - PDF version of the thesis

##Installation
In order to make the native application functional, it is necessary to have [GnuPG](https://gnupg.org/download/index.html) a [Python 3](https://docs.python-guide.org/starting/install3/linux/) application installed. It is also necessary to install [PyQt5](https://pypi.org/project/PyQt5/) and [Magic](https://pypi.org/project/python-magic/) libraries for Python 3. To install the software, you can use previous links, or follow these steps:

###Python 3
To install Python 3, use command:

`sudo apt-get install python3.6`

To install PyQT5 and Magic libraries for python3.6, use commands:

`sudo apt-get install python3-pyqt5`

`sudo apt-get install python3-magic`

###GnuPG
To install GnuPG, use command:

`sudo apt-get install gnupg`

##Native Application
To install the native application, it is necessary to copy the **Native Application** directory into the device and modify the *GnuPG_Decryptor.json* file in the **Native Application** directory, so the *file* attribute points the file *gnupg_decryptor.py* (also in the **Native Application** directory). Then for global visibility of the native application, store the manifest file in either:

`/usr/lib/mozilla/native-messaging-hosts/GnuPG_Decryptor.json`

`/usr/lib/mozilla/managed-storage/GnuPG_Decryptor.json`

`/usr/lib/mozilla/pkcs11-modules/GnuPG_Decryptor.json`

`/usr/lib64/mozilla/native-messaging-hosts/GnuPG_Decryptor.json`

`/usr/lib64/mozilla/managed-storage/GnuPG_Decryptor.json`

`/usr/lib64/mozilla/pkcs11-modules/GnuPG_Decryptor.json`

or for per-user visibility in:

`~/.mozilla/native-messaging-hosts/GnuPG_Decryptor.json`

`~/.mozilla/managed-storage/GnuPG_Decryptor.json`

`~/.mozilla/pkcs11-modules/GnuPG_Decryptor.json`

##Keys
There are four keys that can be imported. Three of the are protected with a password, that is identical with their names.
* test1, no password
* test2, password *test2*
* test3, password *test3*
* test4, password *test4*
