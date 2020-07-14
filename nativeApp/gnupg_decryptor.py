"""
Author: Jiri Matejka
Description: This module is native application of GnuPG_Decryptor broswer extension.
"""
#!/usr/bin/python3 -u

# Note that running python with the `-u` flag is required on Windows,
# in order to ensure that stdin and stdout are opened in binary, rather
# than text, mode.

import json
import sys
import struct
import base64
import subprocess
import magic
from PyQt5.QtWidgets import QApplication
from GUI import GnuPG_Decryptor_GUI

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

    def show( self ):
        """
        Method displays GUI window for user
        """

        # If Gui is not defined yet, construct it
        if( self._gui is None ):
            self._QApp = QApplication( sys.argv )
            initKeys = []
            for keyId, password in self._passwords:
                initKeys.append( { 'id' : keyId, 'password' : password } )
            self._gui  = GnuPG_Decryptor_GUI( self, initKeys )

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
        process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        stdout, _ = process.communicate( stdin.encode() )
        retcode = process.returncode
        ids    = []

        # if success
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            uids   = [ line[3:].strip() for line in stdout if line.startswith( 'uid' ) ]
            for line in uids:
                idx = line.find( ' ' )
                ids.append( { 'id' : line[ idx + 1 : ], 'password' : '' } )

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
        process   = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        stdout, _ = process.communicate()
        retcode   = process.returncode
        uid       = None

        # if success
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            uids   = [ line[3:].strip() for line in stdout if line.startswith( 'uid' ) ]
            if ( uids ):
                uid = uids[0]
                idx = uid.find( ' ' )
                uid = uid[ idx + 1 : ]
        return uid

    def getKeyUidFromData( self, data ):
        """
        Method finds out, which keys were used for data encryption.
        """

        # command line arguments
        args = [ 'gpg', '-d', '--list-only' ]

        # call gpg
        process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        _, stderr = process.communicate( data )
        retcode = process.returncode
        keys  = []

        # if success
        if ( retcode == 0 ):
            # output is on stderr
            stderr   = stderr.decode().splitlines()
            # we care only about lines starting with "gpg: encrypted"
            filtered = [ line for line in stderr if line.startswith( 'gpg: encrypted' )  ]
            for line in filtered:
                # find where ID/fingerprint is
                idx1 = line.find( ', ID' ) + 5
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
        message_length = struct.unpack( '=I', raw_length )[0]
        message = sys.stdin.buffer.read( message_length ).decode( "utf-8" )
        return json.loads( message )


    @staticmethod
    def encode_message( message_content ):
        """
        Encode a message for transmission, given its content.
        """

        encoded_content = json.dumps( message_content ).encode( "utf-8" )
        encoded_length  = struct.pack( '=I', len( encoded_content ) )
        return { 'length' : encoded_length, 'content' : struct.pack( str( len(encoded_content ) ) + "s", encoded_content ) }


    @staticmethod
    def send_message( encoded_message ):
        """
        Sends an encoded message to background script.
        """

        sys.stdout.buffer.write( encoded_message[ 'length' ] )
        sys.stdout.buffer.write( encoded_message[ 'content' ] )
        sys.stdout.buffer.flush()

    @staticmethod
    def debug( messageString ):
        """
        Sends debug message to background script
        """
        GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'message' : messageString, 'type' : 'debug' } ) )

    @staticmethod
    def loadKeys():
        """
        Asks background scripts for stored keys.
        """
        GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'type' : 'getKeysRequest' } ) )

    def updateKeys( self ):
        """
        Update keys in background scripts
        """
        GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'type' : 'updateKeysRequest', 'keys' : self._passwords } ) )

    def main( self ):
        """
        Reads messages from background scripts and create responses.
        """

        mimeResolver     = magic.Magic( mime=True )
        largeRequests    = dict()
        MAX_MESSAGE_SIZE = 750 * 1024

        # load stored keys
        GnuPG_Decryptor.loadKeys()
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
                    rawData = base64.b64decode( message[ 'data' ] )
                elif ( message[ 'encoding' ] == 'ascii' ):
                    rawData = message[ 'data' ].encode()
                else:
                    errorMessage = 'Invalid encoding: ' + message[ 'encoding' ]
                    GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
                    continue

                # data are split into blocks, join those blocks
                if ( message[ 'lastBlock' ] == 0 ):
                    largeRequests[ message[ 'messageId' ] ] = largeRequests[ message[ 'messageId' ] ] + rawData if ( message[ 'messageId' ] in largeRequests ) else rawData
                    continue
                elif ( message[ 'messageId' ] in largeRequests ):
                    rawData = largeRequests[ message[ 'messageId' ] ] + rawData
                    GnuPG_Decryptor.debug( 'Message is commplete' )
                    del( largeRequests[ message[ 'messageId' ] ] )

                # get key, that was used for encryption
                keys = self.getKeyUidFromData( rawData )

                # use only keys that are available
                keys = [ key for key in keys if key in self._passwords ]

                # if we have at least one valid key, decrypt data
                if ( keys ):
                    args     = []
                    sudoPass = ''
                    keyPass  = self._passwords[ keys[0] ]

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
                        args.append( '--pinentry-mode=loopback' )
                        args.append( '--passphrase' )
                        args.append( keyPass )

                    # decrypt command for gpg
                    args.append( '--decrypt' )

                    # call subprocess
                    process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                    decrypted, err = process.communicate( sudoPass.encode() + rawData )
                    retcode = process.returncode

                    # if decryption failed
                    if ( retcode != 0 ):
                        errorMessage = 'Unable to decrypt data: ' + err.decode()
                        GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
                        continue

                    # get mimeType of data
                    mimeType  = mimeResolver.from_buffer( decrypted )

                    # encode data using base64
                    decrypted = base64.b64encode( decrypted )

                    # split data into blocks
                    blocks    = [ decrypted[ i : i + MAX_MESSAGE_SIZE ] for i in range( 0, len( decrypted ), MAX_MESSAGE_SIZE ) ]

                    # get last block of data
                    lastBlock = blocks.pop()

                    # prepare response
                    response  = { 'messageId' : message[ 'messageId' ], 'success' : 1, 'message' : '', 'type' : 'decryptResponse', 'data' : '', 'encoding' : 'base64', 'mimeType' : mimeType, 'lastBlock' : 0, 'tabId' : tabId }

                    # send all blocks, except last one
                    for block in blocks:
                        response[ 'data' ]  = block.decode()
                        GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( response ) )

                    # send last blocks
                    response[ 'data' ]      = lastBlock.decode()
                    response[ 'lastBlock' ] = 1
                    GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( response ) )
                else:
                    errorMessage = 'Unable to decrypt data: Required key is not present'
                    GnuPG_Decryptor.send_message( GnuPG_Decryptor.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
            elif ( message[ 'type' ] == 'displayWindow' ):
                # User clicked on icon - diplay window
                self.show()
            elif ( message[ 'type' ] == 'getKeysResponse' ):
                # Set new keys
                self._passwords = message[ 'keys' ]

app = GnuPG_Decryptor()
app.main()
