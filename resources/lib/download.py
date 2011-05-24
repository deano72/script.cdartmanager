import xbmc, xbmcgui
import urllib, sys, re, os
from traceback import print_exc
try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__author__        = sys.modules[ "__main__" ].__author__
__credits__       = sys.modules[ "__main__" ].__credits__
__credits2__      = sys.modules[ "__main__" ].__credits2__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
__useragent__  = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from fanarttv_scraper import get_distant_artists, get_recognized
from database import get_local_artists_db, remote_cdart_list, get_local_albums_db

from pre_eden_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy

# remove comments to save as dharma
#from dharma_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
#from os import remove as delete_file
#exists = os.path.exists
#from shutil import copy as file_copy


pDialog = xbmcgui.DialogProgress()
 
def download_cdart( url_cdart, album, type ):
    xbmc.log( "[script.cdartmanager] - #    Downloading artwork... ", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - #      Path: %s" % repr(album["path"]), xbmc.LOGDEBUG )
    path = album["path"].replace("\\\\" , "\\")
    print type
    pDialog.create( _(32047))
    #Onscreen Dialog - "Downloading...."
    if type == "cdart":
        file_name = "cdart.png"
    elif type == "cover":
        file_name = "folder.jpg"
    elif type == "fanart":
        file_name = "fanart.jpg"
    elif type == "clearart":
        file_name = "clearart.png"
    else:
        xbmc.log( "[script.cdartmanager] - #    Unknown Type ", xbmc.LOGDEBUG )
        message = [ _(32026), _(32025), "File: %s" % path , "Url: %s" % url_cdart]
        return message, False
    destination = os.path.join( addon_work_folder , file_name) # download to work folder first
    download_success = False 
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    try:
        #this give the ability to use the progress bar by retrieving the downloading information
        #and calculating the percentage
        def _report_hook( count, blocksize, totalsize ):
            percent = int( float( count * blocksize * 100 ) / totalsize )
            strProgressBar = str( percent )
            pDialog.update( percent, _(32035) )
            #Onscreen Dialog - *DOWNLOADING CDART*
            if ( pDialog.iscanceled() ):
                pass  
        if exists( path ):
            fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
            message = [_(32023), _(32024), "File: %s" % path , "Url: %s" % url_cdart]
            success = file_copy( destination, os.path.join( path, file_name ) ) # copy it to album folder
            #message = ["Download Sucessful!"]
            # update database
            if type == "cdart":
                c.execute('''UPDATE alblist SET cdart="TRUE" WHERE title="%s"''' % album["title"])
            download_success = True
        else:
            xbmc.log( "[script.cdartmanager] - #  Path error", xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - #    file path: %s" % repr(destination), xbmc.LOGDEBUG )
            message = [ _(32026),  _(32025) , "File: %s" % path , "Url: %s" % url_cdart]
            #message = Download Problem, Check file paths - cdART Not Downloaded]           
        if ( pDialog.iscanceled() ):
            pDialog.close()            
    except:
        xbmc.log( "[script.cdartmanager] - #  General download error", xbmc.LOGDEBUG )
        message = [ _(32026), _(32025), "File: %s" % path , "Url: %s" % url_cdart]
        #message = [Download Problem, Check file paths - cdART Not Downloaded]           
        print_exc()
    conn.commit()
    c.close()
    return message, download_success  # returns one of the messages built based on success or lack of

def cdart_search( cdart_url, id ):
    cdart = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id:
            cdart = item
            print cdart
            break
    return cdart
    
#Automatic download of non existing cdarts and refreshes addon's db
def auto_download():
    xbmc.log( "[script.cdartmanager] -  Autodownload", xbmc.LOGDEBUG )
    try:
        pDialog.create( _(32046) )
        #Onscreen Dialog - Automatic Downloading of cdART
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        d_error=False
        percent = 0
        local_artist = get_local_artists_db()
        distant_artist = get_distant_artists()
        recognized_artists, artists_list = get_recognized( distant_artist, local_artist )
        pDialog.create( _(32046) )
        count_artist_local = len(recognized_artists)
        percent = 0
        for artist in recognized_artists:
            if ( pDialog.iscanceled() ):
                break
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            xbmc.log( "[script.cdartmanager] - #    Artist: %-40s Local ID: %-10s   Distant ID: %s" % (repr(artist["name"]), artist["local_id"], artist["distant_id"]), xbmc.LOGNOTICE )
            local_album_list = get_local_albums_db( artist["name"] )
            remote_cdart_url = remote_cdart_list( artist )
            for album in local_album_list:
                if ( pDialog.iscanceled() ):
                    break
                if not remote_cdart_url:
                    xbmc.log( "[script.cdartmanager] - #    No cdARTs found", xbmc.LOGNOTICE )
                    break
                album_count += 1
                pDialog.update( percent , "%s%s" % (_(32038) , repr(artist["name"]) )  , "%s%s" % (_(32039) , repr(album["title"] )) )
                name = artist["name"]
                title = album["title"]
                xbmc.log( "[script.cdartmanager] - #     Album: %s" % repr(album["title"]), xbmc.LOGNOTICE )
                if album["cdart"] == "FALSE":
                    musicbrainz_albumid = album["musicbrainz_albumid"]
                    if not musicbrainz_albumid:
                        continue
                    cdart = cdart_search( remote_cdart_url, musicbrainz_albumid )
                    if cdart["picture"]: 
                        xbmc.log( "[script.cdartmanager] - #            ALBUM MATCH FOUND", xbmc.LOGNOTICE )
                        #xbmc.log( "[script.cdartmanager] - test_album[0]: %s" % test_album[0], xbmc.LOGNOTICE )
                        message, d_success = download_cdart( cdart["picture"] , album, "cdart" )
                        if d_success == 1:
                            download_count += 1
                            album["cdart"] = "TRUE"
                        else:
                            xbmc.log( "[script.cdartmanager] - #  Download Error...  Check Path.", xbmc.LOGNOTICE )
                            xbmc.log( "[script.cdartmanager] - #      Path: %s" % repr(album["path"]), xbmc.LOGNOTICE )
                            d_error = True
                    else :
                        xbmc.log( "[script.cdartmanager] - #            ALBUM MATCH NOT FOUND", xbmc.LOGNOTICE )
                else:
                    cdart_existing += 1
                    xbmc.log( "[script.cdartmanager] - #            cdART file already exists, skipped..."    , xbmc.LOGNOTICE )
        pDialog.close()
        if d_error:
            xbmcgui.Dialog().ok( _(32026), "%s: %s" % ( _(32041), download_count ) )
        else:
            xbmcgui.Dialog().ok( _(32040), "%s: %s" % ( _(32041), download_count ) )
        return
    except:
        print_exc()