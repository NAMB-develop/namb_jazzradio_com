import urllib2
import socket
import sys
import ctypes

MediaReadCb = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.c_size_t) # Works!

import edited_vlc as vlc
import threading

class Media(object):

    MediaOpenCb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64))
    MediaReadCb = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.c_size_t)
    MediaSeekCb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint64)
    MediaCloseCb = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)

    def __init__(self, instance, request):
        self.request=request

        self.store=""
        self.storelimit=4096
        self.index=0
        self.cut=0

        def open_cb(opaque, datap, size):
            self.stream=urllib2.urlopen(self.request)
            return 0

        self.ob=Media.MediaOpenCb(open_cb)
        
        def read_cb(opaque, buf, length):
            a=self.index-len(self.store)
            if a < 0:
                to=a*-1 if a*-1 < length else length
                data=self.store[self.index:self.index+to]
                self.index=self.index+to
                for i in range(len(data)):
                    buf[i]=data[i]
                return len(data)
            else:
                data=self.stream.read(length)
                self.store=self.store+data
                self.index=self.index+length
                for i in range(len(data)):
                    buf[i]=data[i]

                if len(self.store) > self.storelimit:
                    diff=len(self.store)-self.storelimit
                    self.cut=self.cut+diff
                    self.store=self.store[:self.storelimit]
                    self.index=self.index-diff
                    
                return len(data)                

        self.rb=Media.MediaReadCb(read_cb)

        def seek_cb(opaque, offset):
            if offset-self.cut < len(self.store) and offset-self.cut > 0:
                self.index=offset-self.cut
                return 0
            else:
                return -1

        self.sb=Media.MediaSeekCb(seek_cb)

        def close_cb(opaque):
            self.stream.close()

        self.cb=Media.MediaCloseCb(close_cb)
        
        self.media=instance.media_new_callbacks(self.ob, #open_cb #Implementation works, but edit of argument of size is weird, plus ListPOINTER does not work.
                                                self.rb, #read_cb
                                                self.sb, #seek_cb
                                                self.cb, #close_cb
                                                None, #opaque
                                                )
    def get_media(self):
        return self.media

##def read_cb(opaque, buf, length):
##    now=time.time()
##    global j
##    while now-j<1:
##        time.sleep(0.5)
##        now=time.time()
##    j=time.time()
##    print("Reading: %r %r %r" % (opaque, buf, length))
##    print("Reading: %r %r %r" % (type(opaque), type(buf), type(length)))
##    print("")
##    data=m.stream.read(length)
##    for i in range(len(data)):
##        buf[i]=data[i]
##    #print("%r" % data[0:2])
##    return len(data)
##
###@MediaCloseCb
##def close_cb(opaque):
##    opaque.stream.close()
##    pass
##
###@MediaOpenCb
##def open_cb(opaque, unknown, number):
##    print("Opening: %s %s %s" % (type(opaque),type(unknown),type(number)))
##    opaque.stream=urllib2.urlopen(opaque.request)
##    return 0
##
###@MediaSeekCb
##def seek_cb(unknown, number):
##    return 0

#read_cb.argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
#read_cb.restype=ctypes.c_ssize_t

#rb=MediaReadCb(read_cb)
#rb=vlc.CallbackDecorators.MediaReadCb(read_cb)

url="http://pub8.jazzradio.com/jr_bossanova_aacplus.flv"
referer='http://www.jazzradio.com/bossanova'

req=urllib2.Request(url)
req.add_header('Referer', referer)
req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36')

i=vlc.Instance('-vvv')
p=i.media_player_new()
global m
m=Media(i, req)
media=m.get_media()
p.set_media(media)
#m.open_stream()
p.play()

##def create_media(vlc_instance, m):
##
##    global t
##    t=ctypes.byref(ctypes.py_object(m))
##    
##    return vlc.libvlc_media_new_callbacks(vlc_instance,
##                                          None,
##                                          rb,
##                                          None,
##                                          None,
##                                          t)
##
##
###http://stackoverflow.com/questions/31250640/using-vlc-imem-to-play-an-h264-video-file-from-memory-but-receiving-error-main/31316867#31316867
###http://stackoverflow.com/questions/20694876/how-can-i-load-a-memory-stream-into-libvlc
##
##
##i=vlc.Instance('-vvv')
##p=i.media_player_new()
##z=create_media(i, m)
##p.set_media(z)
##p.play()



