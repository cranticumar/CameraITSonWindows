#=================================================================================================
# Copyright (c) 2014-2015 Qualcomm Technologies, Inc. All Rights Reserved.
# Qualcomm Technologies Proprietary and Confidential.
#=================================================================================================
# @file  SetDimmer.py
# @brief Python file for setting the dimmer on graybox
#=================================================================================================

import sys, serial, os, platform, getopt, string, time
import subprocess, re
from optparse import OptionParser

lux_value = sys.argv[1]
actual_values = {'1450lux': '0', '1000lux': '56', '500lux': '77', '300lux': '86', '100lux': '100','50lux': '106','20lux': '110','0lux': '128'}

if lux_value in actual_values.keys():
   print "Setting the luminance to "+lux_value
else:
   print "Please select a standard lux value, Exiting now"
   sys.exit(5)


class acDimControlAPI():
   def __init__( self ):
      # options available
      self.parser = OptionParser()
      self.parser.add_option( "--verbose", dest = "verbose", help = "Show communication (yes or no )." )
      self.verbose  = 'no'
      self.baudrate = 115200

      # board name
      self.boardName = 'USB AC DimController'

      # system info
      self.user     = platform.os.environ['USERNAME']
      self.os       = platform.system()
      self.machine  = sys.platform[:5]
      self.hostname = "unknown"

      # get machine's name
      if self.machine == 'win32':
         self.hostname = platform.os.environ['COMPUTERNAME']

      if self.machine in ( 'linux', 'unix', 'mac' ):
         p = subprocess.os.popen( 'hostname', "r" )
         self.hostname = p.read().rstrip('\n')
         p.close()

      # we don't need fully qualified name
      pattern = re.compile( '(.*)\.' )
      match = pattern.search( self.hostname )
      if match:
         self.hostname = match( 1 )

   def initializeBoard( self, chan ):
      # loop until we get acknowlegment - should have version
      # or time out
      timeout = 0
      identity = ''

      chan.write( "\r" )
      chan.write( "version\r" )

      while True:
         o = chan.readline()

         # locate board
         if self.boardName in o:
            return True

         timeout = timeout + 1

         if timeout > 10:
            break

      return False

   def scan( self ):
      # scan for available ports. return a list of tuples (num, name)
      available = []
      for i in range( 256 ):
         try:
            if self.machine == 'win32':
               # windows
               s = serial.Serial( i, self.baudrate, timeout=0.25, writeTimeout=0.25 )
            else:
               # linux,
               s = serial.Serial( "/dev/ttyACM"+str(i), self.baudrate, timeout=0.25 )

            identity = self.initializeBoard( s )
            if identity == True:
               available.append( ( i, s.portstr ) )
            s.close()   # explicit close 'cause of delayed GC in java
         except serial.SerialException:
            # error, just continue to next com port
            continue

      return available

   def readMessage( self, chan, command ):
      # loop until we get acknowlegment - should have message
      # or time out
      timeout = 0
      message = ''

      if self.verbose == 'yes':
         print "Sending command: " + command

      chan.write( command + "\r" )

      while True:
         o = chan.readline()

         # skip the command sent
         if command in o:
            continue

         # don't need these either
         if 'CMD >>' in o:
            continue

         # accepted
         if 'ok' in o:
            break

         # failed
         if 'failed' in o:
            break

         # unknown command
         if 'CMD: Command not recognized' in o:
            break

         # collection
         message += o

         timeout = timeout + 1

         if timeout > 100:
            break


      if message != '':
         message = message.replace('\n','')
         message = message.replace('\r','')
         return True, message

      return False, message

   def writeCommand ( self, chan, command ):
      # command
      # wait until we get acknowlegment
      timeout = 0
      err     = 0
      g       = 0
      f       = 0

      if self.verbose == 'yes':
         print "Sending command (%s)..." % str( command )

      chan.write( command + "\r" )

      while True:
         timeout = timeout + 1

         if timeout > 100:
            err = err + 1
            break

         o = chan.readline()

         if len(o) == 0:
            continue

         if self.verbose == 'yes':
            print o

         # interactive console
         if 'CMD >>' in o:
            # will print twice
            # once this happens then we can detect command response
            continue

         # acknowledgement
         if 'ok' in o:
            # normal response
            g = g + 1

         # acknowledgement
         if 'failed' in o:
            # command failed
            f = f + 1

         # unknown command
         if 'CMD: Command not recognized' in o:
            # unknown command
            err = err + 1

         # finished
         if g >= 1 or f >= 1 or err >= 1:
            break;

      chan.flushInput()

      # results
      if self.verbose == 'yes':
         print "Pass " + str(g)
         print "Fail " + str(f)
         print "Err  " + str(err)

      if g >= 1 and f == 0 and err == 0:
         # accepted
         return True

      # failed
      return False

#
# main section
#
if __name__ == "__main__":
   clientApp = None
   clientApp = acDimControlAPI()
   clientApp.options, clientApp.args = clientApp.parser.parse_args()

   # args
   if clientApp.options.verbose != None:
      clientApp.verbose = clientApp.options.verbose

   print "Found board:"
   for n,s in clientApp.scan():
      print "(%d) %s" % ( n, s )

      try:
         comm = serial.Serial( s, clientApp.baudrate, timeout=0.25, writeTimeout=0.25 )

         print "Set dimmer controls..."

         print "  *** Test 1 - get version of board ***"
         results, infoVersion  = clientApp.readMessage( comm, "version" )
         results, infoUUID     = clientApp.readMessage( comm, "sys getFSUUID" )
         results, infoSerial   = clientApp.readMessage( comm, "sys getFSSerial" )
         results, infoDate     = clientApp.readMessage( comm, "sys getFSDate" )
         results, infoRevision = clientApp.readMessage( comm, "sys getFSBoardVersion" )
         results, infoFirmware = clientApp.readMessage( comm, "sys getFSFirmwareVersion" )

         print "Version: " + infoVersion
         print "UUID   : " + infoUUID
         print "Serial : " + infoSerial

         results = clientApp.writeCommand( comm, "setDimmer "+actual_values[lux_value])
         time.sleep(5)
         print ""
         comm.close()
      except serial.SerialException:
         print "Failed to open com port, exiting..."
         sys.exit(1)

   print "Lux Value Set"

   sys.exit(0)
