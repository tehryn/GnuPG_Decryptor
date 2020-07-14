/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

const encoder = new TextEncoder();
var browser = browser || chrome;

// Maximum size of data part of message (Maximum size of single message is 4 GiB)
let MAX_MESSAGE_SIZE = 3 * 1024 * 1024 * 1024; // 3 GiB

// Id counter for elements
let elemId   = 0;

// Stores decrypted blocks
let blocks   = {};

// Stores URLs to decrypted files and content of decrypted texts
let cache    = {};

// Stores Id of tab
let tabId    = undefined;

// Stores types of sent messages
let types    = {};

// Listen to messages from background script
browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        // Message containts decrypted content - replace encrypted element with decrypted one
        if ( message.type === "decryptResponse" ) {
            // Decryption was successful
            if ( message.success === 1 ) {
                // Decrypted data were seperated into blocks - load all blocks
                if ( message.lastBlock === 0 ) {
                    if ( typeof blocks[ message.messageId ] === 'undefined' ) {
                        blocks[ message.messageId ] = message.data;
                    }
                    else {
                        blocks[ message.messageId ] += message.data;
                    }
                }
                else {
                    // last block of data is received -- append it to blocks[ message.messageId ]
                    if ( typeof blocks[ message.messageId ] !== 'undefined' ) {
                        message.data = blocks[ message.messageId ] + message.data;
                    }

                    // Get the encrypted element
                    let elem = document.getElementById( message.messageId );
                    if ( types[ message.messageId ] == 'text' ) {
                        // If text was encrypted, we replace it with decrypted one

                        // compute hash from encrypted text, so we can find out, if there are more elements with same encrypted content
                        let text = elem.innerHTML.trim();
                        let hash = stringToHash( text );
                        if ( message.encoding == 'base64' ) {
                            cache[ hash ].data =  decodeURIComponent(escape(window.atob( message.data )));
                        }
                        else {
                            cache[ hash ].data = message.data;
                        }
                        cache[ hash ].status = 'decrypted';

                        // replace all encrypted elements with decrypted data
                        cache[ hash ].elements.forEach(
                            function ( id, index ) {
                                elem = document.getElementById( id );
                                elem.innerHTML = cache[ hash ].data;
                            }
                        );
                    }
                    else if ( types[ message.messageId ] == 'file' ) {
                        // If file is encrypted, we need to update URL to it
                        // We start with creatig BLOB from data
                        let blob  = new Blob( [ base64ToArrayBuffer( message.data ) ], { type : message.mimeType } );
                        // Then we create URL to BLOB
                        let url = URL.createObjectURL( blob );

                        // And we update all src attributes poiting to encrypted file with url pointing to decrypted one
                        cache[ elem.src ].url    = url;
                        cache[ elem.src ].status = 'decrypted';
                        cache[ elem.src ].elements.forEach(
                            function ( id, index ) {
                                elem = document.getElementById( id );
                                elem.src = url;
                                // Audio and Video need to be reloaded
                                if ( elem.parentNode && ( elem.parentNode.tagName === 'VIDEO' || elem.parentNode.tagName === 'AUDIO' ) ) {
                                    elem.parentNode.load();
                                }
                            }
                        );
                    }
                }
            }
        }
        else if ( message.type === "tabIdResponse" ) {
            // Message containts new ID
            tabId = message.tabId;
        }
    }
);

// we ask for new ID
setTabId();
// and wait, until we get it
setTimeout( checkTabId, 100 );
function checkTabId() {
    if ( tabId !== undefined ) {
        // once we have an ID, we can send all encrypted data to native application
        main();
    }
    else {
        setTabId();
        setTimeout( checkTabId, 100 );
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Generates new id for an element (and message)
 * @return {STRING} New id of an element (and message)
 */
function getId() {
    let newId = 'GnuPG_DecryptorElemId-' + elemId++;
    while ( document.getElementById( newId ) ) {
        newId = 'GnuPG_DecryptorElemId-' + elemId++;
    }

    return newId;
}

/**
 * Sends request for new ID to background script
 */
function setTabId() {
    sendMessage( { 'type' : 'tabIdRequest' } );
}

/**
 * Connects mutation observer to document, detects all encrypted elements and sends it to native application
 */
function main() {
    let mutObservConfig = { attributes : true, attributeFilter : [ 'src' ], childList : true, subtree : true };
    let mutObserver = new MutationObserver(
        function( mutatuinList, observer ) {
            for ( let mutation of mutatuinList ) {
                if ( mutation.type !== 'attributes' ) {
                    let elements = getElements( mutation.target );
                    parseElements( elements );
                }
            }
        }
    );
    mutObserver.observe( document.documentElement, mutObservConfig );
    let elements = getElements( document.documentElement );
    parseElements( elements );
}

/**
 * Parse all encrypted elements and sends them to native application.
 * @param  {ARRAY} elements List of encrypted elements.
 */
function parseElements( elements ) {
    elements.forEach(
        function( elem, index ) {
            // Id element has no Id, generate one
            let id = elem.data.id;
            if ( !elem.data.id ) {
                elem.data.id = id = getId();
            }

            if ( elem.type === 'file' ) {
                // We are parsing encrypted file, so we try if we already parsed one
                if ( cache[ elem.data.src ] === undefined ) {
                    // File is not in cache, so we create an entry
                    file = elem.data;
                    cache[ file.src ] = { 'status' : 'creatingRequset', 'type' : 'file', 'url' : elem.data.src, 'elements' : [ id ] };

                    // We need to load content of the file
                    let reader = new FileReader();

                    // Once content is loaded, we send it to native application
                    reader.onload = function( event ) {
                        let encrypted = arrayBufferToBase64( event.target.result );
                        let message   = { 'data' : encrypted, 'type' : 'decryptRequest', encoding : 'base64', messageId : id };
                        types[ id ] = 'file';
                        sendMessage( message );
                        cache[ elem.data.src ].status = 'decrypting';
                    };

                    // We read the file as array buffer
                    getFile( elem.data.preParsedData ? elem.data.preParsedData : file.src, 'blob' ).then(
                        function( data ) {
                            reader.readAsArrayBuffer( data );
                        }
                    );
                }
                else {
                    // File is already beeing processed
                    if ( cache[ elem.data.src ].status === 'decrypted' ) {
                        // If decrypted content is ready, we update URL
                        elem.data.src = cache[ elem.data.src ].url;
                        cache[ elem.data.src ].elements.push( id );
                    }
                    else {
                        // Otherwise we add id, so URL will be updated once we receive decrpted content
                        cache[ elem.data.src ].elements.push( id );
                    }
                }
            }
            else if ( elem.type == 'text' ) {
                // We are parsing encrypted text
                data = elem.data.preParsedData ? elem.data.preParsedData : elem.data.innerHTML.trim();

                // Generate hash and check, if we already parsed such text
                hash = stringToHash( data );
                if ( cache[ hash ] === undefined ) {
                    // This is the first time we are parsing this text
                    types[ id ] = 'text';
                    cache[ hash ] = { 'status' : 'decryptRquest', 'type' : 'text', 'data' : data, 'elements' : [ id ] };
                    sendMessage( { 'data' : data, 'type' : 'decryptRequest', encoding : 'ascii', messageId : id } );
                }
                else {
                    // Same text was already parsed
                    if ( cache[ hash ].status === 'decrypted' ) {
                        elem.data.innerHTML = cache[ hash ].data;
                        cache[ hash ].elements.push( id );
                    }
                    else {
                        cache[ hash ].elements.push( id );
                    }
                }
            }

        }
    );
}

/**
 * Finds all encrypted elements that are childs of specified root
 * @param  {DOM ELEMENT OBJECT} root Root of DOM where encrypted elements will seeked
 * @return {ARRAY}                   List of all encrypted elements
 */
function getElements( root ) {
    let arr = [];
    let iterator = document.createNodeIterator( root, NodeFilter.SHOW_ELEMENT );
    let node   = root;
    //let armouredRegex = new RegExp( '^-----BEGIN PGP MESSAGE(, PART [1-9][0-9]*(\/[1-9][0-9]*)?)?-----[aA-zZ|0-9|\\/+=\r\n]+-----END PGP MESSAGE-----$' );
    let armouredRegex = new RegExp( '^-----BEGIN PGP MESSAGE-----[aA-zZ|0-9|\\/+=\\r\\n]+-----END PGP MESSAGE-----$' );

    while ( node ) {
        text = node.innerHTML.trim();
        if ( node.hasAttribute( 'src' ) && ( node.src.toLowerCase().endsWith( '.gpg' ) || node.src.toLowerCase().endsWith( '.asc' ) ) ) {
            arr.push( { 'data' : node, 'type' : 'file', 'preParsedData' : null } );
        }

        if ( node.children.length == 0 && text.startsWith( '-----BEGIN PGP MESSAGE-----' ) && text.match( armouredRegex ) ) {
            arr.push( { 'data' : node, 'type' : 'text', 'preParsedData' : text } );
        }

        node = iterator.nextNode();
    }
    return arr;
}

/**
 * Downloads file from specified URL
 * @param  {STRING} url  URL to file
 * @param  {STRING} type Requested type of response
 * @return {PROMISE}     Promise
 */
function getFile( url, type ) {
    return new Promise(
        function( resolve, reject ) {
            try {
                let xhr = new XMLHttpRequest();
                xhr.open( 'GET', url );
                xhr.responseType = type;
                xhr.onerror = function() {
                    reject( 'Network error.' );
                };
                xhr.onload = function() {
                    if ( xhr.status === 200 ) {
                        resolve( xhr.response );
                    }
                    else {
                        reject( 'Loading error:' + xhr.statusText );
                    }
                };
                xhr.send();
            }
            catch( err ) {
                reject( err.message );
            }
        }
    );
}

/**
 * Converts array buffer to base64
 * @param  {ARRAY BUFFER} buffer Buffer that will be converted
 * @return {STRING}              BASE64 string
 */
function arrayBufferToBase64( buffer ) {
    var binary = '';
    var bytes = new Uint8Array( buffer );
    var len = bytes.byteLength;
    for (var i = 0; i < len; i++) {
        binary += String.fromCharCode( bytes[ i ] );
    }
    return window.btoa( binary );
}

/**
 * Converts base64 string to array buffer
 * @param  {STRING} base64 base64 string that will be converted
 * @return {ARRAY BUFFER}         Array buffer representation of base64 string
 */
function base64ToArrayBuffer( base64 ) {
    let binary_string = window.atob( base64 );
    let len = binary_string.length;
    let bytes = new Uint8Array( len );
    for (let i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt( i );
    }
    return bytes.buffer;
}

/**
 * Sends message to background script
 * @param  {Object} message Message that will be sent
 */
function sendMessage( message ) {
    message.tabId = tabId;
    if ( message.type === 'decryptRequest' ) {
        let dataSize   = message.data.length;
        // If message is too big, split its data into blocks
        if ( dataSize > MAX_MESSAGE_SIZE ) {
            let dataBlocks = splitString( message.data );
            dataBlocks.forEach(
                function( data, index ) {
                    message.data = data;
                    message.lastBlock = ( index + 1 == dataBlocks.length ) ? 1 : 0;
                    browser.runtime.sendMessage( message );
                }
            );
        }
        else {
            message.lastBlock = 1;
            browser.runtime.sendMessage( message );
        }
    }
    else {
        message.lastBlock = 1;
        browser.runtime.sendMessage( message );
    }
}

/**
 * Split string into blocks with maximum size of MAX_MESSAGE_SIZE
 * @param  {STRING} string String that will be split
 * @return {ARRAY}         Array of strings
 */
function splitString( string ) {
    let result = [];
    let steps  = Math.ceil( string.length / MAX_MESSAGE_SIZE );
    for( let i = 0; i < steps; i++ ) {
        result.push( string.substring( i * MAX_MESSAGE_SIZE, ( i + 1 ) * MAX_MESSAGE_SIZE ) );
    }
    return result;
}

/**
 * Computes hash of string
 * @param  {STRING} str Input string
 * @return {STRING}     Result hash
 */
function stringToHash( string ) {
    let hash = 0;

    for ( i = 0; i < string.length; i++ ) {
        hash = ( ( ( hash << 5 ) - hash ) + string.charCodeAt( i ) ) | 0;
    }

    return '' + hash;
}