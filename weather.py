#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
#Copyright (c) 2014 Jim Kemp <kemp.jim@gmail.com>

#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:

#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
### END LICENSE

""" Fetches weather reports Weather.com for display on small screens."""

__version__ = "0.0.8"

###############################################################################
#   Raspberry Pi Weather Display
#	By: Jim Kemp	11/15/2014
#
#
###############################################################################
import os
import pygame
import time
import datetime
import random
from pygame.locals import *
import calendar

import pywapi
import string

import locale
import threading

from contextlib import contextmanager


LOCALE_LOCK = threading.Lock()

@contextmanager
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


from icon_defs import *

mouseX, mouseY = 0, 0
mode = 'w'		# Default to weather mode.

disp_units = "metric"
#disp_units = "imperial"
zip_code = 'SZXX7282'

locale.setlocale(locale.LC_ALL, 'de_CH.UTF-8')

# Show degree F symbol using magic unicode char in a smaller font size.
# The variable uniTmp holds a unicode character that is either DegreeC or DegreeF.
# Yep, one unicode character is has both the letter and the degree symbol.
if disp_units == 'metric':
	uniTmp = unichr(0x2103)		# Unicode for DegreeC
	windSpeed = ' m/s'
	windScale = 0.277778		# To convert kmh to m/s.
	baroUnits = ''
else:
	uniTmp = unichr(0x2109)		# Unicode for DegreeF
	windSpeed = ' mph'
	windScale = 1.0
	baroUnits = ' "Hg'


###############################################################################
def getIcon( w, i ):
	try:
		return int(w['forecasts'][i]['day']['icon'])
	except:
		return 29

# Small LCD Display.
class SmDisplay:
	screen = None;

	####################################################################
	def __init__(self):
		"Ininitializes a new pygame screen using the framebuffer"
		# Based on "Python GUI in Linux frame buffer"
		# http://www.karoltomala.com/blog/?p=679
		disp_no = os.getenv("DISPLAY")
		if disp_no:
			print "X Display = {0}".format(disp_no)

		# Check which frame buffer drivers are available
		# Start with fbcon since directfb hangs with composite output
		drivers = ['fbcon', 'directfb', 'svgalib']
		found = False
		for driver in drivers:
			# Make sure that SDL_VIDEODRIVER is set
			if not os.getenv('SDL_VIDEODRIVER'):
				os.putenv('SDL_VIDEODRIVER', driver)
			try:
				pygame.display.init()
			except pygame.error:
				print 'Driver: {0} failed.'.format(driver)
				continue
			found = True
			break

		if not found:
			raise Exception('No suitable video driver found!')

		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		print "Framebuffer Size: %d x %d" % (size[0], size[1])
		self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
		# Clear the screen to start
		self.screen.fill((0, 0, 0))
		# Initialise font support
		pygame.font.init()
		# Render the screen
		pygame.mouse.set_visible(0)
		pygame.display.update()
		#for fontname in pygame.font.get_fonts():
		#        print fontname
		self.temp = ''
		self.feels_like = '0'
		self.wind_speed = '0'
		self.baro = '29.95'
		self.wind_dir = 'S'
		self.humid = '50.0'
		self.wLastUpdate = ''
		self.day = [ '', '', '', '' ]
		self.icon = [ 0, 0, 0, 0 ]
		self.rain = [ '', '', '', '' ]
		self.temps = [ ['',''], ['',''], ['',''], ['',''] ]
		self.sunrise = '7:00 AM'
		self.sunset = '8:00 PM'
		"""
		# Larger Display
		self.xmax = 800 - 35
		self.ymax = 600 - 5
		self.scaleIcon = True		# Weather icons need scaling.
		self.iconScale = 1.5		# Icon scale amount.
		self.subwinTh = 0.045		# Sub window text height
		self.tmdateTh = 0.100		# Time & Date Text Height
		self.tmdateSmTh = 0.06
		self.tmdateYPos = 10		# Time & Date Y Position
		self.tmdateYPosSm = 18		# Time & Date Y Position Small
		self.errCount = 0		# Count number of failed updates.

		"""
		# Small Display
		self.xmax = 480 - 5
		self.ymax = 320 - 5
		self.scaleIcon = False		# No icon scaling needed.
		self.iconScale = 1.0
		self.subwinTh = 0.05		# Sub window text height
		self.tmdateTh = 0.105		# Time & Date Text Height
		self.tmdateSmTh = 0.055
		self.tmdateYPos = 1		# Time & Date Y Position
		self.tmdateYPosSm = 8		# Time & Date Y Position Small
		self.errCount = 0




	####################################################################
	def __del__(self):
		"Destructor to make sure pygame shuts down, etc."

	####################################################################
	def UpdateWeather( self ):
		# Use Weather.com for source data.
		cc = 'current_conditions'
		f = 'forecasts'
		w = { cc:{ f:1 }}  # Init to something.

		# This is where the magic happens.
		try:
			self.w = pywapi.get_weather_from_weather_com( zip_code, units=disp_units )
			w = self.w
		except:
			print "Error getting update from weather.com"
			self.errCount += 1
			return

		try:
			if ( w[cc]['last_updated'] != self.wLastUpdate ):
				self.wLastUpdate = w[cc]['last_updated']
				print "New Weather Update: " + self.wLastUpdate
				self.temp = string.lower( w[cc]['temperature'] )
				self.feels_like = string.lower( w[cc]['feels_like'] )
				self.wind_speed = string.lower( w[cc]['wind']['speed'] )
				self.baro = string.lower( w[cc]['barometer']['reading'] )
				self.wind_dir = string.upper( w[cc]['wind']['text'] )
				self.humid = string.upper( w[cc]['humidity'] )
				self.vis = string.upper( w[cc]['visibility'] )
				self.gust = string.upper( w[cc]['wind']['gust'] )
				self.wind_direction = string.upper( w[cc]['wind']['direction'] )
				with setlocale('C'):
					self.day[0] = time.strptime( w[f][0]['day_of_week'], '%A' )
					self.day[1] = time.strptime( w[f][1]['day_of_week'], '%A' )
					self.day[2] = time.strptime( w[f][2]['day_of_week'], '%A' )
					self.day[3] = time.strptime( w[f][3]['day_of_week'], '%A' )
				self.sunrise = w[f][0]['sunrise']
				self.sunset = w[f][0]['sunset']
				self.icon[0] = getIcon( w, 0 )
				self.icon[1] = getIcon( w, 1 )
				self.icon[2] = getIcon( w, 2 )
				self.icon[3] = getIcon( w, 3 )
				print 'Icon Index: ', self.icon[0], self.icon[1], self.icon[2], self.icon[3]
				#print 'File: ', sd+icons[self.icon[0]]
				self.rain[0] = w[f][0]['day']['chance_precip']
				self.rain[1] = w[f][1]['day']['chance_precip']
				self.rain[2] = w[f][2]['day']['chance_precip']
				self.rain[3] = w[f][3]['day']['chance_precip']
				if ( w[f][0]['high'] == 'N/A' ):
					self.temps[0][0] = '--'
				else:
					self.temps[0][0] = w[f][0]['high'] + uniTmp
				self.temps[0][1] = w[f][0]['low'] + uniTmp
				self.temps[1][0] = w[f][1]['high'] + uniTmp
				self.temps[1][1] = w[f][1]['low'] + uniTmp
				self.temps[2][0] = w[f][2]['high'] + uniTmp
				self.temps[2][1] = w[f][2]['low'] + uniTmp
				self.temps[3][0] = w[f][3]['high'] + uniTmp
				self.temps[3][1] = w[f][3]['low'] + uniTmp
			self.errCount = 0

		except KeyError:
			print "KeyError -> Weather Error"
			if self.errCount >= 15:
				self.temp = '??'
			self.wLastUpdate = ''
			return False
		except ValueError:
			print "ValueError -> Weather Error"

		return True



	####################################################################
	def disp_weather(self):
		# Fill the screen with black
		self.screen.fill( (0,0,0) )
		xmin = 10
		xmax = self.xmax
		ymax = self.ymax
		lines = 5
		lc = (255,255,255)
		fn = "freesans"

		# Draw Screen Border
		pygame.draw.line( self.screen, lc, (xmin,0),(xmax,0), lines )
		pygame.draw.line( self.screen, lc, (xmin,0),(xmin,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax),(xmax,ymax), lines )	# Bottom
		pygame.draw.line( self.screen, lc, (xmax,0),(xmax,ymax+2), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax*0.15),(xmax,ymax*0.15), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax*0.5),(xmax,ymax*0.5), lines )
		pygame.draw.line( self.screen, lc, (xmax*0.25,ymax*0.5),(xmax*0.25,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmax*0.5,ymax*0.15),(xmax*0.5,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmax*0.75,ymax*0.5),(xmax*0.75,ymax), lines )

		# Time & Date
		th = self.tmdateTh
		sh = self.tmdateSmTh
		font = pygame.font.SysFont( fn, int(ymax*th), bold=1 )	# Regular Font
		sfont = pygame.font.SysFont( fn, int(ymax*sh), bold=1 )	# Small Font for Seconds

		tm1 = time.strftime( "%a, %d. %b   %H:%M", time.localtime() )	# 1st part
		tm1 = tm1.decode('utf-8')
		tm2 = time.strftime( "%S", time.localtime() )					# 2nd

		rtm1 = font.render( tm1, True, lc )
		(tx1,ty1) = rtm1.get_size()
		rtm2 = sfont.render( tm2, True, lc )
		(tx2,ty2) = rtm2.get_size()

		tp = xmax / 2 - (tx1 + tx2) / 2
		self.screen.blit( rtm1, (tp,self.tmdateYPos) )
		self.screen.blit( rtm2, (tp+tx1+3,self.tmdateYPosSm) )

		# Outside Temp
		font = pygame.font.SysFont( fn, int(ymax*(0.5-0.15)*0.9), bold=1 )
		txt = font.render( self.temp, True, lc )
		(tx,ty) = txt.get_size()
		# Show degree F symbol using magic unicode char in a smaller font size.
		dfont = pygame.font.SysFont( fn, int(ymax*(0.5-0.15)*0.5), bold=1 )
		dtxt = dfont.render( uniTmp, True, lc )
		(tx2,ty2) = dtxt.get_size()
		x = xmax*0.27 - (tx*1.02 + tx2) / 2
		self.screen.blit( txt, (x,ymax*0.15) )
		#self.screen.blit( txt, (xmax*0.02,ymax*0.15) )
		x = x + (tx*1.02)
		self.screen.blit( dtxt, (x,ymax*0.2) )
		#self.screen.blit( dtxt, (xmax*0.02+tx*1.02,ymax*0.2) )

		# Conditions
		st = 0.16    # Yaxis Start Pos
		gp = 0.065   # Line Spacing Gap
		th = 0.06    # Text Height
		dh = 0.05    # Degree Symbol Height
		so = 0.01    # Degree Symbol Yaxis Offset
		xp = 0.52    # Xaxis Start Pos
		x2 = 0.78    # Second Column Xaxis Start Pos

		font = pygame.font.SysFont( fn, int(ymax*th), bold=1 )
		txt = font.render( 'Windchill:', True, lc )
		self.screen.blit( txt, (xmax*xp,ymax*st) )
		txt = font.render( self.feels_like, True, lc )
		self.screen.blit( txt, (xmax*x2,ymax*st) )
		(tx,ty) = txt.get_size()
		# Show degree F symbol using magic unicode char.
		dfont = pygame.font.SysFont( fn, int(ymax*dh), bold=1 )
		dtxt = dfont.render( uniTmp, True, lc )
		self.screen.blit( dtxt, (xmax*x2+tx*1.01,ymax*(st+so)) )

		txt = font.render( 'Windspeed:', True, lc )
		self.screen.blit( txt, (xmax*xp,ymax*(st+gp*1)) )
		if 'calm' in self.wind_speed:
			windStr = " 0 %s" % windSpeed
		else:
			windSp = float(self.wind_speed) * windScale
			windStr = "%.0f %s" % (windSp, windSpeed)
		txt = font.render( windStr, True, lc )
		self.screen.blit( txt, (xmax*x2,ymax*(st+gp*1)) )

		txt = font.render( 'Direction:', True, lc )
		self.screen.blit( txt, (xmax*xp,ymax*(st+gp*2)) )
		txt = font.render( string.upper(self.wind_dir), True, lc )
		self.screen.blit( txt, (xmax*x2,ymax*(st+gp*2)) )

		txt = font.render( 'Barometer:', True, lc )
		self.screen.blit( txt, (xmax*xp,ymax*(st+gp*3)) )
		txt = font.render( self.baro + baroUnits, True, lc )
		self.screen.blit( txt, (xmax*x2,ymax*(st+gp*3)) )

		txt = font.render( 'Humidity:', True, lc )
		self.screen.blit( txt, (xmax*xp,ymax*(st+gp*4)) )
		txt = font.render( self.humid+'%', True, lc )
		self.screen.blit( txt, (xmax*x2,ymax*(st+gp*4)) )

		wx = 	0.125			# Sub Window Centers
		wy = 	0.510			# Sub Windows Yaxis Start
		th = 	self.subwinTh		# Text Height
		rpth = 	0.100			# Rain Present Text Height
		gp = 	0.065			# Line Spacing Gap
		ro = 	0.010 * xmax   	# "Rain:" Text Window Offset winthin window.
		rpl =	5.95			# Rain percent line offset.

		font = pygame.font.SysFont( fn, int(ymax*th), bold=1 )
		rpfont = pygame.font.SysFont( fn, int(ymax*rpth), bold=1 )

		# Sub Window 1
		txt = font.render( 'Heute:', True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*wx-tx/2,ymax*(wy+gp*0)) )
		txt = font.render( self.temps[0][0] + ' / ' + self.temps[0][1], True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*wx-tx/2,ymax*(wy+gp*5)) )
		#rtxt = font.render( 'Rain:', True, lc )
		#self.screen.blit( rtxt, (ro,ymax*(wy+gp*5)) )
		rptxt = rpfont.render( self.rain[0]+'%', True, lc )
		(tx,ty) = rptxt.get_size()
		self.screen.blit( rptxt, (xmax*wx-tx/2,ymax*(wy+gp*rpl)) )
		icon = pygame.image.load(sd + icons[self.icon[0]]).convert_alpha()
		(ix,iy) = icon.get_size()
		if self.scaleIcon:
			icon2 = pygame.transform.scale( icon, (int(ix*1.5),int(iy*1.5)) )
			(ix,iy) = icon2.get_size()
			icon = icon2
		if ( iy < 90 ):
			yo = (90 - iy) / 2
		else:
			yo = 0
		self.screen.blit( icon, (xmax*wx-ix/2,ymax*(wy+gp*1.2)+yo) )

		# Sub Window 2
		txt = font.render(  time.strftime( "%A", self.day[1] )+':', True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*(wx*3)-tx/2,ymax*(wy+gp*0)) )
		txt = font.render( self.temps[1][0] + ' / ' + self.temps[1][1], True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*wx*3-tx/2,ymax*(wy+gp*5)) )
		#self.screen.blit( rtxt, (xmax*wx*2+ro,ymax*(wy+gp*5)) )
		rptxt = rpfont.render( self.rain[1]+'%', True, lc )
		(tx,ty) = rptxt.get_size()
		self.screen.blit( rptxt, (xmax*wx*3-tx/2,ymax*(wy+gp*rpl)) )
		icon = pygame.image.load(sd + icons[self.icon[1]]).convert_alpha()
		(ix,iy) = icon.get_size()
		if self.scaleIcon:
			icon2 = pygame.transform.scale( icon, (int(ix*1.5),int(iy*1.5)) )
			(ix,iy) = icon2.get_size()
			icon = icon2
		if ( iy < 90 ):
			yo = (90 - iy) / 2
		else:
			yo = 0
		self.screen.blit( icon, (xmax*wx*3-ix/2,ymax*(wy+gp*1.2)+yo) )

		# Sub Window 3
		txt = font.render( time.strftime( "%A", self.day[2] )+':', True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*(wx*5)-tx/2,ymax*(wy+gp*0)) )
		txt = font.render( self.temps[2][0] + ' / ' + self.temps[2][1], True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*wx*5-tx/2,ymax*(wy+gp*5)) )
		#self.screen.blit( rtxt, (xmax*wx*4+ro,ymax*(wy+gp*5)) )
		rptxt = rpfont.render( self.rain[2]+'%', True, lc )
		(tx,ty) = rptxt.get_size()
		self.screen.blit( rptxt, (xmax*wx*5-tx/2,ymax*(wy+gp*rpl)) )
		icon = pygame.image.load(sd + icons[self.icon[2]]).convert_alpha()
		(ix,iy) = icon.get_size()
		if self.scaleIcon:
			icon2 = pygame.transform.scale( icon, (int(ix*1.5),int(iy*1.5)) )
			(ix,iy) = icon2.get_size()
			icon = icon2
		if ( iy < 90 ):
			yo = (90 - iy) / 2
		else:
			yo = 0
		self.screen.blit( icon, (xmax*wx*5-ix/2,ymax*(wy+gp*1.2)+yo) )

		# Sub Window 4
		txt = font.render( time.strftime( "%A", self.day[3] )+':', True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*(wx*7)-tx/2,ymax*(wy+gp*0)) )
		txt = font.render( self.temps[3][0] + ' / ' + self.temps[3][1], True, lc )
		(tx,ty) = txt.get_size()
		self.screen.blit( txt, (xmax*wx*7-tx/2,ymax*(wy+gp*5)) )
		#self.screen.blit( rtxt, (xmax*wx*6+ro,ymax*(wy+gp*5)) )
		rptxt = rpfont.render( self.rain[3]+'%', True, lc )
		(tx,ty) = rptxt.get_size()
		self.screen.blit( rptxt, (xmax*wx*7-tx/2,ymax*(wy+gp*rpl)) )
		icon = pygame.image.load(sd + icons[self.icon[3]]).convert_alpha()
		(ix,iy) = icon.get_size()
		if self.scaleIcon:
			icon2 = pygame.transform.scale( icon, (int(ix*1.5),int(iy*1.5)) )
			(ix,iy) = icon2.get_size()
			icon = icon2
		if ( iy < 90 ):
			yo = (90 - iy) / 2
		else:
			yo = 0
		self.screen.blit( icon, (xmax*wx*7-ix/2,ymax*(wy+gp*1.2)+yo) )

		# Update the display
		pygame.display.update()

	####################################################################
	def disp_calendar(self):
		# Fill the screen with black
		self.screen.fill( (0,0,0) )
		xmin = 10
		xmax = self.xmax
		ymax = self.ymax
		lines = 5
		lc = (255,255,255)
		sfn = "freemono"
		fn = "freesans"

		# Draw Screen Border
		pygame.draw.line( self.screen, lc, (xmin,0),(xmax,0), lines )
		pygame.draw.line( self.screen, lc, (xmin,0),(xmin,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax),(xmax,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmax,0),(xmax,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax*0.15),(xmax,ymax*0.15), lines )

		# Time & Date
		th = self.tmdateTh
		sh = self.tmdateSmTh
		font = pygame.font.SysFont( fn, int(ymax*th), bold=1 )		# Regular Font
		sfont = pygame.font.SysFont( fn, int(ymax*sh), bold=1 )		# Small Font for Seconds

		tm1 = time.strftime( "%a, %d. %b   %H:%M", time.localtime() )	# 1st part
		tm1 = tm1.decode('utf-8')
		tm2 = time.strftime( "%S", time.localtime() )			# 2nd

		rtm1 = font.render( tm1, True, lc )
		(tx1,ty1) = rtm1.get_size()
		rtm2 = sfont.render( tm2, True, lc )
		(tx2,ty2) = rtm2.get_size()

		tp = xmax / 2 - (tx1 + tx2) / 2
		self.screen.blit( rtm1, (tp,self.tmdateYPos) )
		self.screen.blit( rtm2, (tp+tx1+3,self.tmdateYPosSm) )

		# Conditions
		ys = 0.20		# Yaxis Start Pos
		xs = 0.20		# Xaxis Start Pos
		gp = 0.075	# Line Spacing Gap
		th = 0.05		# Text Height

		cfont = pygame.font.SysFont( sfn, int(ymax*sh), bold=1 )
		#cal = calendar.TextCalendar()
		yr = int( time.strftime( "%Y", time.localtime() ) )	# Get Year
		mn = int( time.strftime( "%m", time.localtime() ) )	# Get Month
		cal = calendar.month( yr, mn ).splitlines()
		i = 0
		for cal_line in cal:
			txt = cfont.render( cal_line, True, lc )
			self.screen.blit( txt, (xmax*xs,ymax*(ys+gp*i)) )
			i = i + 1

		# Update the display
		pygame.display.update()

	####################################################################
	def sPrint( self, s, font, x, l, lc ):
		f = font.render( s, True, lc )
		self.screen.blit( f, (x,self.ymax*0.075*l) )

	####################################################################
	def disp_help( self, inDaylight, dayHrs, dayMins, tDaylight, tDarkness ):
		# Fill the screen with black
		self.screen.fill( (0,0,0) )
		xmax = self.xmax
		ymax = self.ymax
		xmin = 10
		lines = 5
		lc = (255,255,255)
		sfn = "freemono"
		fn = "freesans"

		# Draw Screen Border
		pygame.draw.line( self.screen, lc, (xmin,0),(xmax,0), lines )
		pygame.draw.line( self.screen, lc, (xmin,0),(xmin,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax),(xmax,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmax,0),(xmax,ymax), lines )
		pygame.draw.line( self.screen, lc, (xmin,ymax*0.15),(xmax,ymax*0.15), lines )

		thl = self.tmdateTh	# Large Text Height
		sh = self.tmdateSmTh	# Small Text Height

		# Time & Date
		font = pygame.font.SysFont( fn, int(ymax*thl), bold=1 )		# Regular Font
		sfont = pygame.font.SysFont( fn, int(ymax*sh), bold=1 )		# Small Font

		tm1 = time.strftime( "%a, %d. %b   %H:%M", time.localtime() )	# 1st part
		tm2 = time.strftime( "%S", time.localtime() )			# 2nd

		rtm1 = font.render( tm1, True, lc )
		(tx1,ty1) = rtm1.get_size()
		rtm2 = sfont.render( tm2, True, lc )
		(tx2,ty2) = rtm2.get_size()

		tp = xmax / 2 - (tx1 + tx2) / 2
		self.screen.blit( rtm1, (tp,self.tmdateYPos) )
		self.screen.blit( rtm2, (tp+tx1+3,self.tmdateYPosSm) )

		self.sPrint( "Sunrise: %s" % self.sunrise, sfont, xmax*0.05, 3, lc )
		self.sPrint( "Sunset: %s" % self.sunset, sfont, xmax*0.05, 4, lc )

		s = "Daylight (Hrs:Min): %d:%02d" % (dayHrs, dayMins)
		self.sPrint( s, sfont, xmax*0.05, 5, lc )

		if inDaylight: s = "Sunset in (Hrs:Min): %d:%02d" % stot( tDarkness )
		else:          s = "Sunrise in (Hrs:Min): %d:%02d" % stot( tDaylight )
		self.sPrint( s, sfont, xmax*0.05, 6, lc )

		s = "Update: %s" % self.wLastUpdate
		self.sPrint( s, sfont, xmax*0.05, 7, lc )

		cc = 'current_conditions'
		s = "Current Cond: %s" % self.w[cc]['text']
		self.sPrint( s, sfont, xmax*0.05, 8, lc )

		# Outside Temperature
		s = self.temp + unichr(176) + 'F '
		s = s + self.baro + baroUnits
		s = s + 'Wind ' + self.wind_speed
		if self.gust != 'N/A':
			s = s + '/' + self.gust
		if self.wind_speed != 'calm':
			s = s + 'windSpeed @' + self.wind_direction + unichr(176)
		self.sPrint( s, sfont, xmax*0.05, 9, lc )

		s = "Visability %smi" % self.vis
		self.sPrint( s, sfont, xmax*0.05, 10, lc )

		# Update the display
		pygame.display.update()



	# Save a jpg image of the screen.
	####################################################################
	def screen_cap( self ):
		pygame.image.save( self.screen, "screenshot.jpeg" )
		print "Screen capture complete."


# Helper function to which takes seconds and returns (hours, minutes).
############################################################################
def stot( sec ):
	min = sec.seconds // 60
	hrs = min // 60
	return ( hrs, min % 60 )


# Given a sunrise and sunset time string (sunrise example format '7:00 AM'),
# return true if current local time is between sunrise and sunset. In other
# words, return true if it's daytime and the sun is up. Also, return the
# number of hours:minutes of daylight in this day. Lastly, return the number
# of seconds until daybreak and sunset. If it's dark, daybreak is set to the
# number of seconds until sunrise. If it daytime, sunset is set to the number
# of seconds until the sun sets.
#
# So, five things are returned as:
#  ( InDaylight, Hours, Minutes, secToSun, secToDark).
############################################################################
def Daylight( sr, st ):
	inDaylight = False	# Default return code.

	# Get current datetime with tz's local day and time.
	tNow = datetime.datetime.now()

	# From a string like '7:00 AM', build a datetime variable for
	# today with the hour and minute set to sunrise.
	with setlocale('C'):
		t = time.strptime( sr, '%I:%M %p' )		# Temp Var
	tSunrise = tNow					# Copy time now.
	# Overwrite hour and minute with sunrise hour and minute.
	tSunrise = tSunrise.replace( hour=t.tm_hour, minute=t.tm_min, second=0 )

	# From a string like '8:00 PM', build a datetime variable for
	# today with the hour and minute set to sunset.
	with setlocale('C'):
		t = time.strptime( myDisp.sunset, '%I:%M %p' )
	tSunset = tNow					# Copy time now.
	# Overwrite hour and minute with sunset hour and minute.
	tSunset = tSunset.replace( hour=t.tm_hour, minute=t.tm_min, second=0 )

	# Test if current time is between sunrise and sunset.
	if (tNow > tSunrise) and (tNow < tSunset):
		inDaylight = True		# We're in Daytime
		tDarkness = tSunset - tNow	# Delta seconds until dark.
		tDaylight = 0			# Seconds until daylight
	else:
		inDaylight = False		# We're in Nighttime
		tDarkness = 0			# Seconds until dark.
		# Delta seconds until daybreak.
		if tNow > tSunset:
			# Must be evening - compute sunrise as time left today
			# plus time from midnight tomorrow.
			tMidnight = tNow.replace( hour=23, minute=59, second=59 )
			tNext = tNow.replace( hour=0, minute=0, second=0 )
			tDaylight = (tMidnight - tNow) + (tSunrise - tNext)
		else:
			# Else, must be early morning hours. Time to sunrise is
			# just the delta between sunrise and now.
			tDaylight = tSunrise - tNow

	# Compute the delta time (in seconds) between sunrise and set.
	dDaySec = tSunset - tSunrise		# timedelta in seconds
	(dayHrs, dayMin) = stot( dDaySec )	# split into hours and minutes.

	return ( inDaylight, dayHrs, dayMin, tDaylight, tDarkness )


############################################################################
def btnNext( channel ):
	global mode, dispTO

	if ( mode == 'c' ): mode = 'w'
	elif (mode == 'w' ): mode ='h'
	elif (mode == 'h' ): mode ='c'

	dispTO = 0

	print "Button Event!"


# Display all the available fonts.
#print "Fonts: ", pygame.font.get_fonts()

mode = 'w'		# Default to weather mode.

# Create an instance of the lcd display class.
myDisp = SmDisplay()

running = True		# Stay running while True
s = 0			# Seconds Placeholder to pace display.
dispTO = 0		# Display timeout to automatically switch back to weather dispaly.

# Loads data from Weather.com into class variables.
if myDisp.UpdateWeather() == False:
	print 'Startup Error: no data from Weather.com.'
	#running = False



#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
while running:

	# Look for and process keyboard events to change modes.
	for event in pygame.event.get():
		if event.type == pygame.KEYDOWN:
			# On 'q' or keypad enter key, quit the program.
			if (( event.key == K_KP_ENTER ) or (event.key == K_q)):
				running = False

			# On 'c' key, set mode to 'calendar'.
			elif ( event.key == K_c ):
				mode = 'c'
				dispTO = 0

			# On 'w' key, set mode to 'weather'.
			elif ( event.key == K_w ):
				mode = 'w'
				dispTO = 0

			# On 's' key, save a screen shot.
			elif ( event.key == K_s ):
				myDisp.screen_cap()

			# On 'h' key, set mode to 'help'.
			elif ( event.key == K_h ):
				mode = 'h'
				dispTO = 0

	# Automatically switch back to weather display after a couple minutes.
	if mode != 'w':
		dispTO += 1
		if dispTO > 3000:	# Five minute timeout at 100ms loop rate.
			mode = 'w'
	else:
		dispTO = 0

	# Calendar Display Mode
	if ( mode == 'c' ):
		# Update / Refresh the display after each second.
		if ( s != time.localtime().tm_sec ):
			s = time.localtime().tm_sec
			myDisp.disp_calendar()

	# Weather Display Mode
	if ( mode == 'w' ):
		# Update / Refresh the display after each second.
		if ( s != time.localtime().tm_sec ):
			s = time.localtime().tm_sec
			myDisp.disp_weather()
			#ser.write( "Weather\r\n" )
		# Once the screen is updated, we have a full second to get the weather.
		# Once per minute, update the weather from the net.
		if ( s == 0 ):
			try:
				myDisp.UpdateWeather()
			except:
				print "Unhandled Error in UndateWeather."

	if ( mode == 'h'):
		# Pace the screen updates to once per second.
		if s != time.localtime().tm_sec:
			s = time.localtime().tm_sec

			( inDaylight, dayHrs, dayMins, tDaylight, tDarkness) = Daylight( myDisp.sunrise, myDisp.sunset )

			#if inDaylight:
			#	print "Time until dark (Hr:Min) -> %d:%d" % stot( tDarkness )
			#else:
			#	#print 'tDaylight ->', tDaylight
			#	print "Time until daybreak (Hr:Min) -> %d:%d" % stot( tDaylight )

			try:
				# Stat Screen Display.
				myDisp.disp_help( inDaylight, dayHrs, dayMins, tDaylight, tDarkness )
			except KeyError:
				print "Disp_Help key error."

		# Refresh the weather data once per minute.
		if ( int(s) == 0 ): myDisp.UpdateWeather()

	( inDaylight, dayHrs, dayMins, tDaylight, tDarkness) = Daylight( myDisp.sunrise, myDisp.sunset )


	# Loop timer.
	pygame.time.wait( 100 )


pygame.quit()
