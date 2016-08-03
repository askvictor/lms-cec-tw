import sys
import json

from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.web import server, resource
from twisted.python import log
from twisted.internet import reactor
#import cec

from future.standard_library import install_aliases
install_aliases()

from urllib.parse import unquote

config = {
    'lms_server': '192.168.1.11',  # IP of your Squeeze Server
    'lms_port': 9090,  # network control port (usually 9090)
    'player_mac': '00:04:20:e8:60:a1',  # the MAC address of your squeezebox (or fake MAC if using squeezelite)
    'cec_output': 5,  # the device which we will switch on, and set the input to cec_input
    'cec_input': 1,  # the device which will play (e.g. the raspberry pi) this probably changes vendor to vendor, play around with it
    'default_volume': 80,  # the volume set on the squeezebox. If set, the volume will always revert to this and
                           # HDMI will be used for volume. If not set, will use squeezebox vol instead of HDMI
}


class LMSClient(Protocol):
    def connectionMade(self):
        #cec.init()
        #cec.list_devices()  # necessary for volume to work

        log.msg('connected; intialising CEC and subscribing to playlist and mixer')
        self.transport.write('subscribe playlist,mixer\n')

    def dataReceived(self, data):
        command = unquote(data.decode().strip()).split()
        log.msg("Command received %s" % command)
        if command[0] == config['player_mac'] and command[1] == 'playlist':
            if command[2] == 'play' or (command[2] == 'pause' and command[3] == '0'):
                log.msg("play command received")
                #receiver = cec.Device(config['cec_output'])
                if not receiver.is_on():
                    if receiver.power_on():
                        log.msg("turned receiver on")
                    else:
                        log.msg("couldn't turn receiver on")
                if receiver.set_av_input(config['cec_input']):
                    log.msg("set input on receiver")
                else:
                    log.msg("couldn't set input on receiver")
        if 'default_volume' in config:
            if command[0] == config['player_mac'] and command[1] == 'mixer' and command[2] == 'volume':
                if command[3][0] == '+':
                     log.msg("volume up")
                     self.transport.write(b'%s mixer volume %s\n' % (config['player_mac'], config['default_volume']))
                     #cec.volume_up()
                elif command[3][0] == '-':
                     log.msg("volume down")
                     self.transport.write(b'%s mixer volume %s\n' % (config['player_mac'], config['default_volume']))
                     #cec.volume_down()


class LMSClientFactory(ReconnectingClientFactory):
    def buildProtocol(self, addr):
        log.msg('Connected.')
        log.msg('Resetting reconnection delay')
        self.resetDelay()
        return LMSClient()


class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        if request.path == "/vol_up":
            cec.volume_up()
        elif request.path == "/vol_down":
            cec.volume_down()
        response_data = {}
        request.setResponseCode(200)
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        return json.dumps(response_data)

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    reactor.connectTCP(config['lms_server'], config['lms_port'], LMSClientFactory())
    root = resource.Resource()
    root.putChild("vol_up", Simple())
    root.putChild("vol_down", Simple())
    site = server.Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()