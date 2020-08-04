#!/usr/bin/python3 -u
"""
Author: Jiri Matejka
Description: This module is native application of GnuPG_Decryptor broswer extension.
"""

# Note that running python with the `-u` flag is required on Windows,
# in order to ensure that stdin and stdout are opened in binary, rather
# than text, mode.

import sys
from json import loads, dumps
from struct import pack, unpack
from base64 import b64encode, b64decode
from subprocess import Popen, PIPE
from threading import Thread, Lock
from PyQt5.QtWidgets import QApplication
from magic import Magic
from GnuPG_Decryptor_GUI import GnuPG_Decryptor_GUI

class GnuPG_Decryptor:
    """
    Class representing Native application of GnuPG_Decryptor broswer extension.
    Native application is responsible for accessing private keys and decrypting
    content of a web page.
    """
    def __init__( self ):
        self._passwords = dict()
        self._gui       = None
        self._QApp      = None
        self._sudo      = None
        self._homedir   = None
        self.MAX_MESSAGE_SIZE = 750 * 1024
        self.mimeResolver     = Magic( mime=True )
        self._lock      = Lock()

    def show( self ):
        """
        Method displays GUI window for user
        """

        # If Gui is not defined yet, construct it
        if( self._gui is None ):
            self._QApp = QApplication( sys.argv )
            initKeys = []
            for keyId, password in self._passwords.items():
                initKeys.append( { 'id' : keyId, 'password' : password } )
            self._gui  = GnuPG_Decryptor_GUI( self, initKeys, self._sudo, self._homedir )

        # show the window
        self._gui.show()
        return self._QApp.exec_()

    def keyList( self, settings ):
        """
        Method returns list of secret keys based on sudo and homedir settings
        """

        stdin = ''
        args  = []
        # use sudo
        if ( settings[ 'sudo' ][ 'use' ] ):
            # sudo argument
            args.append( 'sudo' )
            # do not remember password
            args.append( '-Sk' )
            # add password to stdin
            stdin += settings[ 'sudo' ][ 'password' ] + '\n'

        # gpg call
        args.append( 'gpg' )

        # use homedir
        if ( settings[ 'home' ][ 'use' ] ):
            args.append( '--homedir' )
            args.append( settings[ 'home' ][ 'homedir' ] )

        # command to list secret keys
        args.append( '--list-secret-keys' )

        # call subprocess
        process = Popen( args ,stdin=PIPE, stdout=PIPE, stderr=PIPE )
        stdout, _ = process.communicate( stdin.encode() )
        retcode = process.returncode
        ids    = []

        # if success
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            ids    = [ { 'id' : line[25:].strip(), 'password' : '' } for line in stdout if line.startswith( 'uid' ) ]
        return { 'returnCode' : retcode, 'keys' : ids }

    def setPasswords( self, config ):
        """
        Method sets new keys and passwords.
        """

        # clear current keys and passwords
        self._passwords = dict()

        # set new keys and password
        for key in config[ 'keys' ]:
            self._passwords[ key[ 'id' ] ] = key[ 'password' ]

        # set sudo
        if ( config[ 'sudo' ][ 'use' ] ):
            self._sudo = config[ 'sudo' ][ 'password' ]
        else:
            self._sudo = None

        # set homedir parameter
        if ( config[ 'home' ][ 'use' ] ):
            self._homedir = config[ 'home' ][ 'homedir' ]
        else:
            self._homedir = None

        # notify background script about changes
        self.updateKeys()

    def getKeyUidFromId( self, keyId ):
        """
        From key id (or fingerprint if you prefer) generates get UID using gpg application
        """

        args      = [ 'gpg' ]

        # if homedir parameter should be used
        if ( not self._homedir is None ):
            args.append( '--homedir' )
            args.append( self._homedir )

        # add gpg argumnets
        args.append( '--list-public-keys' )
        args.append( '--fingerprint' )
        args.append( keyId )

        # call subprocess
        process   = Popen( args ,stdin=PIPE, stdout=PIPE, stderr=PIPE )
        stdout, _ = process.communicate()
        retcode   = process.returncode
        uid       = None

        # if success
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            uids    = [ line[25:].strip() for line in stdout if line.startswith( 'uid' ) ]
            if ( uids ):
                uid = uids[0]
        return uid

    def getKeyUidFromData( self, data ):
        """
        Method finds out, which keys were used for data encryption.
        """

        # command line arguments
        args = [ 'gpg', '--list-packets', '--list-only' ]

        # call gpg
        process = Popen( args ,stdin=PIPE, stdout=PIPE, stderr=PIPE )
        stdout, _ = process.communicate( data )
        retcode = process.returncode
        keys  = []

        # if success
        if ( retcode == 0 ):
            # output is on stderr
            stdout   = stdout.decode().splitlines()
            # we care only about lines starting with "gpg: encrypted"
            filtered = [ line for line in stdout if line.startswith( ':pubkey' )  ]
            for line in filtered:
                # find where ID/fingerprint is
                idx1 = line.find( 'keyid ' ) + 6
                idx2 = line.find( ',', idx1 )
                if ( idx2 == -1 ):
                    idx2 = len( line )
                # get uid from id/fingerprint
                uid = self.getKeyUidFromId( line[ idx1 : idx2 ] )
                if ( not uid is None ):
                    keys.append( uid )
        return keys

    @staticmethod
    def get_message():
        """
        Reads message from background script
        """
        raw_length = sys.stdin.buffer.read( 4 )

        if not raw_length:
            sys.exit( 0 )
        message_length = unpack( '=I', raw_length )[0]
        message = sys.stdin.buffer.read( message_length ).decode( "utf-8" )
        return loads( message )


    @staticmethod
    def encode_message( message_content ):
        """
        Encode a message for transmission, given its content.
        """

        encoded_content = dumps( message_content ).encode( "utf-8" )
        encoded_length  = pack( '=I', len( encoded_content ) )
        return { 'length' : encoded_length, 'content' : pack( str( len(encoded_content ) ) + "s", encoded_content ) }


    def send_message( self, encoded_message ):
        """
        Sends an encoded message to background script.
        """
        with self._lock:
            sys.stdout.buffer.write( encoded_message[ 'length' ] )
            sys.stdout.buffer.write( encoded_message[ 'content' ] )
            sys.stdout.buffer.flush()

    def debug( self, messageString ):
        """
        Sends debug message to background script
        """
        self.send_message( GnuPG_Decryptor.encode_message( { 'message' : messageString, 'type' : 'debug' } ) )

    def loadKeys( self ):
        """
        Asks background scripts for stored keys.
        """
        self.send_message( GnuPG_Decryptor.encode_message( { 'type' : 'getKeysRequest' } ) )

    def updateKeys( self ):
        """
        Update keys in background scripts
        """
        keys = self._passwords.copy()
        for key in keys.keys():
            keys[ key ] = ''
        message = { 'type' : 'updateKeysRequest', 'keys' : keys }
        if ( not self._sudo is None ):
            message[ 'sudo' ] = 1
        else:
            message[ 'sudo' ] = 0

        if ( not self._homedir is None ):
            message[ 'homedir' ] = self._homedir

        self.send_message( GnuPG_Decryptor.encode_message( message ) )

    def decrypt( self, rawData, keys, messageId, tabId ):
        """
        Decrypts the data and sends decrypted content to the content script.
        """
        err     = b''
        retcode = 0
        for key in keys:
            args     = []
            sudoPass = ''
            keyPass  = self._passwords[ key ]

            # if sudo should be used
            if ( not self._sudo is None ):
                args.append( 'sudo' )
                args.append( '-Sk' )
                sudoPass = self._sudo + '\n'

            # gpp argument
            args.append( 'gpg' )

            # if homedir should be used
            if ( not self._homedir is None ):
                args.append( '--homedir' )
                args.append( self._homedir )

            # be quiet as possible
            args.append( '--quiet' )

            # use password if we know it
            if ( keyPass ):
                args.append( '--no-tty' )
                args.append( '--pinentry-mode=loopback' )
                args.append( '--passphrase' )
                args.append( keyPass )

            # decrypt command for gpg
            args.append( '--decrypt' )

            # call subprocess
            process = Popen( args ,stdin=PIPE, stdout=PIPE, stderr=PIPE )
            decrypted, err = process.communicate( sudoPass.encode() + rawData )
            retcode = process.returncode

            # if decryption failed, try next key
            if ( retcode != 0 ):
                continue

            # get mimeType of data
            mimeType  = self.mimeResolver.from_buffer( decrypted )

            # encode data using base64
            decrypted = b64encode( decrypted )

            # split data into blocks
            blocks    = [ decrypted[ i : i + self.MAX_MESSAGE_SIZE ] for i in range( 0, len( decrypted ), self.MAX_MESSAGE_SIZE ) ]

            # get last block of data
            lastBlock = blocks.pop()

            # prepare response
            response  = { 'messageId' : messageId, 'success' : 1, 'message' : '', 'type' : 'decryptResponse', 'data' : '', 'encoding' : 'base64', 'mimeType' : mimeType, 'lastBlock' : 0, 'tabId' : tabId }

            # send all blocks, except last one
            for block in blocks:
                response[ 'data' ]  = block.decode()
                self.send_message( GnuPG_Decryptor.encode_message( response ) )

            # send last blocks
            response[ 'data' ]      = lastBlock.decode()
            response[ 'lastBlock' ] = 1
            self.send_message( GnuPG_Decryptor.encode_message( response ) )
            break
        if ( retcode != 0 ):
            errorMessage = 'Unable to decrypt data: ' + err.decode()
            self.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : messageId, 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
        elif ( not keys ):
            errorMessage = 'Unable to decrypt data: Required key is not present'
            self.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : messageId, 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )

    def main( self ):
        """
        Reads messages from background scripts and create responses.
        """
        largeRequests    = dict()
        # load stored keys
        self.loadKeys()
        while True:
            # read message
            message      = GnuPG_Decryptor.get_message()
            errorMessage = str()
            if ( message[ 'type' ] == 'decryptRequest' and 'tabId' in message ):
                # message is containts encrypted data

                # ged id of sender
                tabId = message[ 'tabId' ]

                # decode data
                if ( message[ 'encoding' ] == 'base64' ):
                    rawData = b64decode( message[ 'data' ] )
                elif ( message[ 'encoding' ] == 'ascii' ):
                    rawData = message[ 'data' ].encode()
                else:
                    errorMessage = 'Invalid encoding: ' + message[ 'encoding' ]
                    self.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
                    continue

                # data are split into blocks, join those blocks
                if ( message[ 'lastBlock' ] == 0 ):
                    largeRequests[ message[ 'messageId' ] ] = largeRequests[ message[ 'messageId' ] ] + rawData if ( message[ 'messageId' ] in largeRequests ) else rawData
                    continue
                elif ( message[ 'messageId' ] in largeRequests ):
                    rawData = largeRequests[ message[ 'messageId' ] ] + rawData
                    del( largeRequests[ message[ 'messageId' ] ] )

                # get key, that was used for encryption
                keys = self.getKeyUidFromData( rawData )

                # use only keys that are available
                keys = [ key for key in keys if key in self._passwords ]
                #start_time = time.time()
                t1 = Thread(target = self.decrypt, args = ( rawData, keys, message[ 'messageId' ], tabId ) )
                t1.start()
                # if we have at least one valid key, decrypt data
            elif ( message[ 'type' ] == 'displayWindow' ):
                # User clicked on icon - diplay window
                self.show()
            elif ( message[ 'type' ] == 'getKeysResponse' ):
                # Set new keys
                self._passwords = message[ 'keys' ]
                self._homedir   = message[ 'homedir' ] if 'homedir' in message else None
                self._sudo      = '' if 'sudo' in message and message[ 'sudo' ] else None

app = GnuPG_Decryptor()
app.main()
