import urllib2
import socket

import ctypes
import Queue

q=None

def create_request():
    req=urllib2.Request("http://pub8.jazzradio.com/jr_pariscafe_aacplus.flv")
    req.add_header('Referer','http://www.jazzradio.com/pariscafe')
    req.add_header('User-Agent',"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36")
    return req

def create_stream(req):
    return urllib2.urlopen(req)

def create_request_core():
    s=socket.socket()
    return s

def create_stream_core(s):
    s.connect(("pub8.jazzradio.com",80))
    req=[
        'GET /jr_vocallegends_aacplus.flv HTTP/1.1',
        'Host: www.jazzradio.com',
        'Referer: http://www.jazzradio.com/vocallegends',
        'User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
        'Connection: keep-alive',
        '',
        ''
        ]
    s.send("\r\n".join(req))
    return s
    

from streamutil import *

packets=[None]*1024

import threading

class Streamer(object):

    def __init__(self, event, packets):
        self.packets=packets
        self.event=event
        self.stopper=threading.Event()
        self.thread=None
        self.started=False
        #self.f=open("stream%s.bin"%str(self.stopper),'wb')

    def stop(self):
        print("Stopping thread")
        self.stopper.set()
        self.event.clear()
        self.started=False
        self.stream.close()
        while not self.packets.empty():
            self.packets.get()

    def start(self):
        print("Starting thread")
        self.stopper=threading.Event()
        self.event.clear()
        self.started=True
        self.thread=threading.Thread(target=self.run)
        self.thread.daemon=True
        self.thread.start()
        

    def run(self):
        self.stream=create_stream_core(create_request_core())
        self.start_time=int(time.time())
        http_header=self.stream.recv(129)
        header=self.stream.recv(9)
        self.packets.put(["","","","","","",header])
        print("%r"%header)
        chunk=""
        index=0
        last_suc=None
        while not self.stopper.is_set():
            d=self.stream.recv(8196)
            chunk=chunk+d
            if chunk:
                if "adswizz" in chunk:
                    print("Ad coming up")
                    self.event.set()
                while True:
                    p=process_packet(chunk)
                    pdata="".join(filter(None, p))
                    if p[-1]:
                        i=len(pdata)
                        last_suc=p
                        self.packets.put(p)
                        chunk=chunk[i:]
                    else:
                        if p[1]:
                            if not p[1] in at:
                                print("Corrupted packet: %r\n%r"%(p,pdata))
                                c=chunk[0:1]
                                chunk=chunk[1:]
                                pp=process_packet(chunk)
                                if pp[-1]:
                                    pp[-2]=c+pp[-2]
                                    i=pp[-1]
                                    self.packets.put(pp)
                                    chunk=chunk[i+1:]                                
                                else:
                                    print("Fail after retry: %r"%pp)
                                    print("From chunk: %r"%chunk)
                                    print("Last succesful: %r"%last_suc)
                                    raise IOError
                                break
                            break
                        else:
                            break
        self.stream.close()

import Queue, subprocess, time, sys

def get_time(s1):
    return struct.unpack(">I",s1[3]+s1[0:3])[0]
    #return int((s1[3]+s1[0:3]).encode('hex'), 16)

def get_string(t1):
    s1=struct.pack(">I", t1)
    return s1[1:]+s1[0]

def transform_time(t1, offset):
    i_t1=get_time(t1)
    i_t2=i_t1+offset
    return get_string(i_t2)


def read(queue):
    data=part
    while len(data) < length:
        data=data+queue.get()
    if len(data) > length:
        part=data[length:]
    return data[:length]

instance=None

class Worker(object):

    def __init__(self, event=None):
        self.ad_event1=threading.Event()
        self.buffer1=Queue.Queue()
        self.s1=Streamer(self.ad_event1, self.buffer1)
        self.ad_event2=threading.Event()
        self.buffer2=Queue.Queue()
        self.s2=Streamer(self.ad_event2, self.buffer2)
        self.current=self.buffer1
        self.debug=False
        self.debug_en=True
        #self.debug_break=True
        self.ad_switch=True
        self.t_prev_ad=time.time()
        self.songchanges=Queue.Queue()

        self.q=Queue.Queue()


        MediaOpenCb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint64)) # The last argument seems to be some sort of buffer size thing.
        MediaReadCb = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.c_size_t)
        MediaSeekCb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint64)
        MediaCloseCb = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)

        def opaque_to_pyobj(opaque):
            return ctypes.cast(opaque,ctypes.POINTER(ctypes.py_object)).contents.value


        def open_cb(opaque, datap, length):
            m=opaque_to_pyobj(opaque)
            import urllib2
            m.stream=urllib2.urlopen(m.request)
            datap.contents.value=opaque
            length.contents.value=4096
            return 0
                
        def read_cb(opaque, buf, length):
            m=opaque_to_pyobj(opaque)
            a=m.index-len(m.store)
            if a < 0:
                #The index position is at a position in store.
                to=a*-1 if a*-1 < length else length
                data=m.store[m.index:m.index+to]
                m.index=m.index+to
            else:
                #The index position is at a position in data we need to get.
                data=self.part
                while len(data) < length:
                    data=data+self.q.get()
                if len(data) > length:
                    self.part=data[length:]
                    data=data[:length]
                m.store=m.store+data
                m.index=m.index+length

                if len(m.store) > m.storelimit:
                    diff=len(m.store)-m.storelimit
                    m.cut=m.cut+diff
                    m.store=m.store[:m.storelimit]
                    m.index=m.index-diff
                    
            for i in range(len(data)):
                buf[i]=data[i]
            print("%r %r" % (len(data), length))
            return len(data)

        def seek_cb(opaque, offset):
            m=opaque_to_pyobj(opaque)
            #The offset is absolute, therefore we need to adjust it for the bytes we cut off.
            if offset-m.cut < len(m.store) and offset-m.cut > 0:
                m.index=offset-m.cut
                return 0
            else:
                return -1

        def close_cb(opaque):
            m=opaque_to_pyobj(opaque)
            
            m.store=""
            m.part=""


        self.request=create_request()
        self.ob=MediaOpenCb(open_cb)
        self.rb=MediaReadCb(read_cb)
        self.sb=MediaSeekCb(seek_cb)
        self.cb=MediaCloseCb(close_cb)
        self.ref=ctypes.cast(ctypes.pointer(ctypes.py_object(self)), ctypes.c_void_p)
        self.store=""
        self.storelimit=4096
        self.index=0
        self.cut=0
        self.part=""


    def get_media(self):
        return self.media


    def start_vlc_imem(self):
        import sys, os
        sys.path.insert(0, os.path.join("..","..",".."))

        import extensions
        extensions.load_extension("vlc")
        
        self.instance=extensions.get_extension("vlc").Instance('-vvv')
        self.player=self.instance.media_player_new()

        


    def process_v2_imem(self):
        try:
            self.p=self.streamers[self.cur].packets.get(True, 5)
        except Queue.Empty:
            print("Empty queue for longer than 5 seconds!")
            return
        if self.p[3] and len(self.p[3]) == 4:
            self.p[3]=transform_time(transform_time(self.p[3],-1*self.offset_start), self.offset)
        data="".join(filter(None, self.p))
        self.q.put(data)
        #print("Writing")
        #self.f.write(data)
        if "onMetaData" in self.p[5]:
            d=read_metadata(self.p[5])
            if "tlPreciseTime" in d and "StreamTitle" in d:
                correctedtime=self.streamers[self.cur].start_time+int(d["tlPreciseTime"])
                self.songchanges.put((correctedtime, d["StreamTitle"]))
            print(d)
            return True
        return False        
            
    def run_repeatable(self):
        self.streamers=[self.s1, self.s2]
        self.cur=0
        self.streamers[self.cur].start()
        self.startuptime=int(time.time())
        self.proc=self.start_vlc_imem()
        self.media=self.instance.media_new_callbacks(self.ob, #open_cb
                                                self.rb, #read_cb
                                                self.sb, #seek_cb
                                                self.cb, #close_cb
                                                self.ref, #opaque
                                                )
        self.player.set_media(self.get_media())
        self.player.play()
        adcoming=False
        self.delay=30
        self.offset=0
        self.offset_start=0
        self.p=None
        self.slowdown=False
        self.stdinwrite_speed=0

        while True:
            self.delayer = time.time()-self.t_prev_ad > self.delay
            self.trackswitch = self.process_v2_imem()
            #if self.ad_switch and self.delayer and self.streamers[self.cur].event.is_set():
            if self.trackswitch:
                self.streamers[self.cur].event.clear()
                self.t_prev_ad=time.time()
                print("Ad!")
                self.prospect=self.cur+1 if self.cur < len(self.streamers)-1 else 0
                if self.cur==self.prospect:
                    print("Current and prospect streamers appear to be the same object.")
                self.streamers[self.prospect].start()
                self.streamers[self.prospect].packets.get(True)
                self.streamers[self.prospect].packets.get(True)
                self.p2=self.streamers[self.prospect].packets.get(True)
                tries=0
                maxtries=500
                while tries<maxtries:
                    #Currently the fastest: 160:
                    tries=tries+1
                    if self.p[5]==self.p2[5]:
                        print("Switching to thread %s. Succesful in %s tries" % (self.prospect, tries))
                        self.streamers[self.cur].stop()
                        self.cur=self.prospect
                        self.offset=get_time(self.p[3])
                        self.offset_start=get_time(self.p2[3])
                        break
                    else:
                        #print("Not similar, rechecking...\n%r\n%r"%(p[5],p2[5]))
                        self.p2=self.streamers[self.prospect].packets.get(True)
                        #p2=self.buffer2.get(True)
                        #process()
                if not tries<maxtries:
                    print("Failed to interlace stream in thread %s..." % self.prospect)
                    self.streamers[self.prospect].stop()

        #self.streamers[self.current].stop()
        self.proc.kill()

   
w=Worker()
w.run_repeatable()        

        
