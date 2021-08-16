import urllib.request
import json
import sys
import os
import re
import time
import datetime
import hashlib
import base64
from packaging import version
from pathvalidate import sanitize_filename

# BEGIN CLASS LOTABuilds
class LOTABuilds:

  def __init__(self,buffer = False):
    self.__builds = []
    self.__buffer = buffer
    
  def loadGithub(self):
    if not os.path.isfile('github.json'):
      print('No config present')
    file = open('github.json')
    repos = json.load(file)
    file.close()
    if self.__buffer:
      if self.__hasBufferdReleases():
        if input('Refresh buffered releases? [Y/N = default]').lower() == 'y':
          self.__deleteBufferedReleases()
    else:
      self.__deleteBufferedReleases()
    for repo in repos:
      releases = {}
      if self.__buffer:
        releases = self.__loadBufferedReleases(repo['name'])
      if not releases:
        releases = self.__loadGithubReleases(repo['name'])
        if self.__buffer:
          self.__saveBufferedReleases(repo['name'],releases)
      for release in releases:
        self.__parseGithubBuild(release)

  def __loadGithubReleases(self,repo):
    request = urllib.request.Request('https://api.github.com/repos/'+repo+'/releases')
    request.add_header('user-agent', 'curl/7.68.0')
    request.add_header('Accept', 'application/vnd.github.v3+json')
    response = urllib.request.urlopen(request)
    content = response.read()
    encoding = response.info().get_content_charset('utf-8')
    return json.loads(content.decode(encoding))

  def __hasBufferdReleases(self):
    if not os.path.isdir('buffer') or not os.listdir('buffer'):
      return False
    return True

  def __prepareBuffer(self):
    if not os.path.isdir('buffer'):
      os.mkdir('buffer')

  def __loadBufferedReleases(self,repo):
    self.__prepareBuffer()
    filename = 'buffer/'+sanitize_filename(repo)+'.json'
    if os.path.isfile(filename):
      file = open(filename, 'r')
      result = json.loads(file.read())
      file.close()
      return result
    return {}

  def __saveBufferedReleases(self,repo,releases):
    if releases:
      self.__prepareBuffer()
      filename = 'buffer/'+sanitize_filename(repo)+'.json'
      file = open(filename, 'w')
      json.dump(releases,file,indent=4)
      file.close()

  def __deleteBufferedReleases(self):
    if os.path.isdir('buffer'):
      self.__clearFolder('buffer')

  def __parseGithubBuild(self,release):
    archives = []
    props = []
    md5sums = []
    changelogs = []
    build = {}
    # First split all assets because they are not properly sorted
    for asset in release['assets']:
      if asset['content_type'] == 'application/zip':
        archives.append(asset)
      else:
        extension = os.path.splitext(asset['name'])[1]
        if extension == '.txt':
          changelogs.append(asset)
        elif extension == '.html':
          changelogs.append(asset)
        elif extension == '.md5sum':
          md5sums.append(asset)
        elif extension == '.prop':
          props.append(asset)
    for archive in archives:
      tokens = self.__parseFilenameFull(archive['name'])
      build['filePath'] = archive['browser_download_url']
      build['url'] = archive['browser_download_url']
      build['channel'] = self.__getChannel(re.sub('/[0-9]/','',tokens[3]), tokens[0], tokens[1])
      build['filename'] = archive['name']
      build['timestamp'] = int(time.mktime(datetime.datetime.strptime(archive['updated_at'],'%Y-%m-%dT%H:%M:%SZ').timetuple()))
      build['model'] = tokens[5] if tokens[1] == 'cm' else tokens[4]
      build['version'] = tokens[1]
      build['size'] = archive['size']
    for prop in props:
      properties = self.__loadProperties(prop['browser_download_url'])
      build['timestamp'] = int(properties.get('ro.build.date.utc',build['timestamp']))
      build['incremental'] = properties.get('ro.build.version.incremental','')
      build['apiLevel'] = properties.get('ro.build.version.sdk','')
      build['model'] = properties.get('ro.lineage.device',properties.get('ro.cm.device',build['model']))
    for md5sum in md5sums:
      md5s = self.__loadMd5sums(md5sum['browser_download_url'])
      build['md5'] = md5s.get(build['filename'],'')
    for changelog in changelogs:
      build['changelogUrl'] = changelog['browser_download_url']
    if not 'changelogUrl' in build:
      build['changelogUrl'] = release['html_url']
    seed = str(build.get('timestamp',0))+build.get('model','')+build.get('apiLevel','')
    build['uid'] = hashlib.sha256(seed.encode('utf-8')).hexdigest()
    self.__builds.append(build)

  def __parseFilenameFull(self,fileName):
    #  tokens Schema:
    #    array(
    #      0 => [TYPE] (ex. cm, lineage, etc.)
    #      1 => [VERSION] (ex. 10.1.x, 10.2, 11, etc.)
    #      2 => [DATE OF BUILD] (ex. 20140130)
    #      3 => [CHANNEL OF THE BUILD] (ex. RC, RC2, NIGHTLY, etc.)
    #      4 =>
    #        CM => [SNAPSHOT CODE] (ex. ZNH0EAO2O0, etc.)
    #        LINEAGE => [MODEL] (ex. i9100, i9300, etc.)
    #      5 =>
    #        CM => [MODEL] (ex. i9100, i9300, etc.)
    #        LINEAGE => [SIGNED] (ex. signed)
    #    )
    matches = re.match(r'([A-Za-z0-9]+)?-([0-9\.]+)-([\d_]+)?-([\w+]+)-([A-Za-z0-9_]+)?-?([\w+]+)?', fileName)
    if not matches:
      return [''] * 6
    return self.__removeTrailingDashes(matches.group(1,2,3,4,5,6))

  def __removeTrailingDashes(self,tokens):
    result = []
    for token in tokens:
      if token:
        result.append(token.strip('-'))
      else:
        result.append('')
    return result

  def __getChannel(self,tokenChannel,tokenType,tokenVersion):
    result = 'stable'
    channel = tokenChannel.lower()
    if channel:
      result = channel
      if tokenType == 'cm' or version.parse(tokenVersion) < version.parse('14.1'):
        if channel== 'experimental':
          result = 'snapshot'
        elif channel == 'unofficial':
          result = 'nightly'
    return result

  def __loadFile(self,url):
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request)
    content = response.read()
    encoding = response.info().get_content_charset('utf-8')
    return content.decode(encoding).splitlines()
    
  def __loadProperties(self,url):
    lines = self.__loadFile(url)
    lines = [x for x in lines if x and not x.startswith('#')]
    return dict(map(lambda s : s.split('='), lines))       

  def __loadMd5sums(self,url):
    lines = self.__loadFile(url)
    return dict(map(lambda s : list(reversed(s.split('  '))), lines))

  def __clearFolder(self,folder):
    for root, dirs, files in os.walk(folder, topdown=False):
      for name in files:
        os.remove(os.path.join(root, name))
      for name in dirs:
        os.rmdir(os.path.join(root, name))

  def __prepareOutput(self):
    if not os.path.isdir('api'):
      os.mkdir('api')
    if not os.path.isdir('api/v1'):
      os.mkdir('api/v1')
    self.__clearFolder('api/v1')

  def writeApiFiles(self):
    self.__prepareOutput()
    models = set([build['model'] for build in self.__builds])
    channels = set([build['channel'] for build in self.__builds])
    for model in models:
      for channel in channels:
        updates = []
        for build in self.__builds:
          if build['model'] == model:
            if build['channel'] == channel:
              update = {}
              # CyanogenMod
              update['incremental'] = build.get('incremental','')
              update['api_level'] = build.get('apiLevel','')
              update['url'] = build.get('url','')
              update['timestamp'] = build.get('timestamp',0)
              update['md5sum'] = build.get('md5','')
              update['changes'] = build.get('changelogUrl','')
              update['channel'] = channel
              update['filename'] = build.get('filename','')
              # LineageOS
              update['romtype'] = channel
              update['datetime'] = build.get('timestamp',0)
              update['version'] = build.get('version','')
              update['id'] = build.get('uid','')
              update['size'] = build.get('size',0)
              updates.append(update)
        if updates:
          response = { "response" : updates }
          file = open('api/v1/'+model+'_'+channel,'w')
          json.dump(response,file,indent=4)
          file.close()
# END CLASS LOTABuilds

def main():
  if len(sys.argv) == 1:
    loatbuilds = LOTABuilds()
  elif len(sys.argv) == 2:
    if sys.argv[1] == '-b':
      loatbuilds = LOTABuilds(True)
    else:
      return
  else:
    return
  loatbuilds.loadGithub()
  loatbuilds.writeApiFiles()

if __name__ == '__main__':
    main()
