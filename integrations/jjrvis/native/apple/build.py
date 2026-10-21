"""Build the local Apple clients without purchasing or uploading anything."""
import argparse, json, plistlib, shutil, subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--ios-simulator',action='store_true');parser.add_argument('--identity',default='-');args=parser.parse_args()
out=root/'.build';out.mkdir(exist_ok=True)
ios=args.ios_simulator
app=out/('JJRVIS-iPhone.app' if ios else 'JJRVIS.app')
contents=app if ios else app/'Contents';binary=contents if ios else contents/'MacOS';resources=contents if ios else contents/'Resources'
binary.mkdir(parents=True,exist_ok=True);resources.mkdir(exist_ok=True)
sdk='iphonesimulator' if ios else 'macosx';target='arm64-apple-ios17.0-simulator' if ios else 'arm64-apple-macosx13.0'
sdkpath=subprocess.check_output(['xcrun','--sdk',sdk,'--show-sdk-path'],text=True).strip()
subprocess.run(['xcrun','--sdk',sdk,'swiftc','-swift-version','5','-parse-as-library','-O','-sdk',sdkpath,'-target',target,str(root/'JJRVISApp.swift'),'-o',str(binary/'JJRVIS'),'-framework','SwiftUI','-framework','WebKit','-framework','LocalAuthentication','-framework','Speech','-framework','AVFoundation'],check=True)
info={'CFBundleExecutable':'JJRVIS','CFBundleIdentifier':'com.jjrvis.client','CFBundleName':'JJRVIS','CFBundleDisplayName':'JJRVIS','CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'0.1.0','NSMicrophoneUsageDescription':'JJRVIS listens to your questions when you enable voice.','NSSpeechRecognitionUsageDescription':'JJRVIS transcribes your questions on this device.','NSCameraUsageDescription':'JJRVIS uses the camera only when you enable a camera feature.','NSFaceIDUsageDescription':'Unlock your private JJRVIS workspace.','NSAppTransportSecurity':{'NSAllowsLocalNetworking':True},'CFBundleURLTypes':[{'CFBundleURLName':'JJRVIS','CFBundleURLSchemes':['jjrvis']}],'NSHumanReadableCopyright':'JJRVIS development preview'}
if ios:info.update({'MinimumOSVersion':'17.0','UIDeviceFamily':[1,2],'UILaunchScreen':{},'CFBundleSupportedPlatforms':['iPhoneSimulator'],'LSRequiresIPhoneOS':True,'UIApplicationSceneManifest':{'UIApplicationSupportsMultipleScenes':False,'UISceneConfigurations':{}}})
else:info.update({'LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True,'NSPrincipalClass':'NSApplication'})
(contents/'Info.plist').write_bytes(plistlib.dumps(info))
icon=root.parent.parent/'assets/app-icon-512.png'
if icon.exists() and not ios:
 iconset=out/'JJRVIS.iconset';iconset.mkdir(exist_ok=True)
 for size in [16,32,128,256,512]:
  subprocess.run(['sips','-z',str(size),str(size),str(icon),'--out',str(iconset/f'icon_{size}x{size}.png')],check=True,stdout=subprocess.DEVNULL)
  if size<=256:subprocess.run(['sips','-z',str(size*2),str(size*2),str(icon),'--out',str(iconset/f'icon_{size}x{size}@2x.png')],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['iconutil','-c','icns',str(iconset),'-o',str(resources/'JJRVIS.icns')],check=True)
 info['CFBundleIconFile']='JJRVIS';(contents/'Info.plist').write_bytes(plistlib.dumps(info))
entitlements=out/'mac-entitlements.plist';entitlements.write_bytes(plistlib.dumps({'com.apple.security.device.audio-input':True,'com.apple.security.personal-information.speech-recognition':True}))
sign=['codesign','--force','--sign',args.identity]
if not ios:sign+=['--entitlements',str(entitlements)]
if args.identity!='-':sign+=['--options','runtime']
subprocess.run(sign+[str(app)],check=True)
subprocess.run(['codesign','--verify','--strict',str(app)],check=True)
print(json.dumps({'app':str(app),'platform':sdk,'signed':'ad-hoc' if args.identity=='-' else 'development','notarized':False}))
