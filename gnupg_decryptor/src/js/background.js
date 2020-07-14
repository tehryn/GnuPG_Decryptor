/*
 * Author: Jiri Matejka
 * Decription: background.js is background script for GnuPG_Decryptor extension. Purpose of this script is to manage communication with native application and browser extension.
 */

/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

var browser     = browser || chrome;
var keys        = {};

// Connects to native application
let port = browser.runtime.connectNative( "GnuPG_Decryptor" );

// Listens to messages from native application.
port.onMessage.addListener(
    ( message ) => {
        // Message contains decrypted content - forward it to content script
        if ( message.type === 'decryptResponse' ){
            console.log( message );
            browser.tabs.sendMessage( message.tabId, message, null );
        }
        // Message contains debug information - log it into console
        else if ( message.type === 'debug' ) {
            console.log( message );
        }
        // List of keys need to be update it - store it
        else if ( message.type === 'updateKeysRequest' ) {
            keys = message.keys;
        }
        // Native application require list of keys
        else if ( message.type === 'getKeysRequest' ) {
            response = { 'type' : 'getKeysResponse', 'keys' : keys };
            port.postMessage( response );
        }
    }
);

// Listens to messages from content script
browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        // Message contains encrypted content - forward it to native application
        if ( message.type === "decryptRequest" ) {
            port.postMessage( message );
        }
        // Content scrips wants to know its id for future communication - give it its id
        else if ( message.type === "tabIdRequest" ) {
            browser.tabs.sendMessage( sender.tab.id, { 'type' : 'tabIdResponse', 'tabId' : sender.tab.id }, null );
        }
    }
);

// Listens when user clicked on icon
browser.browserAction.onClicked.addListener(
    function() {
        // Inform native application about event
        port.postMessage( { 'type' : 'displayWindow' } );
    }
);