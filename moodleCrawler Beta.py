#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#  Copyright 2017 Daniel Vogt
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import cookielib
import urllib2
import urllib
import io
import os
import os.path
import hashlib
import sys
import stat
import md5
import re
import filecmp
import sys
import cgi

from datetime import datetime
from ConfigParser import ConfigParser



def checkQuotationMarks(settingString):
   if not settingString is None and settingString[0] == "\"" and settingString[-1] == "\"":
      settingString = settingString[1:-1]
   if settingString is None:
      settingString = ""
   return settingString
 


def addSlashIfNeeded(settingString):
   if not settingString is None and not settingString[-1] == "/":
      settingString = settingString + "/"
   return settingString



def normPath(pathSring):
   return os.path.normpath(pathSring)



def removeSpaces(pathString):
   return pathString.replace(" ", "")



#get Config
conf = ConfigParser()
project_dir = os.path.dirname(os.path.abspath(__file__))
conf.read(os.path.join(project_dir, 'config.ini'))
  

root_directory = normPath(checkQuotationMarks(conf.get("dirs", "root_dir")))
username = checkQuotationMarks(conf.get("auth", "username"))
password = checkQuotationMarks(conf.get("auth", "password"))
crawlforum = checkQuotationMarks(conf.get("crawl", "forum")) #/forum/
crawlwiki = checkQuotationMarks(conf.get("crawl", "wiki")) #/wiki/
usehistory = checkQuotationMarks(conf.get("crawl", "history")) #do not recrawl
loglevel = checkQuotationMarks(conf.get("crawl", "loglevel"))
downloadExternals = checkQuotationMarks(conf.get("crawl", "externallinks"))
maxdepth = checkQuotationMarks(conf.get("crawl", "maxdepth"))


authentication_url = checkQuotationMarks(conf.get("auth", "url"))
useColors = checkQuotationMarks(conf.get("other", "colors"))




#Import Libs if needed
try:
   from bs4 import BeautifulSoup
except Exception as e:
   print("Module BeautifulSoup4 is missing!")
   exit(1)

if useColors == "true":
   try:
      from colorama import init
   except Exception as e:
      print("Module Colorama is missing!")
      exit(1)
   
   try:
      from termcolor import colored
   except Exception as e:
      print("Module Termcolor is missing!")
      exit(1)

   # use Colorama to make Termcolor work on Windows too
   init()


#utf8 shit
reload(sys)
sys.setdefaultencoding('utf-8')

#Setup Dump Search
filesBySize = {}


#Setup Loader
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36')]
urllib2.install_opener(opener)


#setup crawler live history
visitedPages = set() #hashtable -> faster !?


def walker(arg, dirname, fnames):
    d = os.getcwd()
    os.chdir(dirname)
    try:
        fnames.remove('Thumbs')
    except ValueError:
        pass
    for f in fnames:
        if not os.path.isfile(f):
            continue
        size = os.stat(f)[stat.ST_SIZE]
        if size < 100:
            continue
        if filesBySize.has_key(size):
            a = filesBySize[size]
        else:
            a = []
            filesBySize[size] = a
        a.append(os.path.join(dirname, f))
    os.chdir(d)



#Log levels:
# - Level 0: Minimal Information + small Errors
# - Level 1: More Information + Successes 
# - Level 2: Doing Statemants + Found information
# - Level 3: More Errors + More Infos
# - Level 4: More Doing Statements + Dowload Info + Scann Dublicates
# - Level 5: More Download Info + More Info about dublicates

 
def log(logString, level=0):
   logString = logString.encode('utf-8')
   if useColors == "true":
      if level <= int(loglevel):
         if level == 0:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)
         elif level == 1:
            print(colored(datetime.now().strftime('%H:%M:%S') + " " + logString, "green"))
         elif level == 2:
            print(colored(datetime.now().strftime('%H:%M:%S') + " " + logString, "yellow"))
         elif level == 3:
            print(colored(datetime.now().strftime('%H:%M:%S') + " " + logString, "red"))
         elif level == 4:
            print(colored(datetime.now().strftime('%H:%M:%S') + " " + logString, "magenta"))
         elif level == 5:
            print(colored(datetime.now().strftime('%H:%M:%S') + " " + logString, "cyan"))
   else:
      if level <= int(loglevel):
         if level == 0:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)
         elif level == 1:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString) 
         elif level == 2:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)
         elif level == 3:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)
         elif level == 4:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)
         elif level == 5:
            print(datetime.now().strftime('%H:%M:%S') + " " + logString)



def donwloadFile(downloadFileResponse):
   log("Download has started.", 4)
       
   downloadFileContent = ""
   
   if downloadFileResponse is None:
      log("Faild to download file", 4)
      return ""

   try:
       total_size = downloadFileResponse.info().getheader('Content-Length').strip()
       header = True
   except Exception as e:
       log("No Content-Length available.", 5)
       header = False # a response doesn't always include the "Content-Length" header
          
   if header:
       total_size = int(total_size)
         
   bytes_so_far = 0
        
   while True:
       downloadFileContentBuffer = downloadFileResponse.read(81924)
       if not downloadFileContentBuffer: 
           break
           
       bytes_so_far += len(downloadFileContentBuffer) 
       downloadFileContent = downloadFileContent + downloadFileContentBuffer
              
       if not header: 
          log("Downloaded %d bytes" % (bytes_so_far), 5)
           
       else:
          percent = float(bytes_so_far) / total_size
          percent = round(percent*100, 2)
          log("Downloaded %d of %d bytes (%0.2f%%)\r" % (bytes_so_far, total_size, percent), 5)
            
          
   log("Download complete.", 4)
   return downloadFileContent



def saveFile(webFileFilename, pathToSave, webFileContent, webFileResponse, webFileHref):
   if webFileFilename == "":
      webFileFilename = "index.html"
            
   if webFileFilename.split('.')[-1] == webFileFilename:
      webFileFilename = webFileFilename + ".html"


   file_name = normPath(addSlashIfNeeded(pathToSave) + webFileFilename)

   if file_name[-4:] == ".php":
      file_name = file_name[:len(file_name) - 4] + ".html"
   
   #file_name = urllib.unquote(url).decode('utf8')
         

   if not os.path.isdir(pathToSave):
      os.makedirs(pathToSave)    

   if os.path.isfile(file_name): 
      fileend = file_name.split('.')[-1]
      filebegin = file_name[:(len(file_name) - len(fileend)) - 1]
         
      ii = 1
      while True:
       new_name = filebegin + "_" + str(ii) + "." + fileend
       if not os.path.isfile(new_name):
          file_name = new_name
          break
       ii += 1
     
   try:
      log("Creating new file: '" +  file_name + "'")
   except Exception as e:
      log("Exception: " + str(e) + "    PathToSave:" +  pathToSave)
      exit(1)


   pdfFile = io.open(file_name, 'wb')
   pdfFile.write(webFileContent)
   webFileResponse.close()
   pdfFile.close()
   return file_name


#adds an entry to the log file ... so that the file gets not recrawled
def addFileToLog(pageLink, filePath):
   logFileWriter = io.open(crawlHistoryFile, 'ab')
   logFileWriter.write(datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " "+ pageLink + " saved to '" + filePath + "'\n")
   logFileWriter.close()
   global logFile
   logFileReader = io.open(crawlHistoryFile, 'rb')
   logFile = logFileReader.read()
   logFileReader.close()



#status:
# 0 - Not logged in
# 1 - Logged in
# 2 - Had to re login
# 3 - Something went wrong

def checkLoginStatus(pageContent):
   PageSoup = BeautifulSoup(pageContent, "lxml") 
   #LoginStatusConntent = PageSoup.find(class_="logininfo")
   LoginStatusConntent = PageSoup.select(".logininfo")

   if not LoginStatusConntent is None or len(LoginStatusConntent) == 0:
   
      log("Checking login status.", 4)  
      #Lookup in the Moodle source if it is standard (login / log in on every page)
      #Is a relogin needed ? Try to figure out when relogin is needed.
      if "Logout" not in str(LoginStatusConntent[-1]) and "logout" not in str(LoginStatusConntent[-1]):
         log("Try to relogin, connection maybe lost.", 3)
         
         try:
            responseLogin = urllib2.urlopen(req, timeout=10)
         except Exception as e:
            raise NotGoodErrror(e)
          
         LoginContents = donwloadFile(responseLogin)
          
          
         if "errorcode=" in responseLogin.geturl():
             log("Cannot login. Check your login data.", 3)
             return 0
         
         #Lookup in the Moodle source if it is standard   ("Logout" on every Page)
         LoginSoup = BeautifulSoup(LoginContents, "lxml") 
         #LoginStatusConntent = LoginSoup.find(class_="logininfo")
         LoginStatusConntent = PageSoup.select(".logininfo")
        
         if LoginStatusConntent is None or ("Logout" not in str(LoginStatusConntent[-1]) and "logout" not in str(LoginStatusConntent[-1])):  
             log("Cannot connect to moodle or Moodle has changed. Crawler is not logged in. Check your login data.", 3)
             return 0
           
         log("Successfully logged in again.", 4)
         #reload page  
         return 2
      else:
         log("Crawler is still loged in.", 4)
         return 1
   else:
      log("No logininfo on this page.", 5)
      return 3    



def decodeFilename(fileName):
  htmlDecode = urllib.unquote(fileName).decode('utf8')
  htmlDecode = htmlDecode.replace('/', '-').replace('\\', '-').replace(' ', '-').replace('#', '-').replace('%', '-').replace('&', '-').replace('{', '-').replace('}', '-').replace('<', '-')
  htmlDecode = htmlDecode.replace('>', '-').replace('*', '-').replace('?', '-').replace('$', '-').replace('!', '-').replace(u'‘', '-').replace('|', '-').replace('=', '-').replace(u'`', '-').replace('+', '-')
  htmlDecode = htmlDecode.replace(':', '-').replace('@', '-').replace('"', '-')
  return htmlDecode



#warning this function exit the stript if it could not load the course list page
#try to crawl all courses from moodlepage/my/
def findOwnCourses(myCoursesURL):
   log("Searching Courses...", 2)
   
   #Lookup in the Moodle source if it is standard (moodlePath/my/ are my courses)
   try:
      responseCourses = urllib2.urlopen(myCoursesURL + "my/", timeout=10)
   except Exception as e:
      log("Connection lost! It is not possible to connect to course page! At: " + myCoursesURL)
      log("Exception details: " + str(e), 5)
      exit(1)
   CoursesContents = donwloadFile(responseCourses)
   
   
   
   
   CoursesContentsSoup = BeautifulSoup(CoursesContents, "lxml")
   
   CoursesContentsList = CoursesContentsSoup.find(id="region-main")
   
   
   #CoursesContentsList = CoursesContents.split('class="block_course_list  block list_block"')[1].split('class="footer"')[0]
   #>Meine Kurse</h2>
    
   if CoursesContentsList is None:
      log("Unable to find courses")
      log("Full page: " +  str(CoursesContents), 5)
      exit(1)
      
   #courseNameList = CoursesContentsList.find_all(class_="course_title")
   courseNameList = CoursesContentsList.select(".coursebox")
   
   #regexCourseName = re.compile('class="course_title">(.*?)</div>')
   #course_list = regexCourseName.findall(str(CoursesContentsList))
   courses = []
   
   #blockCourse = True
   
   for course_string in courseNameList:
       #aCourse = course_string.find('a')
       aCourse = course_string.select("h3 a, h2 a")
       #course_name = aCourse.text.encode('ascii', 'ignore').replace('/', '|').replace('\\', '|').replace(' ', '_').replace('.', '_')
   
       if aCourse is None or len(aCourse) == 0:
          log("No link to this course was found!", 3)
          log("Full page: " +  str(course_string), 5)
          continue
   
       course_name = decodeFilename(aCourse[0].text).strip("-")
   
       course_link = removeSpaces(aCourse[0].get('href'))
       #if course_name == "TINF15B5: Programmieren \ Java":
       #   blockCourse = False
   
       #if blockCourse == False:
       courses.append([course_name, course_link])
       log("Found Course: '" + course_name + "'", 2)


   if len(courses) == 0:
      log("Unable to find courses")
      log("Full page: " + str(CoursesContentsList), 5)

   return courses



def searchfordumps(pathtoSearch):
#find dublication in folder  pathtoSearch
    filesBySize = {}
    log('Scanning directory "%s"....' % pathtoSearch, 5)
    os.path.walk(pathtoSearch, walker, filesBySize)

    log('Finding potential dupes...', 4)
    potentialDupes = []
    potentialCount = 0
    trueType = type(True)
    sizes = filesBySize.keys()
    sizes.sort()
    for k in sizes:
        inFiles = filesBySize[k]
        outFiles = []
        hashes = {}
        if len(inFiles) is 1: continue
        log('Testing %d files of size %d...' % (len(inFiles), k), 5)
        for fileName in inFiles:
            if not os.path.isfile(fileName):
                continue
            aFile = file(fileName, 'r')
            hasher = md5.new(aFile.read(1024))
            hashValue = hasher.digest()
            if hashes.has_key(hashValue):
                x = hashes[hashValue]
                if type(x) is not trueType:
                    outFiles.append(hashes[hashValue])
                    hashes[hashValue] = True
                outFiles.append(fileName)
            else:
                hashes[hashValue] = fileName
            aFile.close()
        if len(outFiles):
            potentialDupes.append(outFiles)
            potentialCount = potentialCount + len(outFiles)
    del filesBySize

    log('Found %d sets of potential dupes...' % potentialCount, 5)
    log('Scanning for real dupes...', 5)

    dupes = []
    for aSet in potentialDupes:
        outFiles = []
        hashes = {}
        for fileName in aSet:
            log('Scanning file "%s"...' % fileName, 5)
            aFile = file(fileName, 'r')
            hasher = md5.new()
            while True:
                r = aFile.read(4096)
                if not len(r):
                    break
                hasher.update(r)
            aFile.close()
            hashValue = hasher.digest()
            if hashes.has_key(hashValue):
                if not len(outFiles):
                    outFiles.append(hashes[hashValue])
                outFiles.append(fileName)
            else:
                hashes[hashValue] = fileName
        if len(outFiles):
            dupes.append(outFiles)

    i = 0
    for d in dupes:
        log('Original is %s' % d[0], 4)
        for f in d[1:]:
            i = i + 1
            log('Deleting %s' % f, 4)
            os.remove(f) 



#log External Link toLog file and File in Folder
def logExternalLink(extlink, extLinkDir):
   if not os.path.isdir(extLinkDir):
      os.makedirs(extLinkDir)   
   
   externalLinkPath = normPath(addSlashIfNeeded(extLinkDir) + "external-links.log")
   boolExternalLinkStored = True

   if os.path.isfile(externalLinkPath):
      externalLinkReadeer = io.open(externalLinkPath, 'rb')
      externallinks = externalLinkReadeer.read()
      externalLinkReadeer.close()
      if not extlink in externallinks:
         log("I will store it in the '" + externalLinkPath + "' file.", 4)
         externalLinkWriter = io.open(externalLinkPath, 'ab')
         externalLinkWriter.write(datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " "+ extlink + "\n")
         externalLinkWriter.close()
         

      else:
         log("This link was stored in the '" + externalLinkPath + "' file earlier.", 5)
         boolExternalLinkStored = False

   else:
      log("I will store it in the '" + externalLinkPath + "' file.", 4)
      externalLinkWriter = io.open(externalLinkPath, 'ab')
      externalLinkWriter.write(datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " "+ extlink + "\n")
      externalLinkWriter.close()

   if boolExternalLinkStored == True:
      logFileWriter = io.open(crawlHistoryFile, 'ab')
      logFileWriter.write(datetime.now().strftime('%d.%m.%Y %H:%M:%S') + " External: "+ extlink + " saved to '" + externalLinkPath + "'\n")
      logFileWriter.close()
      logFileReader = io.open(crawlHistoryFile, 'rb')
      logFile = logFileReader.read()
      logFileReader.close()

   



#try to crawl all links on a moodle page. And runs rekursive this funktion on it
def crawlMoodlePage(pagelink, pagename, parentDir, calledFrom, depth=0):

    if calledFrom is None or calledFrom == "":
       log("Something went wrong! CalledFrom is empty!", 2) 
       calledFrom = ""
    
    #check Parameter
    wrongParameter = False

    if pagelink is None or pagelink == "":
       log("Something went wrong! Pagelink is empty!", 2) 
       pagelink = ""
       wrongParameter = True
        
    if pagename is None or pagename == "":
       log("Something went wrong! Pagename is empty!", 2) 
       pagename = ""
        
    if parentDir is None or parentDir == "":
       log("Something went wrong! ParentDir is empty!", 2) 
       parentDir = ""
       wrongParameter = True
 
    log("Check page: '" + pagelink + "'' named: '" + pagename + "' found on: '" + calledFrom + "'' depth: " + str(depth), 2) 
   
    if depth > maxdepth:
       log("Max depth is reached! Please change the max depth if you want to crawl this link.", 2)
       return

    if wrongParameter == True:
       log("The parameters are to wrong. I return!", 2) 
       return

    #check if link is empty
    if pagelink is None or pagelink == "":
       log("There went something wrong, this is an empty link.", 3)
       return
 
    #korregiere link falls nicht korrekt
    if not pagelink.startswith("https://") and not pagelink.startswith("http://") and not pagelink.startswith("www."):
       if pagelink.startswith('/'):
          pagelink = calledFrom[:(len(calledFrom) - len(calledFrom.split('/')[-1])) - 1] + pagelink
       else:
          pagelink = calledFrom[:len(calledFrom) - len(calledFrom.split('/')[-1])] + pagelink
  
    #check crawl history
    if usehistory == "true" and pagelink in logFile:
       log("This link was crawled in the past. I will not recrawl it, change the settings if you want to recrawl it.", 3)
       return

    #Add link to visited pages
    if pagelink in visitedPages:
       log("This link was viewed in the past. I will not reviewed it.", 3)
       return

    visitedPages.add(pagelink)


    #check if this is an external link
    isexternlink = False

    if not domainMoodle in pagelink:
       log("This is an external link.", 2)
       
       logExternalLink(pagelink, parentDir)
       
       isexternlink = True
       if downloadExternals == "false":
          log("Ups this is an external link. I do not crawl external links. Change the settings if you want to crawl external links.", 3)
          return


    #check if the page is in a forum
    if crawlforum == "false" and "/forum/" in pagelink and isexternlink == False:
       log("Ups this is a forum. I do not crawl this forum. Change the settings if you want to crawl forums.", 3)
       return
    
    #check if the page is in a wiki
    if crawlwiki == "false" and "/wiki/" in pagelink and isexternlink == False:
       log("Ups this is a wiki. I do not crawl this wiki. Change the settings if you want to crawl wikis.", 3)
       return

    #Skip Moodle Pages
    #/user/   = users                               | skipTotaly
    #/badges/ = Auszeichnungen                      | skipTotaly
    #/blog/ = blogs                                 | skipTotaly
    #/feedback/ = feedback page unwichtig ?         | skipTotaly

    #/choicegroup/ = gruppen wahl -- unwichtig ?    | skipTotaly
    #/groupexchange/ = gruppenwechsel unwichtig?    | skipTotaly
    if isexternlink == False:
       if "/user/" in pagelink or  "/badges/" in pagelink or "/blog/" in pagelink or "/feedback/" in pagelink or "/choicegroup/" in pagelink or "/groupexchange/" in pagelink:
          log("This is a moodle page. But I will skip it because it is not important.", 4)
          return



    #try to get a response from link
    try:
       responsePageLink = urllib2.urlopen(pagelink, timeout=10)
    except Exception as e:
       log("Connection lost! Page does not exist!", 2)
       log("Exception details: " + str(e), 5)
       return
     
    #get the filename
    pageFileName = ""
    try:
       pageFileNameEnc = responsePageLink.info()['Content-Disposition']
       value, params = cgi.parse_header(pageFileNameEnc)
       pageFileName = params['filename']
    except Exception as e:
          log("No Content-Disposition available. Exception details: " + str(e), 5)
    if pageFileName is None or pageFileName == "":
       pageFileName = os.path.basename(urllib2.urlparse.urlsplit(pagelink).path)
    
    pageFileName = decodeFilename(pageFileName).strip("-")

    #is this page a html page
    pageIsHtml = False
    if "text/html" in responsePageLink.info().getheader('Content-Type') or pageFileName[-4:] == ".php" or pageFileName[-5:] == ".html":
       pageIsHtml = True

    #cheating: try to fix moodle page names
    if isexternlink == False and pageIsHtml == True:
       pageFileName = pagename + ".html"


    PageLinkContent = donwloadFile(responsePageLink)
    
     
    #check for login status
    if pageIsHtml == True:
       try:
          loginStatus = checkLoginStatus(PageLinkContent) 
       except Exception as e:
          log("Connection lost! It is not possible to connect to moodle!", 3)
          log("Exception details: " + str(e), 5)
          return

       if loginStatus == 0:  #Not logged in
          log("Ups, there went something wrong with the moodle login - this is bad. If this happens again please contect the project maintainer.", 0)
         
          #try to donload anyway ? ++++++++++++++++++++++++++++++++++++

          return

       elif loginStatus == 2: #Relogged in
          log("Recheck Page: '" + pagelink + "'", 4)
          try:
             responsePageLink = urllib2.urlopen(pagelink, timeout=10)
          except Exception as e:
             log("Connection lost! Page does not exist!", 3)
             log("Exception details: " + str(e), 5)
             return
     
          PageLinkContent = donwloadFile(responsePageLink)
          
       elif loginStatus == 3: #Not a moodle Page
          if isexternlink == False:
             log("Strangely, this is not a moodle page! I did not expect that this is an external link!", 3)
             isexternlink = True
 

    pageDir = normPath(addSlashIfNeeded(parentDir) + pagename)

    pageFoundLinks = 0

    isaMoodlePage = False

    page_links = None

    if pageIsHtml == True and isexternlink == False:
       PageSoup = BeautifulSoup(PageLinkContent, "lxml") 
 
       page_links_Soup = PageSoup.find(id="region-main") 

       if not page_links_Soup is None: 
          [s.extract() for s in PageSoup('aside')]
          PageLinkContent = str(PageSoup)

          page_links = page_links_Soup.find_all('a')
   

          pageFoundLinks = len(page_links)
          isaMoodlePage = True 


    #do some filters for moodle pages
    pageSaveDir = parentDir
    doSave = True
    doAddToHistory = False


#/url/ = redirekt unwichtig                     | doNotSave; DoNotRecrawl
#/resource/ = redirekt unwichtig!               | doNotSave; DoNotRecrawl

#/folder/ = folder strukt unwichtig ?           | doNotSave;

#/pluginfile.php/ = download file               | DoNotRecrawl;

#/course/view.php = startpage course            | saveInPagedir

#/page/ = info meistens WICHTIG                 | ???
#/wiki/ = wiki shit                             | saveInPagedir
#/quiz/ = hausaufgaben wichtig ?                | saveInPagedir


    if isaMoodlePage:
         #saveIt in pageDir
         if "/course/view.php" in pagelink or "/wiki/" in pagelink  or "/quiz/" in pagelink:
            pageSaveDir = pageDir

         #Add To History -> not recrawl
         if  "/pluginfile.php/" in pagelink  or "/url/" in pagelink or "/resource/" in pagelink:
            doAddToHistory = True

         #do not save
         if "/folder/" in pagelink  or "/url/" in pagelink  or "/resource/" in pagelink:
            doSave = False

         #remove in every moodle page the action modules


    pageFilePath = "This file was not saved. It is listed here for crawl purposes."
    if doSave:
       pageFilePath = saveFile(pageFileName, pageSaveDir, PageLinkContent, responsePageLink, pagelink)


    if not page_links is None:
      for link in page_links:
         hrefPageLink = link.get('href') 
         nextName = link.text

         #remove moodle shit (at the end of a link text)
         removeShit = link.select(".accesshide")
         if not removeShit is None and len(removeShit) == 1:
           removeShitText = removeShit[0].text
           if nextName.endswith(removeShitText):
               nextName = nextName[:-len(removeShitText)]


         nextName = decodeFilename(nextName).strip("-")


         crawlMoodlePage(hrefPageLink, nextName, pageDir, pagelink, (depth + 1))

  
    # add Link to crawler history
    if isexternlink == True or pageIsHtml == False or doAddToHistory == True: 
       addFileToLog(pagelink, pageFilePath)


 

 

#Setup Login Credentials
moodlePath = ""
useSpecpath = False

if authentication_url.split('?')[0][-16:] == "/login/index.php":
   moodlePath = addSlashIfNeeded(authentication_url.split('?')[0][:-16])
else:
   useSpecpath = True
   log("This script will probably not work. Please use an authentication URL that ends with /login/index.php or contact the project owner.")

payload = {
    'username': username,
    'password': password
}


data = urllib.urlencode(payload)

crawlHistoryFile = normPath(addSlashIfNeeded(root_directory)+ ".crawlhistory.log")




log("Moodle Crawler started working.")

# Connection established?
log("Try to login...", 2)

#Log the credentials
#log("+++++++++ Login Credentials - Remove these lines from the log file +++++++++, 3)
#log("These lines are only for check purposes, 3)
#log("Authentication url: '" + authentication_url + "'", 3)
#log("Username: '" + username + "'", 3)
#log("Password: '" + password + "'", 3)
#log("Root directory: '" + root_directory + "'", 3)
#log("+++++++++ End Login Credentials +++++++++, 3)




#login prozedur
req = urllib2.Request(authentication_url, data)

try:
   responseLogin = urllib2.urlopen(req, timeout=10)
except Exception as e:
   log("Connection lost! It is not possible to connect to login page!")
   log("Exception details: " + str(e), 5)
   exit(1)
   
LoginContents = donwloadFile(responseLogin)
 
if "errorcode=" in responseLogin.geturl():
    log("Cannot login. Check your login data.")
    log("Full url: " + responseLogin.geturl(), 5)
    exit(1)

#Lookup in the Moodle source if it is standard   ("Logout" on every Page)
LoginSoup = BeautifulSoup(LoginContents, "lxml") 

LoginStatusConntent = LoginSoup.select(".logininfo")
if LoginStatusConntent is None or len(LoginStatusConntent) == 0 or ("Logout" not in str(LoginStatusConntent[-1]) and "logout" not in str(LoginStatusConntent[-1])): 
   log("Cannot connect to moodle or Moodle has changed. Crawler is not logged in. Check your login data.") 
   log("Full page: " + str(LoginStatusConntent[-1]), 5)
   exit(1)


log("Logged in!", 1)
 
 

#Get moodle base url

#Lookup in the Moodle source if it is standard (Domain + subfolder)
mainpageURL = addSlashIfNeeded(responseLogin.geturl())  #get mainURL from login response (this is not normal)

domainMoodle = "" 
if mainpageURL.startswith("https://"):
   domainMoodle = mainpageURL[8:]

if mainpageURL.startswith("http://"):
   domainMoodle = mainpageURL[7:]

domainMoodle = domainMoodle.split("/")[0]
 

if useSpecpath == False:  #get mainURL from Login page link (this is normal)
   mainpageURL = moodlePath


#create rootdir ++++++++++++++ warning danger +++++++++++
if not os.path.isdir(root_directory):
   os.makedirs(root_directory)    


 #create crealHistoryfile
if not os.path.isfile(crawlHistoryFile):
   logFileWriter = open(crawlHistoryFile, 'ab')
   logFileWriter.close()
   
logFileReader = open(crawlHistoryFile, 'rb')
logFile = logFileReader.read()
logFileReader.close()




#find own courses (returns an array)
courses = findOwnCourses(mainpageURL)
 

   

#couse loop
current_dir = normPath(addSlashIfNeeded(root_directory))

for course in courses:

    log("Check course: '" + course[0] + "'")
    crawlMoodlePage(course[1], course[0], current_dir, mainpageURL + "my/")

searchfordumps(current_dir)



 
log("Update Complete")
