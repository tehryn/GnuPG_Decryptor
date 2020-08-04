"""
This module implements GUI for GnuPG_Decryptor broswer extension
"""
from os import getcwd
from PyQt5.QtWidgets import QWidget, QLabel, QBoxLayout, QLineEdit, QCheckBox, QPushButton, QDesktopWidget, QFileDialog
from PyQt5.QtGui import QIcon, QFont

class GnuPG_Decryptor_GUI( QWidget ):
    """
    Main window of application.
    """
    def __init__( self, app, initKeys, sudo, homedir ):
        super().__init__()
        self._backend = app
        self._sudo    = sudo
        self._homedir = homedir
        self.initUI( initKeys )

    def resizeEvent( self, _ ):
        """
        Change size of KeyList when widows is resized
        """
        self._keyList.setMaximumSize( self.width(), self.height() * 0.66 )

    def initUI( self, initKeys ):
        """
        Inits UI (icon, minimum size, widgets, etc)
        """
        self.setWindowIcon( QIcon( './icon/gnupg_256.png' ) )
        self.setWindowTitle( 'GnuPG_Decryptor' )
        self.setMinimumSize( 700, 350 )
        self.center()
        self._keyList   = KeyList( self, initKeys, self._sudo, self._homedir )
        self._refresher = Refresher( self, self._sudo, self._homedir )
        self._backend.debug( str({ 'sudo' : self._sudo, 'home' : self._homedir }) )

        self._layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        self._layout.addWidget( self._keyList )
        self._layout.addWidget( self._refresher )

        self.setLayout( self._layout )
        self.show()

    def center( self ):
        """
        Center itself on screen
        """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter( cp )
        self.move( qr.topLeft() )

    def notifyBackend( self, message ):
        """
        Notifies backend about actions
        """
        if ( message[ 'action' ] == 'refresh' ):
            # refreshes keys
            data = self._backend.keyList( message )
            # if success, display new keys
            if ( data[ 'returnCode' ] == 0 ):
                sudo = message['sudo']['password']    if message[ 'sudo' ][ 'use' ] else None
                home = message['home']['homedir'] if message[ 'home' ][ 'use' ] else None
                self._keyList.newKeys( data[ 'keys' ], sudo, home )
        elif ( message[ 'action' ] == 'confirm' ):
            # confirm changes and closes window
            self._backend.debug( str( message ) )
            self._backend.setPasswords( message )
            self.close()

class KeyList( QWidget ):
    """
    Displaya list of available keys for user.
    """
    def __init__( self, parent, initKeys, sudo, homedir ):
        super().__init__( parent )
        self._parent  = parent
        self._keys    = []
        self._sudo    = sudo
        self._homedir = homedir
        self.initUI()
        self.newKeys( initKeys, sudo, homedir )

    def initUI( self ):
        """
        Inits UI (size, widgets, font, etc)
        """

        font = QFont()
        font.setBold( True )
        header = QLabel( 'Available Keys', self )
        header.setFont( font )
        header.setMaximumHeight( KeyItem.itemHeight() )
        self._layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        self._layout.setSpacing(5)
        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout( self._layout )
        self._layout.addWidget( header )

        self._button = QPushButton( "Confirm" )
        self._button.setMaximumWidth( 80 )
        self._button.clicked.connect( self.confirm )
        self._noKeys = QLabel( 'No keys found.' )

        self._layout.addWidget( self._noKeys )
        self._layout.addWidget( self._button )
        self._layout.addStretch( 1 )


    def confirm( self ):
        """
        Notifies parent if Confirm button is pressed
        """

        keys = list()
        for key in self._keys:
            keys.append( { 'id' : key.getId(), 'password' : key.getPass() } )

        useSudo = 0 if self._sudo    is None else 1
        useHome = 0 if self._homedir is None else 1
        sudo    = self._sudo    if useSudo else ''
        homedir = self._homedir if useHome else ''
        message = { 'action' : 'confirm', 'keys' : keys, 'sudo' : { 'use' : useSudo, 'password' : sudo }, 'home' : { 'use' : useHome, 'homedir' : homedir } }
        self._parent.notifyBackend( message )

    def newKeys( self, keys, sudo = None, homedir = None ):
        """
        Displays new keys fo user
        """

        self._sudo    = sudo
        self._homedir = homedir
        self.clearList()
        if ( keys ):
            self._noKeys.hide()
            for key in keys:
                self.newKey( key )
        else:
            self._noKeys.show()

    def clearList( self ):
        """
        Deletes all items
        """

        for item in self._keys:
            self._layout.removeWidget( item )
            item.deleteLater()
        self._keys = []

    def newKey( self, key ):
        """
        Adds new key into list
        """

        item = KeyItem( key, self )
        self._layout.insertWidget( self._layout.count() - 2, item )
        self._keys.append( item )

class KeyItem( QWidget ):
    """
    Grafic representation of one key.
    """
    @staticmethod
    def itemHeight():
        """
        Returns height of item
        """

        return 20

    @staticmethod
    def itemWidths():
        """
        Returns widths of content
        """

        return [ 420, 300 ]

    def __init__( self, key, parent ):
        super().__init__( parent )
        self._parent = parent
        self._id = key[ 'id' ]
        self.initUI( key[ 'password' ] )

    def initUI( self, password ):
        """
        Inits UI (size, font, widgets, etc.)
        """

        self.setMinimumHeight( KeyItem.itemHeight() )
        self.setMaximumHeight( KeyItem.itemHeight() )
        self._labelId        = QLabel( self._id, self )
        self._labelPassText  = QLabel( 'Password: ', self )
        self._labelPass      = QLineEdit( self )
        self._layout         = QBoxLayout( QBoxLayout.LeftToRight, parent = self )
        self._labelPass.setEchoMode( QLineEdit.Password )
        self._labelPass.setText( password )
        widths = KeyItem.itemWidths()
        self._labelId.setMaximumWidth( widths[0] )
        self._labelId.setMinimumWidth( widths[0] )
        self._layout.addWidget( self._labelId  )
        self._layout.addWidget( self._labelPassText  )
        self._layout.addWidget( self._labelPass  )
        self._layout.addStretch( 1  )
        self._layout.setContentsMargins( 10, 0, 0, 0 )
        self.setLayout( self._layout )

    def getPass( self ):
        """
        Returns password
        """
        return self._labelPass.text()

    def getId( self ):
        """
        Returns uid of key
        """
        return self._id

class Refresher( QWidget ):
    """
    Grafic representation of refresh form.
    """
    def __init__( self, parent, sudo, homedir ):
        super().__init__( parent )
        self.initUI( sudo, homedir )
        self._parent = parent

    def initUI( self, sudo, homedir ):
        """
        Inits UI (size, widgets, fots, etc.)
        """
        font = QFont()
        font.setBold( True )
        header = QLabel( 'Refresh Keys', self )
        header.setFont( font )

        self._sudoWidget = QWidget( self )
        self._sudoWidget.hide()
        sudoLayout = QBoxLayout( QBoxLayout.LeftToRight, parent = self._sudoWidget )
        self._sudoWidget.setLayout( sudoLayout )

        self._homeWidget = QWidget( self )
        self._homeWidget.hide()
        homeLayout = QBoxLayout( QBoxLayout.LeftToRight, parent = self._homeWidget )
        self._homeWidget.setLayout( homeLayout )

        self._sudo = QLineEdit( self._sudoWidget )
        self._sudo.setMinimumWidth( 300 )
        self._sudo.setEchoMode( QLineEdit.Password )

        sudoLabel = QLabel( "sudo:  ", parent = self._sudoWidget )
        sudoLayout.addWidget( sudoLabel )
        sudoLayout.addWidget( self._sudo )
        sudoLayout.addStretch( 1 )
        sudoLayout.setContentsMargins( 0, 0, 0, 0)

        homeLabel  = QLabel( "home:",  parent = self._homeWidget )
        self._homedirLabel = QLineEdit( parent = self._homeWidget )
        self._homedirLabel.setReadOnly( True )
        self._homedirLabel.setMinimumWidth( 300 )

        selectHome = QPushButton( "Change homedir" )
        selectHome.clicked.connect( self.selectDir )
        selectHome.setContentsMargins( 0, 0, 0, 0 )

        homeLayout.addWidget( homeLabel )
        homeLayout.addWidget( self._homedirLabel )
        homeLayout.addWidget( selectHome )
        homeLayout.addStretch( 1 )
        homeLayout.setContentsMargins( 0, 0, 0, 0 )


        self._sudoChck  = QCheckBox( 'Use sudo to access private keys', parent = self )
        self._homeChck  = QCheckBox( 'Use homedir parameter for gpg', parent = self )
        self._sudoChck.toggled.connect( self.toggleChck )
        self._homeChck.toggled.connect( self.toggleChck )

        if ( homedir ):
            self._homedirLabel.setText( homedir )
            self._homeChck.setChecked( True )
        else:
            self._homedirLabel.setText( getcwd() )

        if ( sudo ):
            self._sudo.setText( sudo )
            self._sudoChck.setChecked( True )

        button = QPushButton( "Refresh" )
        button.setMaximumWidth( 80 )
        button.clicked.connect( self.refresh )

        layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        layout.setSpacing(5)
        layout.setContentsMargins( 0, 0, 0, 0 )
        self.setLayout( layout )
        layout.addWidget( header )
        layout.addWidget( self._sudoChck )
        layout.addWidget( self._homeChck )
        layout.addWidget( self._sudoWidget )
        layout.addWidget( self._homeWidget )
        layout.addWidget( button )
        layout.addStretch( 1 )

    def refresh( self ):
        """
        Notifies parent when refresh button is pressed.
        """

        useSudo = self._sudoChck.isChecked()
        sudo    = self._sudo.text() if useSudo else None
        useHome = self._homeChck.isChecked()
        home    = self._homedirLabel.text() if useHome else None
        message = {
            'action' : 'refresh',
            'sudo' : { 'use' : useSudo, 'password' : sudo },
            'home' : { 'use' : useHome, 'homedir'  : home }
        }
        self._parent.notifyBackend( message )

    def selectDir( self ):
        """
        Displays dialogue to selecet directory.
        """

        homedir = QFileDialog.getExistingDirectory( self, "Select GPG Homedir", self._homedirLabel.text(), QFileDialog.ReadOnly )
        if ( homedir ):
            self._homedirLabel.setText( homedir )

    def toggleChck( self ):
        """
        Display/hide sudo and homedir edit lines.
        """

        if ( self._sudoChck.isChecked() ):
            self._sudoWidget.show()
        else:
            self._sudoWidget.hide()

        if ( self._homeChck.isChecked() ):
            self._homeWidget.show()
        else:
            self._homeWidget.hide()
