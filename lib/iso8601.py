"""Copyright (c) 2004-2008, University of Cambridge.

All rights reserved.

Redistribution and use of this software in source and binary forms
(where applicable), with or without modification, are permitted
provided that the following conditions are met:

 *  Redistributions of source code must retain the above copyright
    notice, this list of conditions, and the following disclaimer.

 *  Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions, and the following
    disclaimer in the documentation and/or other materials provided with
    the distribution.
    
 *  Neither the name of the University of Cambridge, nor the names of
    any other contributors to the software, may be used to endorse or
    promote products derived from this software without specific prior
    written permission.

THIS SOFTWARE IS PROVIDED ``AS IS'', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""
	
import time,types,math,string

class ISODateTimeError:
	"""A class for representing errors in ISO date and time values"""
	pass

class ISODateCoercionError(ISODateTimeError):
	def __repr__ (self):
		return "Couldn't convert value to ISO Date"

class ISODateComparisonError(ISODateTimeError):
	def __repr__ (self):
		return "Incompatible ISO Dates in comparison"

class ISOAmbiguousDateError(ISODateTimeError):
	def __repr__ (self):
		return 'Ambiguous ISO Date'

class ISOBadOrdinalDateError(ISODateTimeError):
	def __init__ (self,ordinalDay):
		self.ordinalDay=ordinalDay
	
	def __repr__ (self):
		return 'ISO Ordinal Day out of range: '+str(self.ordinalDay)

class ISOBadWeekDateError(ISODateTimeError):
	def __init__ (self,week):
		self.week=week
	
	def __repr__ (self):
		return 'ISO Week out of range: '+str(self.week)

class ISODateUnderflowError(ISODateTimeError):
	def __repr__ (self):
		return 'ISO date underflowed'

class ISODateOverflowError(ISODateTimeError):
	def __repr__ (self):
		return 'ISO date overflowed'


class ISOInvalidDateError(ISODateTimeError):
	def __repr__ (self):
		return 'Invalid ISO date'
				
class ISODateSyntaxError(ISODateTimeError):
	def __init__ (self,dateStr):
		self.dateStr=dateStr
	
	def __repr__ (self):
		return 'Syntax error in ISO date : '+self.dateStr

class ISOTimeCoercionError(ISODateTimeError):
	def __repr__ (self):
		return "Couldn't convert value to ISO Time"

class ISOTimeComparisonError(ISODateTimeError):
	def __repr__ (self):
		return "Incompatible ISO Times in comparison"

class ISOAmbiguousTimeError(ISODateTimeError):
	def __repr__ (self):
		return 'Ambiguous ISO Time'

class ISOInvalidTimeError(ISODateTimeError):
	def __repr__ (self):
		return 'Invalid ISO Time'
		
class ISOTimeSyntaxError(ISODateTimeError):
	def __init__ (self,timeStr):
		self.timeStr=timeStr
	
	def __repr__ (self):
		return 'Syntax error in ISO time : '+self.timeStr

class ISOTimeZoneSyntaxError(ISODateTimeError):
	def __init__ (self,zoneStr):
		self.zoneStr=zoneStr
	
	def __repr__ (self):
		return 'Syntax error in ISO time zone : '+self.zoneStr
	
MONTH_SIZES=(31,28,31,30,31,30,31,31,30,31,30,31)
MONTH_SIZES_LEAPYEAR=(31,29,31,30,31,30,31,31,30,31,30,31)
MONTH_OFFSETS=(0,31,59,90,120,151,181,212,243,273,304,334)

def LeapYear(year):
	"""Leapyear returns 1 if year is a leap year and 0 otherwise.  Note that leap years
	famously fall on all years that divide by 4 except those that divide by 100 but
	including those that divide by 400."""
	if year%4:
		return 0
	elif year%100:
		return 1
	elif year%400:
		return 0
	else:
		return 1

def DayOfWeek(year,month,day):
	"""DayOfWeek returns the day of week 1-7, 1 being Monday for the given year, month
	and day"""
	num=year*365
	num=num+year/4+1
	num=num-(year/100+1)
	num=num+year/400+1
	if month<3 and LeapYear(year):
		num=num-1
	return (num+MONTH_OFFSETS[month-1]+day+4)%7+1

def WeekCount(year):
	"""Week count returns the number of calendar weeks in a year.  Most years have 52
	weeks of course, but if the year begins on a Thursday or a leap year begins on a
	Wednesday then it has 53."""
	dow=DayOfWeek(year,1,1)
	if dow==4:
		return 53
	elif dow==3 and LeapYear(year):
		return 53
	else:
		return 52
		
def ReadISOTimeZone (zoneStr):	
	if zoneStr=='Z':
		zone=0
	elif zoneStr:
		zSign=zoneStr[0]
		zoneStr=zoneStr[1:]
		if len(zoneStr)>=2 and zoneStr[:2].isdigit():
			zone=int(zoneStr[:2])*60
			zoneStr=zoneStr[2:]
		else:
			raise ISOTimeZoneSyntaxError(zoneStr)
		if len(zoneStr)==3 and zoneStr[0]==':':
			zoneStr=zoneStr[1:]
		if len(zoneStr)==2 and zoneStr.isdigit():
			zone=zone+int(zoneStr)
		elif zoneStr:
			raise ISOTimeZoneSyntaxError(zoneStr)
	else:
		zone=None
	return zone

class ISODate:
	"""A class for representing ISO dates"""
	
	def __init__(self,value=None,baseDate=None):
		if type(value) in (types.StringType,types.UnicodeType):
			self.ReadISODate(value,baseDate)
		elif isinstance(value,ISODate):
			self.SetDate(value)
		elif value is None:
			self.Reset()
		else:
			raise ISODateCoercionError()
				
	def Reset (self):
		self.century=self.year=self.month=self.day=None
	
	def FullySpecified (self):
		return self.century is not None and self.year is not None and \
			self.month is not None and self.day is not None

	def Now (self):
		self.SetTimeTuple(time.gmtime(time.time()))
	
	def Legal (self):
		if self.century is None:
			if self.year is not None and (self.year<0 or self.year>99):
				return 0
			# The tests for month and day are the same whether or not year is
			# specified in the absence of a century.
			if self.month is None:
				if self.day is None:
					return 1
				else:
					return self.day>=1 and self.day<=31
			else:
				if self.day is None:
					return 1
				else:
					return self.day>=1 and self.day<=MONTH_SIZES_LEAPYEAR[self.month-1]
		else:
			if self.century<0 or self.century>99:
				return 0
			if self.year is None:
				return self.month is None and self.day is None

			else:
				if self.year<0 or self.year>99 or (self.year==0 and self.century==0):
					return 0
				absYear=self.century*100+self.year
				if self.month is None:
					return self.day is None
				else:
					if self.month<1 or self.month>12:
						return 0
					if self.day is None:
						return 1
					else:
						if LeapYear(absYear):
							return self.day>=1 and self.day<=MONTH_SIZES_LEAPYEAR[self.month-1]
						else:
							return self.day>=1 and self.day<=MONTH_SIZES[self.month-1]
	
	def GetTruncation (self):
		if self.century is None:
			if self.year is None:
				if self.month is None:
					if self.day is None:
						return 4
					else:
						return 3
				else:
					return 2
			else:
				return 1
		else:
			return 0
	
	def SetTruncation (self,truncation,baseDate=None):
		if baseDate is not None and self.GetTruncation()>truncation:
			if self.GetPrecision()>baseDate.GetPrecision() or baseDate.GetTruncation():
				raise ISOAmbiguousDateError()
			if self.century is None:
				self.century=baseDate.century
				if self.year is None:
					self.year=baseDate.year
					if self.month is None:
						self.month=baseDate.month
						if self.day is None:
							self.day=baseDate.day
						elif self.day<baseDate.day:
							self.month=self.month+1
					elif self.month<baseDate.month:
						self.year=self.year+1
					elif self.month==baseDate.month and \
						self.day is not None and self.day<baseDate.day:
						self.year=self.year+1
				elif self.year<baseDate.year:
					self.century=self.century+1
				elif self.year==baseDate.year:
					if self.month is not None:
						if self.month<baseDate.month:
							self.century=self.century+1
						elif self.month==baseDate.month and \
							self.day is not None and self.day<baseDate.day:
								self.century=self.century+1
				if self.month>12:
					self.year=self.year+1
					self.month=12
				if self.year>99:
					self.century=self.century+1
					self.year=0
				if self.century>99:
					raise ISODateOverflowError()
				if not self.Legal():
					raise ISOInvalidDateError()								
		if truncation>0:
			self.century=None
			if truncation>1:
				self.year=None
				if truncation>2:
					self.month=None
					if truncation>3:
						self.day=None

	def GetPrecision (self):
		if self.day is None:
			if self.month is None:
				if self.year is None:
					if self.century is None:
						return 0
					else:
						return 1
				else:
					return 2
			else:
				return 3
		else:
			return 4
	
	def SetPrecision (self,precision):
		if precision>0:
			if self.century is None:
				self.century=0
			if precision>1:
				if self.year is None:
					self.year=0
				if precision>2:
					if self.month is None:
						self.month=1
					if precision>3:
						if self.day is None:
							self.day=1
					else:
						self.day=None
				else:
					self.month=self.day=None
			else:
				self.year=self.month=self.day=None
		else:
			self.century=self.year=self.month=self.day=None
				
	def __cmp__ (self,other):
		"""ISODate can hold partially specified dates, which raises the problem of comparisons
		between things such as 1985 and January.  We take a fairly strict view here, forcing
		the two dates to be equally specified (that is, equal amounts of truncation and
		precision).  Although at first site it may be tempting to declare 1st April to be
		greater than March, it is harder to determine the relationship between 1st April and
		April itself."""
		if not isinstance(other,ISODate):
			other=ISODate(other)
		if self.GetTruncation()!=other.GetTruncation() or self.GetPrecision()!=other.GetPrecision():
			raise ISODateComparisonError()
		if self.century is None or self.century==other.century:
			if self.year is None or self.year==other.year:
				if self.month is None or self.month==other.month:
					if self.day is None or self.day==other.day:
						return 0
					elif self.day<other.day:
						return -1
					else:
						return 1
				elif self.month<other.month:
					return -1
				else:
					return 1
			elif self.year<other.year:
				return -1
			else:
				return 1
		elif self.century<other.century:
			return -1
		else:
			return 1
	
	def GetDate (self,dst):
		dst.century,dst.year=self.century,self.year
		dst.month,dst.day=self.month,self.day
		
	def SetDate (self,src):
		self.century,self.year=src.century,src.year
		self.month,self.day=src.month,src.day
	
	def GetAbsoluteDay (self):
		"""Return a notional day number - with 1 being the 0001-01-01 which is the base day of our calendar."""
		if not self.FullySpecified():
			raise ISOAmbiguousDateError()
		absYear=self.century*100+self.year-1
		return (absYear/4)-(absYear/100)+(absYear/400)+(absYear*365)+self.GetOrdinal()
	
	def SetAbsoluteDay (self,absDay):
		quadCentury=146097	# 365*400+97 always holds
		century=36524		# 365*100+24 excludes centennial leap
		quadYear=1461		# 365*4+1    includes leap
		# Shift the base so that day 0 1st Jan, makes the year calculation easier
		absDay=absDay-1
		# All quad centuries are equal
		absYear=400*(absDay/quadCentury)
		absDay=absDay%quadCentury
		# A quad century has one more day than 4 centuries because it ends in a leap year
		# We must check for this case specially to stop abother 4 complete centuries be added!
		if absDay==(quadCentury-1):
			absYear=absYear+399
			absDay=365
		else:
			absYear=absYear+100*(absDay/century)
			absDay=absDay%century
			# A century has one fewer days than 25 quad years so we are safe this time
			absYear=absYear+4*(absDay/quadYear)
			absDay=absDay%quadYear
			# However, a quad year has 1 more day than 4 years so we have a second special case
			if absDay==(quadYear-1):
				absYear=absYear+3
				absDay=365
			else:
				absYear=absYear+(absDay/365)
				absDay=absDay%365
		absYear=absYear+1
		# Finally, return the base so that 1 is the 1st of Jan for setting the ordinal
		self.SetOrdinal(absYear/100,absYear%100,absDay+1)
					
	def AddAbsoluteDays (self,days):
		if days:
			self.SetAbsoluteDay(self.GetAbsoluteDay()+days)
		
	def GetOrdinal (self):
		if not self.FullySpecified():		
			raise ISOAmbiguousDateError()
		else:
			if LeapYear(self.century*100+self.year):
				mSizes=MONTH_SIZES_LEAPYEAR
			else:
				mSizes=MONTH_SIZES
			ordinal=self.day
			for m in mSizes[:self.month-1]:
				ordinal=ordinal+m
			return ordinal

	def SetOrdinal (self,century,year,ordinalDay,baseDate=None):
		if century is None:
			if baseDate is None or not baseDate.FullySpecified():
				raise ISOAmbiguousDateError()
			century=baseDate.century
			if year is None:
				year=baseDate.year
				if ordinalDay<baseDate.GetOrdinal():
					year=year+1
					if year==100:
						year=0
						century=century+1
			elif year<baseDate.year or (year==baseDate.year and ordinalDay<baseDate.GetOrdinal()):
				century=century+1
		if century<0 or century>99 or year<0 or year>99:
			raise ISOInvalidDateError()
		self.century=century
		self.year=year
		if LeapYear(century*100+year):
			mSizes=MONTH_SIZES_LEAPYEAR
		else:
			mSizes=MONTH_SIZES
		self.month=1
		self.day=ordinalDay
		for m in mSizes:
			if self.day>m:
				self.day=self.day-m
				self.month=self.month+1
			else:
				break
		if self.day<1 or self.month>12:
			self.month=None
			self.day=None
			raise ISOBadOrdinalDateError(ordinalDay)
	
	def GetWeekday (self):
		"""Returns a 3-tuple of year, week number, day-of-week (1==Monday, 7=Sunday)"""
		if not self.FullySpecified():
			raise ISOAmbiguousDateError()
		else:
			absYear=self.century*100+self.year
			absYearLength=365+LeapYear(absYear)
			ordinal=self.GetOrdinal()
			dow=DayOfWeek(absYear,self.month,self.day)
			thursday=ordinal+4-dow
			if thursday<1:
				# Thursday this week was actually last year, and so we are
				# part of the last calendar week of last year too.
				absYear=absYear-1
				return absYear,WeekCount(absYear),dow	
			elif thursday>absYearLength:
				# Thursday this week is actually next year, and so we are
				# part of the first calendar week of next year too.
				absYear=absYear+1
				return absYear,1,dow
			else:
				# We are part of this year, but which week?  Jan 4th is always
				# part of the first week of the year, so we calculate the ordinal
				# value of the Monay that began that week 
				yearBase=5-DayOfWeek(absYear,1,4)
				return absYear,(ordinal-yearBase)/7+1,dow

	def SetWeekday (self,century,decade,year,week,day,baseDate=None):
		if century is None:
			if baseDate is None or not baseDate.FullySpecified():
				raise ISOAmbiguousDateError()
			weekOverflow=0
			absBaseYear,baseWeek,baseDay=baseDate.GetWeekday()
			century=absBaseYear/100
			baseDecade=(absBaseYear%100)/10
			baseYear=(absBaseYear%10)
			if decade is None:
				decade=baseDecade
				if year is None:
					year=baseYear
					if week is None:
						week=baseWeek
						if day<baseDay:
							# must be next week then
							week=week+1
							weekOverflow=1	
					else:
						if week<baseWeek or (week==baseWeek and day<baseDay):
							# must be next year then
							year=year+1
				else:
					if year<baseYear:
						decade=decade+1
					elif year==baseYear:
						if week<baseWeek or (week==baseWeek and day<baseDay):
							# next decade
							decade=decade+1
			else:
				if decade<baseDecade:
					century=century+1
				elif decade==baseDecade:
					if year<baseYear:
						century=century+1
					elif year==baseYear:
						if week<baseWeek or (week==baseWeek and day<baseDay):
							# next century then
							century=century+1
			absYear=century*100+decade*10+year
			if week>WeekCount(absYear):
				if weekOverflow:
					year=year+1
					week=1
				else:
					raise ISOBadWeekDateError(week)
			if year>=10:
				year=year-10
				decade=decade+1
			if decade>=10:
				decade=decade-10
				century=century+1
		# Now we have century, decade, year, week and day
		absYear=century*100+decade*10+year
		ordinalDay=4-DayOfWeek(absYear,1,4)+(week-1)*7+day
		if ordinalDay<1:
			if absYear==0:
				raise ISODateUnderflowError()
			absYear=absYear-1
			if LeapYear(absYear):
				ordinalDay=ordinalDay+366
			else:
				ordinalDay=ordinalDay+365
		else:
			absYearLength=365+LeapYear(absYear)
			if ordinalDay>absYearLength:
				if absYear==9999:
					raise ISODateOverflowError()
				absYear=absYear+1
				ordinalDay=ordinalDay-absYearLength
		self.SetOrdinal(absYear/100,absYear%100,ordinalDay)
		

	def GetTimeTuple (self,timeTuple):
		"""GetTimeTuple changes the year, month and date fields of timeTuple"""
		if self.century is not None and self.year is not None:
			timeTuple[0]=self.century*100+self.year
		else:
			timeTyple[0]=None
		timeTuple[1]=self.month
		timeTuple[2]=self.day
		
	def SetTimeTuple (self,timeTuple):
		self.century=timeTuple[0]/100
		self.year=timeTuple[0]%100
		self.month=timeTuple[1]
		self.day=timeTuple[2]
		if not self.Legal():
			raise ISOInvalidDateError()
			
	def ReadISODate (self,dateStr,baseDate):
		"""Parse a date in one of the formats supported by ISO 8601, using baseDate
		to provide a context for resolving partially specified ordinals."""
		syntax=1
		fields=string.split(dateStr,'-')
		if 'W' in dateStr:
			syntax=self.ParseWeekDate(fields,baseDate)
		else:
			syntax=self.ParseCalendarDate(fields,baseDate)
		if not syntax:
			raise ISODateSyntaxError(dateStr)
	
	def ParseCalendarDate (self,fields,baseDate=None):
		"""Given a list of hyphen delimitted fields create a calendar/ordinal date.
		We divide the supported formats by the number of fields in the first instance
		to make the implementation clearer:
		1 field formats: YYYYMMDD, YYYYDDD, YYMMDD, YYDDD, YYYY, YY
		2 field formats: YYYY-DDD, YYYY-MM, YY-DDD, -YYMM, -DDD, -YY
		3 field formats: YYYY-MM-DD, YY-MM-DD, -YY-MM, --MMDD, --MM
		4 field formats: --MM-DD, ---DD"""
		syntax=''
		nFields=len(fields)
		for fieldStr in fields:
			if fieldStr and not fieldStr.isdigit():
				nFields=0
				break
		if nFields==1:
			fieldStr=fields[0]
			fieldLen=len(fieldStr)
			if fieldLen==8:
				# YYYYMMDD
				self.century=int(fieldStr[:2])
				self.year=int(fieldStr[2:4])
				self.month=int(fieldStr[4:6])
				self.day=int(fieldStr[6:8])
				syntax='YYYYMMDD'
			elif fieldLen==7:
				# YYYYDDD
				self.SetOrdinal(int(fieldStr[:2]),int(fieldStr[2:4]),int(fieldStr[4:]))
				syntax='YYYYDDD'
			elif fieldLen==6:
				# YYMMDD
				self.century=None
				self.year=int(fieldStr[:2])
				self.month=int(fieldStr[2:4])
				self.day=int(fieldStr[4:6])
				syntax='YYMMDD'
			elif fieldLen==5:
				# YYDDD
				self.SetOrdinal(None,int(fieldStr[:2]),int(fieldStr[2:]),baseDate)
				syntax='YYDDD'
			elif fieldLen==4:
				# YYYY
				self.century=int(fieldStr[:2])
				self.year=int(fieldStr[2:])
				self.month=None
				self.day=None
				syntax='YYYY'
			elif fieldLen==2:
				# YY
				self.century=int(fieldStr)
				self.year=self.month=self.day=None
				syntax='YY'
		elif nFields==2:
			fieldStr=fields[0]
			fieldLen=len(fieldStr)
			if fieldLen==4:
				self.century=int(fieldStr[:2])
				self.year=int(fieldStr[2:])
				fieldStr=fields[1]
				fieldLen=len(fieldStr)
				if fieldLen==3:
					# YYYY-DDD
					self.SetOrdinal(self.century,self.year,int(fieldStr))
					syntax='YYYY-DDD'
				elif fieldLen==2:
					# YYYY-MM
					self.month=int(fieldStr)
					self.day=None
					syntax='YYYY-MM'
				else:
					syntax=0
			elif fieldLen==2 and len(fields[1])==3:
				# YY-DDD
				self.SetOrdinal(None,int(fieldStr),int(fields[1]),baseDate)
				syntax='YY-DDD'
			elif fieldLen==0:
				fieldStr=fields[1]
				fieldLen=len(fieldStr)
				if fieldLen==4:
					# -YYMM
					self.century=None
					self.year=int(fieldStr[:2])
					self.month=int(fieldStr[2:])
					self.day=None
					syntax='-YYMM'
				elif fieldLen==3:
					# -DDD
					self.SetOrdinal(None,None,int(fieldStr),baseDate)
					syntax='-DDD'
				elif fieldLen==2:
					# -YY
					self.century=None
					self.year=int(fieldStr)
					self.month=self.day=None
					syntax='-YY'
		elif nFields==3:
			fieldStr=fields[0]
			fieldLen=len(fieldStr)
			if fieldLen==4 and len(fields[1])==2 and len(fields[2])==2:
				# YYYY-MM-DD
				self.century=int(fieldStr[:2])
				self.year=int(fieldStr[2:])
				self.month=int(fields[1])
				self.day=int(fields[2])
				syntax='YYYY-MM-DD'
			elif fieldLen==2 and len(fields[1])==2 and len(fields[2])==2:
				# YY-MM-DD
				self.century=None
				self.year=int(fieldStr)
				self.month=int(fields[1])
				self.day=int(fields[2])
				syntax='YY-MM-DD'
			elif fieldLen==0:
				if len(fields[1])==2 and len(fields[2])==2:
					# -YY-MM
					self.century=None
					self.year=int(fields[1])
					self.month=int(fields[2])
					self.day=None
					syntax='-YY-MM'
				elif len(fields[1])==0:
					fieldStr=fields[2]
					fieldLen=len(fieldStr)
					if fieldLen==4:
						# --MMDD
						self.century=self.year=None
						self.month=int(fieldStr[:2])
						self.day=int(fieldStr[2:])
						syntax='--MMDD'
					elif fieldLen==2:
						# --MM
						self.century=self.year=None
						self.month=int(fieldStr)
						self.day=None
						syntax='--MM'
		elif nFields==4:
			if len(fields[0])==0 and len(fields[1])==0:
				if len(fields[2])==2 and len(fields[3])==2:
					# --MM-DD
					self.century=self.year=None
					self.month=int(fields[2])
					self.day=int(fields[3])
					syntax='--MM-DD'
				elif len(fields[2])==0 and len(fields[3])==2:
					# ---DD
					self.century=self.year=self.month=None
					self.day=int(fields[3])
					syntax='---DD'
		if syntax and not self.Legal():
			raise ISOInvalidDateError()						
		return syntax

	def ParseWeekDate (self,fields,baseDate=None):
		"""Given a list of hyphen delimitted fields create a week date.
		1 field formats: YYYYWwwD, YYYYWww, YYWwwD, YYWww
		2 field formats: YYYY-Www, YY-Www, -YWwwD, -YWww, -WwwD, -Www
		3 field formats: YYYY-Www-D, YY-Www-D, -Www-D, -Y-Www, -W-D
		4 field formats: -Y-Www-D"""
		syntax=''
		nFields=len(fields)
		if nFields==1:
			fieldStr=fields[0]
			fieldLen=len(fieldStr)
			if fieldLen==8 and fieldStr[4]=='W' and \
				fieldStr[:4].isdigit() and fieldStr[5:].isdigit():
				# YYYYWwwD
				self.SetWeekday(int(fieldStr[:2]),int(fieldStr[2]),int(fieldStr[3]),
					int(fieldStr[5:7]),int(fieldStr[7]),baseDate)
				syntax='YYYYWwwD'
			elif fieldLen==7 and fieldStr[4]=='W' and \
				fieldStr[:4].isdigit() and fieldStr[5:].isdigit():
				# YYYYWww
				self.SetWeekday(int(fieldStr[:2]),int(fieldStr[2]),int(fieldStr[3]),
					int(fieldStr[5:7]),1,baseDate)
				syntax='YYYYWww'
			elif fieldLen==6 and fieldStr[2]=='W' and \
				fieldStr[:2].isdigit() and fieldStr[3:].isdigit():
				# YYWwwD
				self.SetWeekday(None,int(fieldStr[0]),int(fieldStr[1]),int(fieldStr[3:5]),
					int(fieldStr[5]),baseDate)
				syntax='YYWwwD'
			elif fieldLen==5 and fieldStr[2]=='W' and \
				fieldStr[:2].isdigit() and fieldStr[3:].isdigit():
				# YYWww
				self.SetWeekday(None,int(fieldStr[0]),int(fieldStr[1]),int(fieldStr[3:5]),1,baseDate)
				syntax='YYWww'
		elif nFields==2:
			fieldStr=fields[1]
			fieldLen=len(fieldStr)
			if fieldLen==3 and fieldStr[0]=='W' and (len(fields[0])==0 or fields[0].isdigit()) and fieldStr[1:].isdigit():
				week=int(fieldStr[1:])
				fieldStr=fields[0]
				fieldLen=len(fieldStr)
				if fieldLen==4:
					# YYYY-Www
					self.SetWeekday(int(fieldStr[:2]),int(fieldStr[2]),int(fieldStr[3]),
						week,1,baseDate)
					syntax='YYYY-Www'
				elif fieldLen==2:
					# YY-Www
					self.SetWeekday(None,int(fieldStr[0]),int(fieldStr[1]),week,1,baseDate)
					syntax='YY-Www'
				elif fieldLen==0:
					# -Www
					self.SetWeekday(None,None,None,week,1,baseDate)
					syntax='-Www'
			elif fieldLen==4 and fieldStr[0]=='W' and fieldStr[1:].isdigit():
				# -WwwD
				self.SetWeekday(None,None,None,int(fieldStr[1:3]),int(fieldStr[3]),baseDate)
				syntax='-WwwD'
			elif fieldLen==4 and fieldStr[1]=='W' and fieldStr[0].isdigit() and \
				fieldStr[2:].isdigit():
				# -YWww
				self.SetWeekday(None,None,int(fieldStr[0]),int(fieldStr[2:]),1,baseDate)
				syntax='-YWww'
			elif fieldLen==5 and fieldStr[1]=='W' and fieldStr[0].isdigit() and \
				fieldStr[2:].isdigit():
				# -YWwwD
				self.SetWeekday(None,None,int(fieldStr[0]),int(fieldStr[2:4]),
					int(fieldStr[4]),baseDate)
				syntax='-YWwwD'
		elif nFields==3:
			fieldStr=fields[1]
			fieldLen=len(fieldStr)
			if fieldLen==3 and fieldStr[0]=='W' and fieldStr[1:].isdigit() and \
				(len(fields[0])==0 or fields[0].isdigit()) and len(fields[2])==1 and fields[2].isdigit():
				week=int(fieldStr[1:])
				day=int(fields[2])
				fieldStr=fields[0]
				fieldLen=len(fieldStr)
				if fieldLen==4:
					# YYYY-Www-D
					self.SetWeekday(int(fieldStr[:2]),int(fieldStr[2]),int(fieldStr[3]),
						week,day,baseDate)
					syntax='YYYY-Www-D'
				elif fieldLen==2:
					# YY-Www-D
					self.SetWeekday(None,int(fieldStr[0]),int(fieldStr[1]),week,day,baseDate)
					syntax='YY-Www-D'
				elif fieldLen==0:
					self.SetWeekday(None,None,None,week,day,baseDate)
					syntax='-Www-D'
			elif fieldStr=='W' and len(fields[0])==0 and len(fields[2])==1 and \
				fields[2].isdigit():
				# -W-D
				self.SetWeekday(None,None,None,None,int(fields[2]),baseDate)
				syntax='-W-D'
			elif len(fields[0])==0 and fieldLen==1 and fieldStr.isdigit() and len(fields[2])==3 and \
				fields[2][0]=='W' and fields[2][1:].isdigit():
				# -Y-Www
				self.SetWeekday(None,None,int(fieldStr),int(fields[2][1:]),1,baseDate)
				syntax='-Y-Www'
		elif nFields==4 and len(fields[0])==0 and len(fields[1])==1 and fields[1].isdigit() and \
			len(fields[2])==3 and fields[2][0]=='W' and fields[2][1:].isdigit() and \
			len(fields[3])==1 and fields[3].isdigit():
			self.SetWeekday(None,None,int(fields[1]),int(fields[2][1:]),int(fields[3]),baseDate)
			syntax='-Y-Www-D'
		return syntax

	def WriteISOCalendarDate (self,basic):
		if self.century is None:
			if self.year is None:
				if self.month is None:
					if self.day is None:
						raise ISOAmbiguousDateError()
					else:
						# ---DD
						return "---"+string.zfill(str(self.day),2)
				else:
					mStr=string.zfill(str(self.month),2)
					if self.day is None:
						# --MM
						return "--"+mStr
					elif basic:
						# --MMDD
						return "--"+mStr+string.zfill(str(self.day),2)
					else:
						# --MM-DD
						return "--"+mStr+"-"+string.zfill(str(self.day),2)
			else:
				yStr=string.zfill(str(self.year),2)
				if self.month is None:
					# -YY
					return "-"+yStr
				else:
					mStr=string.zfill(str(self.month),2)
					if self.day is None:
						if basic:
							# -YYMM
							return "-"+yStr+mStr
						else:
							# -YY-MM
							return "-"+yStr+"-"+mStr
					elif basic:
						# YYMMDD
						return yStr+mStr+string.zfill(str(self.day),2)
					else:
						# YY-MM-DD
						return yStr+"-"+mStr+"-"+string.zfill(str(self.day),2)
		else:
			cStr=string.zfill(str(self.century),2)
			if self.year is None:
				# YY
				return cStr
			else:
				yStr=string.zfill(str(self.year),2)
				if self.month is None:
					# YYYY
					return cStr+yStr
				else:
					mStr=string.zfill(str(self.month),2)
					if self.day is None:
						# YYYY-MM
						return cStr+yStr+"-"+mStr
					elif basic:
						# YYYYMMDD
						return cStr+yStr+mStr+string.zfill(str(self.day),2)
					else:
						# YYYY-MM-DD
						return cStr+yStr+"-"+mStr+"-"+string.zfill(str(self.day),2)
				
	
	def WriteISOOrdinalDate (self,basic,dropCentury=0,dropYear=0):
		dStr=string.zfill(str(self.GetOrdinal()),3)
		if dropCentury:
			if dropYear:
				# -DDD
				return "-"+dStr
			elif basic:
				# YYDDD
				return string.zfill(str(self.year),2)+dStr
			else:
				# YY-DDD
				return string.zfill(str(self.year),2)+"-"+dStr
		elif basic:
			# YYYYDDD
			return string.zfill(str(self.century*100+self.year),4)+dStr
		else:
			# YYYY-DDD
			return string.zfill(str(self.century*100+self.year),4)+"-"+dStr

	def WriteISOWeekDate (self,basic,showDay,dropCentury=0,dropDecade=0,dropYear=0,dropWeek=0):
		wYear,week,weekday=self.GetWeekday()
		wStr='W'+string.zfill(str(week),2)
		if dropCentury:
			if dropDecade:
				if dropYear:
					if dropWeek:
						# -W-D force showDay!
						result="-W"
						showDay=1
						basic=0
					else:
						# -Www/-WwwD/-Www-D
						result="-"+wStr
				else:
					yStr=str(wYear%10)
					if basic:
						# -YWww/-YWwwD
						result="-"+yStr+wStr
					else:
						# -Y-Www/-Y-Www-D
						result="-"+yStr+"-"+wStr
			else:
				yStr=string.zfill(str(wYear%100),2)
				if basic:
					# YYWww/YYWwwD
					result=yStr+wStr
				else:
					# YY-Www/YY-Www-D
					result=yStr+"-"+wStr
		else:
			yStr=string.zfill(str(wYear),4)
			if basic:
				# YYYYWww/YYYYWwwD
				result=yStr+wStr
			else:
				# YYYY-Www/YYYY-Www-D
				result=yStr+"-"+wStr
		if showDay:
			if basic:
				return result+str(weekday)
			else:
				return result+"-"+str(weekday)
		else:
			return result


								
class ISOTime:
	"""A class for representing ISO times"""

	def __init__(self,value=None):
		if type(value) in (types.StringType,types.UnicodeType):
			self.ReadISOTime(value)
		elif isinstance(value,ISOTime):
			self.SetTime(value)
		elif value is None:
			self.Reset()
		else:
			raise ISOTimeCoercionError()
				
	def Reset (self):
		self.hour=self.minute=self.second=None

	def Zero (self):
		self.hour=self.minute=self.second=0
		
	def FullySpecified (self):
		return self.hour is not None and self.minute is not None and self.second is not None

	def Now (self):
		self.SetTimeTuple(time.gmtime(time.time()))
	
	def Legal (self):
		"""Given the effect of timezones, a leap second can occurr at any minutes,
		literally"""
		if self.hour is None:
			if self.minute is None:
				if self.second is None:
					return 1
				else:
					return self.second>=0 and self.second<=60
			elif self.minute<0 or self.minute>59:
				return 0
			elif self.second is None:
				return 1
			else:
				return self.second>=0 and self.second<=60
		elif self.hour==24:
			if self.minute is None:
				return self.second is None
			elif self.minute!=0:
				return 0
			elif self.second is None:
				return 1
			elif self.second!=0:
				return 0
			else:
				return 1
		elif self.hour>24 or self.hour<0:
			return 0
		elif self.minute is None:
			return self.second is None
		elif self.minute<0 or self.minute>59:
			return 0
		elif self.second is None:
			return 1
		else:
			return self.second>=0 and self.second<=60
	
	def GetTruncation (self):
		if self.hour is None:
			if self.minute is None:
				if self.second is None:
					return 3
				else:
					return 2
			else:
				return 1
		else:
			return 0

	def SetTruncation (self,truncation,baseTime=None):
		overflow=0
		if baseTime is not None and self.GetTruncation()>truncation:
			if self.GetPrecision()>baseTime.GetPrecision() or baseTime.GetTruncation():
				raise ISOAmbiguousTimeError()
			if self.hour is None:
				self.hour=baseTime.hour
				if self.minute is None:
					self.minute=baseTime.minute
					if self.second is None:
						self.second=baseTime.second
					elif self.second<baseTime.second:
						self.minute=self.minute+1
				elif self.minute<baseTime.minute:
					self.hour=self.hour+1
				elif self.minute==baseTime.minute and \
					self.second is not None and self.second<baseTime.second:
					self.hour=self.hour+1
				if self.minute>59:
					self.hour=self.hour+1
					self.minute=0
				if self.hour>24 or (self.hour==24 and (self.minute>0 or self.second>0)):
					self.hour=self.hour-24
					overflow=1
				if not self.Legal():
					raise ISOInvalidTimeError()								
		if truncation>0:
			self.hour=None
			if truncation>1:
				self.minute=None
				if truncation>2:
					self.second=None
		return overflow

	def GetPrecision (self):
		if self.second is None:
			if self.minute is None:
				if self.hour is None:
					return 0
				else:
					return 1
			else:
				return 2
		else:
			return 3

	def SetPrecision (self,precision,decimalize=0):
		if precision>0:
			if precision>1:
				if self.minute is None:
					if type(self.hour) is types.FloatType:
						self.minute,self.hour=math.modf(self.hour)
						self.hour=int(self.hour)
						self.minute=self.minute*60
					elif self.hour is not None:
						self.minute=0
				if precision>2:
					if self.second is None:
						if type(self.minute) is types.FloatType:
							self.second,self.minute=math.modf(self.minute)
							self.minute=int(self.minute)
							self.second=self.second*60
						elif self.minute is not None:
							self.second=0
				elif self.minute is None:
					pass
				else:
					if decimalize:
						if self.second is not None:
							self.minute=self.minute+(self.second/60.0)
					self.second=None
			elif self.hour is None:
				# Nothing to do
				pass
			else:
				if decimalize:
					if self.minute is not None:
						self.hour=self.hour+(self.minute/60.0)
						if self.second is not None:
							self.hour=self.hour+(self.second/3600.0)
				self.minute=self.second=None
		else:
			self.hour=self.minute=self.second=None
				
	def __cmp__ (self,other):
		"""ISOTime can hold partially specified times, we deal with comparisons in a similar
		way to ISODate.__cmp__.  Although this behaviour is consistent it might seem strange
		at first as it rules comparing 09:00:15 with 09:00.  Recall though that 09:00 is
		actually all times in the range [09:00:00-09:00:59] if this behaviour seems strange.
		The SetPrecision method should be used to reduce precision to the lowest common
		denominator before ordering times of mixed precision.  In some circumstances it may
		be appropriate to extend the precision in a context where 09:00 means 09:00:00 or
		to use decimization when reducing precision causing 09:00:15 to become 09:00,25 which
		will sort as expect - treating 09:00 as 09:00,0 automatically."""
		if not isinstance(other,ISOTime):
			other=ISOTime(other)
		if self.GetTruncation()!=other.GetTruncation() or self.GetPrecision()!=other.GetPrecision():
			raise ISOTimeComparisonError()
		if self.hour is None or self.hour==other.hour:
			if self.minute is None or self.minute==other.minute:
				if self.second is None or self.second==other.second:
					return 0
				elif self.second<other.second:
					return -1
				else:
					return 1
			elif self.minute<other.minute:
				return -1
			else:
				return 1
		elif self.hour<other.hour:
			return -1
		else:
			return 1
	
	def GetTime (self,dst):
		dst.hour,dst.minute,dst.second=self.hour,self.minute,self.second
	
	def SetTime (self,src):
		self.hour,self.minute,self.second=src.hour,src.minute,src.second
		
	def GetSeconds (self):
		"""Note that leap seconds and midnight ensure that t.SetSeconds(t.GetSeconds()) is in
		no way an identity tranformation on fully-specified times."""
		if not self.FullySpecified():
			raise ISOAmbiguousTimeError()
		return self.second+self.minute*60+self.hour*3600
	
	def SetSeconds (self,s):
		"""Set a fully-specified time based on s seconds past midnight.  If s is greater
		than or equal to the number of seconds in a normal day then the number of whole days
		represented is returned and the time is set to the fractional part of the day, otherwise
		0 is returned.  Negative numbers underflow (and return negative numbers of days"""
		overflow=0
		if type(s) is types.FloatType:
			if s<0:
				# whole numbers of days are adjusted to 00:00:00 rather than 24:00:00
				overflow=-int((-s-1)/86400)-1
				s=math.fmod(-s,86400)
				if s: s=86400-s
			fSeconds,i=math.modf(s)
			s=int(i)
			self.second=(s%60)+fSeconds
		else:
			if s<0:
				overflow=-((-s-1)/86400)-1
				s=(-s)%86400
				if s: s=86400-s
			self.second=s%60
		m=s/60
		self.minute=m%60
		h=m/60
		self.hour=h%24
		return overflow+h/24
	
	def AddSeconds (self,s):
		s1=self.GetSeconds()
		if self.seconds==60:
			# Must be leap second
			# Leap second handling
			if s==0:
				return 0
			elif s>0: 
				return self.SetSeconds(s1-1+s)
			elif s<0:
				return self.SetSeconds(s1+s)
		else:
			# We don't do anything special for 24:00:00 so if s==0 it will overflow
			return self.SetSeconds(s1+s)
	
	def AddZone (self,m):
		"""Adds the number of minutes, m to this time and returns the day over/underflow
		in the same way as AddSeconds.  This method preserves leap seconds.  This method
		poses us with a real problem because time zones are represented in hours or
		minutes independently of the precision of the time they are applied to.  It is
		therefore unavoidable that when changing the zone of a time by fractions of an
		hour that the precision of the time must grow (admittedly a rare occurence)."""
		if self.GetTruncation() or self.GetPrecision()<1:
			raise ISOAmbiguousTimeError()
		if self.minute is not None:
			if self.second is not None:
				saveSecond=self.second
				self.second=0
				overflow=self.SetSeconds(self.GetSeconds()+m*60)
				self.second=saveSecond
			else:
				self.second=0
				overflow=self.SetSeconds(self.GetSeconds()+m*60)
				self.second=None
		else:
			self.second=0
			self.minute=0
			overflow=self.SetSeconds(self.GetSeconds()+m*60)
			self.second=None
			# This is a problem area - if minute is non-zero after the zone
			# change we are forced to grow the precision to accomodate. 
			if self.minute==0:
				self.minute=None
		return overflow
						
	def GetTimeTuple (self,timeTuple):
		"""GetTimeTuple changes the hour, minute and second fields of timeTuple"""
		timeTuple[3]=self.hour
		timeTuple[4]=self.minute
		timeTuple[5]=self.second
		
	def SetTimeTuple (self,timeTuple):
		self.hour=timeTuple[3]
		self.minute=timeTuple[4]
		self.second=timeTuple[5]
		if not self.Legal():
			raise ISOInvalidDateError()

	def ReadISOTime (self,timeStr):
		"""
		hhmmss hh:mm:ss hhmm hh:mm hh hhmmss,ss hh:mm:ss,ss hhmm,mm hh:mm,mm hh,hh
		-mmss -mm:ss -mm --ss -mmss,s -mm:ss,s -mm,m --ss,s"""
		syntax=1
		extended=0
		parse=timeStr
		if parse and parse[0]=='T':
			parse=parse[1:]
		zoneStr=''
		for zSep in 'Z-+':
			# This loop is cunningly different from the similar loop in ReadISOTimePoint
			# in that it ignores a leading '-'.  That's because a leading hyphen indicates
			# a truncated time and truncated times can't have zone specifiers.
			zPos=string.find(parse,zSep)
			if zPos>0:
				zoneStr=parse[zPos:]
				parse=parse[:zPos]
				break;		
		# hour
		if parse and parse[0]=='-':
			self.hour=None
			parse=parse[1:]
		elif len(parse)>=2 and parse[:2].isdigit():
			self.hour=int(parse[:2])
			parse=parse[2:]
			# Fractional hours consumes the rest of the string - one digit in
			# the decimal is required.
			if len(parse)>1 and (parse[0] in ',.') and parse[1:].isdigit():
				self.hour=float(str(self.hour)+"."+parse[1:])
				parse=""
		else:
			raise ISOTimeSyntaxError(timeStr)
		# minute
		if self.hour is None:
			if parse and parse[0]=='-':
				# Truncated forms have different rules
				self.minute=None
				parse=parse[1:]
			elif len(parse)>=2 and parse[:2].isdigit():
				self.minute=int(parse[:2])
				parse=parse[2:]
				if parse and (parse[0] in ',.') and parse[1:].isdigit():
					self.minute=float(str(self.minute)+"."+parse[1:])
					parse=""
			else:
				raise ISOTimeSyntaxError(timeStr)	
		elif parse:
			if parse and parse[0]==':':
				extended=1
				parse=parse[1:]
			if len(parse)>=2 and parse[:2].isdigit():
				self.minute=int(parse[:2])
				parse=parse[2:]
				if len(parse)>1 and (parse[0] in ',.') and parse[1:].isdigit():
					self.minute=float(str(self.minute)+"."+parse[1:])
					parse=""
			else:
				raise ISOTimeSyntaxError(timeStr)	
		else:
			self.minute=None
		# seconds
		if parse:
			if extended or self.minute is not None:
				if parse and parse[0]==':':
					parse=parse[1:]
				elif extended:
					raise ISOTimeSyntaxError(timeStr)
			if len(parse)>=2 and parse[:2].isdigit():
				self.second=int(parse[:2])
				parse=parse[2:]
				# Truncated forms can have an empty decimal part if desired
				if len(parse)>(1-(self.hour is None)) and (parse[0] in ',.') and parse[1:].isdigit():
					self.second=float(str(self.second)+"."+parse[1:])
					parse=""
			else:
				raise ISOTimeSyntaxError(timeStr)
		elif self.hour is None and self.minute is None:
			raise ISOTimeSyntaxError(timeStr)
		else:
			self.second=None
		if not self.Legal():
			raise ISOInvalidTimeError()
		# If there was a zone specifier return the result of that.
		if zoneStr:
			return ReadISOTimeZone(zoneStr)
		else:
			return None
	
	def FormatDecimal (self, value, ndigits, fpSep):
		vd,vi=math.modf(value)
		if ndigits>0:
			return string.zfill(str(int(vi)),2)+fpSep+(('%.'+str(ndigits)+'f')%vd)[2:]
		else:
			return string.zfill(str(int(vi)),2)+fpSep
		
	def WriteISOTime (self,basic,ndigits=3,fpSep=','):
		if self.hour is None:
			if self.minute is None:
				if self.second is None:
					raise ISOAmbiguousTimeError()
				elif type(self.second) is types.FloatType:
					result="--"+self.FormatDecimal(self.second,ndigits,fpSep)
				else:
					result="--"+string.zfill(str(self.second),2)
			elif type(self.minute) is types.FloatType:
				result="-"+self.FormatDecimal(self.minute,ndigits,fpSep)
			else:
				result="-"+string.zfill(str(self.minute),2)
				if self.second is not None:
					if not basic:
						result=result+":"
					if type(self.second) is types.FloatType:
						result=result+self.FormatDecimal(self.second,ndigits,fpSep)
					else:
						result=result+string.zfill(str(self.second),2)
		elif type(self.hour) is types.FloatType:
			# Values that are not truncated must have at least one trailing decimal digit
			# if digit format is used
			if ndigits<1: ndigits=1
			result=self.FormatDecimal(self.hour,ndigits,fpSep)
		else:
			if ndigits<1: ndigits=1
			result=string.zfill(str(self.hour),2)
			if self.minute is not None:
				if not basic:
					result=result+":"
				if type(self.minute) is types.FloatType:
					result=result+self.FormatDecimal(self.minute,ndigits,fpSep)
				else:
					result=result+string.zfill(str(self.minute),2)
					if self.second is not None:
						if not basic:
							result=result+":"
						if type(self.second) is types.FloatType:
							result=result+self.FormatDecimal(self.second,ndigits,fpSep)
						else:
							result=result+string.zfill(str(self.second),2)
		return result


class ISOTimePoint:
	"""A class for representing ISO timepoints"""

	def __init__(self,value=None):
		if type(value) in (types.StringType,types.UnicodeType):
			self.ReadISOTimePoint(value)
		elif isinstance(value,ISOTimePoint):
			self.SetTimePoint(value)
		elif value is None:
			self.Reset()
		else:
			raise ISOTimePointCoercionError()
				
	def Reset (self):
		self.date=ISODate()
		self.time=ISOTime()
		self.zone=None

	def Zero (self):
		self.date.Zero()
		self.time.Zero()
		self.zone=0
		
	def FullySpecified (self):
		return self.date.FullySpecified() and self.time.FullySpecified() and self.zone is not None

	def Now (self,localTime):
		t=time.time()
		utcTuple=time.gmtime(t)
		self.date.SetTimeTuple(utcTuple)
		self.time.SetTimeTuple(utcTuple)
		self.zone=0
		if localTime:
			localTuple=time.localtime(t)
			localDate=ISODate()
			localDate.SetTimeTuple(localTuple)
			if localDate<self.date:
				self.zone=-1440
			elif localDate>self.date:
				self.zone=+1440
			else:
				self.zone=0
			localTime=ISOTime()
			localTime.SetTimeTuple(localTuple)
			self.zone=self.zone+int(localTime.GetSeconds()-self.time.GetSeconds())/60
			self.date=localDate
			self.time=localTime
		else:
			zone=0
	
	def UnixTime (self,unixEpoch):
		self.date.century=19
		self.date.year=70
		self.date.month=self.date.day=1
		self.date.AddAbsoluteDays(self.time.SetSeconds(unixEpoch))
		self.zone=0
				
	def Legal (self):
		"""Time must not be truncated and date must be full precision"""
		if not self.date.Legal() or self.date.GetPrecision()<4:
			return 0
		elif not self.time.Legal() or self.time.GetTruncation():
			return 0
		elif self.zone is not None:
			return self.zone>-1440 and self.zone<1440
		else:
			return 1
	
	def GetTruncation (self):
		return self.date.GetTruncation()
	
	def SetTruncation (self, truncation, baseTimePoint=None):
		if baseTimePoint and baseTimePoint.zone!=self.zone:
			baseTimePoint=ISOTimePoint(baseTimePoint)
			baseTimePoint.ChangeZone(self.zone)
		self.date.SetTruncation(truncation,baseTimePoint.date)
		
	def GetPrecision (self):
		return self.time.GetPrecision()
	
	def SetPrecision (self,precision,decimalize=0):
		self.time.SetPrecision(precision,decimalize)
	
	def __cmp__ (self,other):
		if not isinstance(other,ISOTimePoint):
			other=ISOTimePoint(other)
		if self.GetTruncation()!=other.GetTruncation() or self.GetPrecision()!=other.GetPrecision():
			raise ISOTimePointComparisonError()
		if other.zone!=self.zone:
			other=ISOTimePoint(other)
			other.ChangeZone(self.zone)
		if self.date<other.date:
			return -1
		elif self.date>other.date:
			return 1
		elif self.time<other.time:
			return -1
		elif self.time>other.time:
			return 1
		else:
			return 0
	
	def GetTimePoint (self,dst):
		dst.date=ISODate(self.date)
		dst.time=ISOTime(self.time)
		dst.zone=self.zone
	
	def SetTimePoint (self,src):
		self.date=ISODate(src.date)
		self.time=ISOTime(src.time)
		self.zone=src.zone
	
	def GetTimeTuple (self,timeTuple):
		self.date.GetTimeTuple(timeTuple)
		self.time.GetTimeTuple(timeTuple)
	
	def SetTimeTuple (self,timeTuple):
		self.date.SetTimeTuple(timeTuple)
		self.time.SetTimeTuple(timeTuple)
		self.zone=None
	
	def ChangeZone (self,newZone):
		if newZone is None:
			self.zone=None
		elif self.zone is None:
			raise ISOAmbiguousTimePointError()
		elif self.zone!=newZone:
			self.date.AddAbsoluteDays(self.time.AddZone(newZone-self.zone))
	
	def ReadISOTimePoint (self,timePointStr):
		tPos=string.find(timePointStr,'T')
		if tPos<0:
			raise ISOTimePointSyntaxError(timePointStr)	
		dateStr=timePointStr[:tPos]
		timeStr=timePointStr[tPos:]
		zoneStr=''
		for zSep in 'Z-+':
			zPos=string.find(timeStr,zSep)
			if zPos>=0:
				zoneStr=timeStr[zPos:]
				timeStr=timeStr[:zPos]
				break;
		self.date=ISODate(dateStr)
		self.time=ISOTime(timeStr)
		if zoneStr:
			self.zone=ReadISOTimeZone(zoneStr)
		else:
			self.zone=None
		if not self.Legal():
			raise ISOInvalidTimePointError()
	
	def WriteISOTimeZone (self,basic,useZ=0,hideMins=0):
		if self.zone is None:
			result=""
		elif self.zone==0 and useZ:
			result="Z"
		else:
			if self.zone>=0:
				result="+"
				zMins=self.zone
			else:
				result="-"
				zMins=-self.zone
			result=result+string.zfill(str(zMins/60),2)
			if not hideMins:
				if not basic:
					result=result+":"
				result=result+string.zfill(str(zMins%60),2)
		return result
	
	def WriteISOCalendarTimePoint (self,basic,useZ=0,hideMins=0,ndigits=3,fpSep=','):
		result=self.date.WriteISOCalendarDate(basic)
		result=result+"T"+self.time.WriteISOTime(basic,ndigits,fpSep)
		result=result+self.WriteISOTimeZone(useZ,hideMins)
		return result
	
	def WriteISOOrdinalTimePoint (self,basic,useZ=0,hideMins=0,dropCentury=0,dropYear=0,ndigits=3,fpSep=','):
		result=self.date.WriteISOOrdinalDate(basic,dropCentury,dropYear)
		result=result+"T"+self.time.WriteISOTime(basic,ndigits,fpSep)
		result=result+self.WriteISOTimeZone(useZ,hideMins)
		return result

	def WriteISOWeekTimePoint (self,basic,useZ=0,hideMins=0,dropCentury=0,dropDecade=0,dropYear=0,dropWeek=0,
		ndigits=3,fpSep=','):
		# We must show the day-of-week in order to satisfy the precision constraint
		result=self.date.WriteISOWeekDate(basic,1,dropCentury,dropDecade,dropYear,dropWeek)
		result=result+"T"+self.time.WriteISOTime(basic,ndigits,fpSep)
		result=result+self.WriteISOTimeZone(useZ,hideMins)
		return result
		
			
ISO_TEST_DATES=["19850412","1985-04-12","1985-04","1985","19","850412","85-04-12","-8504","-85-04",
		"-85","--0412","--04-12","--04","---12","1985102","1985-102","85102","85-102","-102",
		"1985W155","1985-W15-5","1985W15","1985-W15","85W155","85-W15-5","85W15","85-W15",
		"-5W155","-5-W15-5","-5W15","-5-W15","-W155","-W15-5","-W15","-W-5"]

ISO_TEST_TIMES=["232050","23:30:50","2320","23:20","23","232050,5","23:20:50,5","2320,8","23:20,8","23,3",
		"-2050","-20:50","-20","--50","-2050,5","-20:50,5","-20,8","--50,5","000000","00:00:00",
		"240000","24:00:00","232030Z","2320Z","23Z","23:20:30Z","23:20Z","152746+0100","152746-0500",
		"152746+01","152746-05","15:27:46+01:00","15:27:46-05:00","15:27:46+01","15:27:46-05"]

ISO_TEST_TIMEPOINTS=["19850412T101530","19850412T101530Z","19850412T101530+0400","19850412T101530+04",
		"1985-04-12T10:15:30","1985-04-12T10:15:30Z","1985-04-12T10:15:30+04:00","1985-04-12T10:15:30+04",
		"19850412T1015","1985-04-12T10:15","1985102T1015Z","1985-102T10:15Z","1985W155T1015+0400",
		"1985-W15-5T10:15+04"]
		
#	"""
#	Timezone specifiers:
#	Z
#	+hhmm
#	+hh
#	+hh:mm
#	"""

def TestAbsoluteDays (dMax):
	dNum=1
	d=ISODate()
	dMatch=ISODate()
	d.century=0
	d.year=1
	d.month=d.day=1
	print "Tested AbsoluteDay routines from "+d.WriteISOCalendarDate(0)+" to..."
	while dNum<=dMax:
		if dNum!=d.GetAbsoluteDay():
			print d.WriteISOCalendarDate(0)+"  :  GetAbsoluteDay FAILED"
		dMatch.SetAbsoluteDay(dNum)
		if d!=dMatch:
			print d.WriteISOCalendarDate(0)+"  :  SetAbsoluteDay FAILED ("+str(dNum)+")"
		d.day=d.day+1
		if not d.Legal():
			d.day=1
			d.month=d.month+1
			if not d.Legal():
				d.month=1
				d.year=d.year+1
				if not d.Legal():
					d.year=0
					d.century=d.century+1
					if not d.Legal():
						break
		dNum=dNum+1
	print "..."+d.WriteISOCalendarDate(0)

			
if __name__=='__main__':
	TestAbsoluteDays(800000)			
	print ""
	tp=ISOTimePoint()
	tp.Now(1)
	print tp.WriteISOCalendarTimePoint(0)
	print tp.WriteISOOrdinalTimePoint(0)
	print tp.WriteISOWeekTimePoint(0)
	print ""
	for testTimePoint in ISO_TEST_TIMEPOINTS:
		tp=ISOTimePoint(testTimePoint)
		print "Source : "+testTimePoint+"  Output : "+tp.WriteISOCalendarTimePoint(1)
	print ""	
	for testTime in ISO_TEST_TIMES:
		t=ISOTime(testTime)
		print "Source : "+testTime+"  Output : "+t.WriteISOTime(0,4,'.')
	print ""
	testDate=ISODate('19850412')
	baseDate=ISODate('19850408')
	print ""
	for basic in (0,1):
		print ISODate(testDate.WriteISOOrdinalDate(basic),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOOrdinalDate(basic,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOOrdinalDate(basic,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,0),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,0,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,0,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,1,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,0,1,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,1,1,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,0,1,1,1,1),baseDate).WriteISOCalendarDate(0)
		print ISODate(testDate.WriteISOWeekDate(basic,1,1,1,1,1),baseDate).WriteISOCalendarDate(0)
		
		