import SwiftUI
import WebKit
import LocalAuthentication
import Speech
import AVFoundation
#if os(macOS)
import AppKit
#else
import UIKit
#endif

// A device-local unlock gate. This does not claim to authenticate a remote account.
final class DesktopSession: ObservableObject {
    @Published var unlocked = false
    @Published var notice = "Your private command centre."
    @Published var busy = false
    let browser = BrowserBridge()
    func unlock() {
        guard !busy else { return }; busy = true
        let context = LAContext()
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) else {
            busy = false; notice = "Set up a device passcode or password before unlocking JJRVIS."; return
        }
        context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: "Unlock your private JJRVIS workspace") { success, _ in
            DispatchQueue.main.async { self.busy = false; self.unlocked = success
                self.notice = success ? "" : "Unlock cancelled. Your workspace remains locked."
                if success { self.browser.openWorkspace() }
            }
        }
    }
    func lock() {
        browser.stopRecognition(); browser.webView.evaluateJavaScript("document.querySelector('#assistant-stop')?.click();")
        unlocked = false; notice = "Your workspace is locked."
    }
}

@main struct JJRVISApplication: App {
    @StateObject private var session = DesktopSession()
    var body: some Scene {
        #if os(macOS)
        Window("JJRVIS", id: "main") { content.frame(minWidth: 900, minHeight: 680) }
            .defaultSize(width: 1360, height: 900)
            .commands {
                CommandGroup(replacing: .newItem) {}
                CommandMenu("Workspace") {
                    Button("Lock JJRVIS") { session.lock() }.keyboardShortcut("l", modifiers: [.command, .shift])
                    Button("Refresh interface") { session.browser.webView.reloadFromOrigin() }.keyboardShortcut("r")
                    Button("App release notes") { NSWorkspace.shared.open(URL(string: "https://github.com/jpjohno/moneypenny-studio/releases")!) }
                }
            }
        #else
        WindowGroup { content }
        #endif
    }
    private var content: some View {
        ZStack {
            Color(red: 0.025, green: 0.055, blue: 0.085).ignoresSafeArea()
            if session.unlocked { WorkspaceView(bridge: session.browser) }
            else {
                VStack(spacing: 22) {
                    Image(systemName: "sparkles").font(.system(size: 54, weight: .light)).foregroundStyle(.cyan)
                    Text("JJRVIS").font(.system(size: 38, weight: .light, design: .rounded)).tracking(6)
                    Text(session.notice).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    Button(session.busy ? "Unlocking…" : "Unlock JJRVIS") { session.unlock() }
                        .buttonStyle(.borderedProminent).controlSize(.large).disabled(session.busy)
                    Text("Use your device’s secure sign-in.\nYour biometric data stays on your device.").font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.padding(40).foregroundStyle(.white)
            }
        }.preferredColorScheme(.dark)
    }
}

final class BrowserBridge: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    private(set) var webView: WKWebView!
    private var started = false
    private let engine = AVAudioEngine()
    private var recognition: SFSpeechRecognitionTask?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var tapInstalled = false
    private var speechEpoch = 0
    private var activeID: Int?
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-GB"))
    override init() {
        super.init()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.mediaTypesRequiringUserActionForPlayback = []
        config.applicationNameForUserAgent = "JJRVISNative/0.1"
        #if os(iOS)
        config.allowsInlineMediaPlayback = true
        #endif
        let source = Self.speechShim
        config.userContentController.addUserScript(WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        config.userContentController.add(self, name: "jjrvisSpeech")
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self; webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.customUserAgent = nil
    }
    private func trusted(_ url: URL?) -> Bool {
        guard let url else { return false }
        return (url.scheme == "http" && ["127.0.0.1", "localhost"].contains(url.host ?? "") && url.port == 8766)
            || (url.scheme == "https" && url.host == "app.jjrvis.com" && (url.port == nil || url.port == 443))
    }
    func openWorkspace() {
        guard !started else { return }; started = true
        #if os(macOS)
        let local = URL(string: "http://127.0.0.1:8766/workspace/local-connect")!
        var request = URLRequest(url: URL(string: "http://127.0.0.1:8766/workspace")!); request.timeoutInterval = 2
        URLSession.shared.dataTask(with: request) { _, response, _ in
            DispatchQueue.main.async {
                let available = (response as? HTTPURLResponse)?.statusCode == 200
                self.load(available ? local : URL(string: "https://app.jjrvis.com/workspace")!)
            }
        }.resume()
        #else
        load(URL(string: "https://app.jjrvis.com/workspace")!)
        #endif
    }
    private func load(_ url: URL) { webView.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 25)) }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        // Subframes remain under the website's existing CSP and permissions.
        if navigationAction.targetFrame?.isMainFrame == false { decisionHandler(.allow); return }
        if trusted(url) { decisionHandler(.allow); return }
        decisionHandler(.cancel)
        if ["https", "http", "mailto", "tel"].contains(url.scheme ?? "") { openExternal(url) }
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url=navigationAction.request.url, ["https", "http", "mailto", "tel"].contains(url.scheme ?? "") { openExternal(url) }; return nil
    }
    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        let local = origin.protocol == "http" && ["127.0.0.1", "localhost"].contains(origin.host) && origin.port == 8766
        let remote = origin.protocol == "https" && origin.host == "app.jjrvis.com" && [0, 443].contains(origin.port)
        guard frame.isMainFrame, trusted(frame.request.url), local || remote else { decisionHandler(.deny); return }
        // A deliberate capture request still goes through the system's prompt.
        decisionHandler(.prompt)
    }
    private func openExternal(_ url: URL) {
        #if os(macOS)
        NSWorkspace.shared.open(url)
        #else
        UIApplication.shared.open(url)
        #endif
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, trusted(message.frameInfo.request.url),
              let value=message.body as? [String: Any], let command=value["command"] as? String, let id=value["id"] as? Int else { return }
        if command == "start" { startRecognition(id) }
        else if activeID == id && (command == "stop" || command == "abort") { stopRecognition() }
    }
    private func emit(_ value: [String: Any]) {
        guard let data=try? JSONSerialization.data(withJSONObject: value),let json=String(data:data,encoding:.utf8) else { return }
        webView.evaluateJavaScript("window.dispatchEvent(new CustomEvent('jjrvis-native-speech',{detail:\(json)}));")
    }
    private func startRecognition(_ id: Int) {
        stopRecognition(); activeID=id; let own=speechEpoch
        SFSpeechRecognizer.requestAuthorization { status in
            DispatchQueue.main.async {
                guard own == self.speechEpoch, self.activeID == id else { return }
                guard status == .authorized else { self.emit(["id":id,"type":"error","error":"not-allowed"]);self.stopRecognition();return }
                #if os(macOS)
                AVCaptureDevice.requestAccess(for: .audio) { allowed in DispatchQueue.main.async { self.beginAudio(id,own:own,allowed:allowed) } }
                #else
                AVAudioApplication.requestRecordPermission { allowed in DispatchQueue.main.async { self.beginAudio(id,own:own,allowed:allowed) } }
                #endif
            }
        }
    }
    private func beginAudio(_ id:Int, own:Int, allowed:Bool) {
        guard own == speechEpoch, activeID == id else { return }
        guard allowed, let recognizer, recognizer.isAvailable else { emit(["id":id,"type":"error","error":allowed ? "service-not-allowed":"not-allowed"]);stopRecognition();return }
        do {
            #if os(iOS)
            try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode:.default, options:[.defaultToSpeaker,.allowBluetoothHFP])
            try AVAudioSession.sharedInstance().setActive(true)
            #endif
            let request=SFSpeechAudioBufferRecognitionRequest();request.shouldReportPartialResults=true
            // Keep dictation on-device. Do not silently send microphone audio to Apple.
            guard recognizer.supportsOnDeviceRecognition else { emit(["id":id,"type":"error","error":"service-not-allowed"]);stopRecognition();return }
            request.requiresOnDeviceRecognition=true;recognitionRequest=request
            let input=engine.inputNode
            try? input.setVoiceProcessingEnabled(true)
            let format=input.outputFormat(forBus:0)
            guard format.sampleRate > 0 else { throw NSError(domain:"JJRVIS",code:1) }
            input.installTap(onBus:0,bufferSize:1024,format:format) { buffer,_ in request.append(buffer) };tapInstalled=true
            engine.prepare();try engine.start();emit(["id":id,"type":"start"])
            recognition=recognizer.recognitionTask(with:request) { result,error in
                DispatchQueue.main.async {
                    guard own == self.speechEpoch, self.activeID == id else { return }
                    if let result { self.emit(["id":id,"type":"result","text":result.bestTranscription.formattedString,"final":result.isFinal]) }
                    if error != nil || result?.isFinal == true { self.stopRecognition() }
                }
            }
        } catch { emit(["id":id,"type":"error","error":"audio-capture"]);stopRecognition() }
    }
    func stopRecognition() {
        speechEpoch += 1;let previous=activeID;activeID=nil
        engine.stop();if tapInstalled {engine.inputNode.removeTap(onBus:0);tapInstalled=false}
        recognitionRequest?.endAudio();recognition?.cancel();recognition=nil;recognitionRequest=nil
        if let previous { emit(["id":previous,"type":"end"]) }
    }
    private static let speechShim = #"""
    (()=>{
      const sessions=new Map();let sequence=0;
      try{if(localStorage.getItem('jjrvis-wake-enabled')===null){localStorage.setItem('jjrvis-wake-enabled','false');localStorage.setItem('jjrvis-wake-persistent-v3','1');}}catch{}
      class NativeRecognition {
        constructor(){this.id=++sequence;this.lang='en-GB';this.continuous=true;this.interimResults=true;this.running=false;sessions.set(this.id,this);}
        start(){if(this.running)throw new DOMException('Already listening','InvalidStateError');this.running=true;sessions.set(this.id,this);window.webkit.messageHandlers.jjrvisSpeech.postMessage({id:this.id,command:'start'});}
        stop(){window.webkit.messageHandlers.jjrvisSpeech.postMessage({id:this.id,command:'stop'});}
        abort(){window.webkit.messageHandlers.jjrvisSpeech.postMessage({id:this.id,command:'abort'});}
      }
      window.addEventListener('jjrvis-native-speech',event=>{const d=event.detail,r=sessions.get(d.id);if(!r)return;
        if(d.type==='result'){const result={0:{transcript:d.text,confidence:1},length:1,isFinal:d.final};r.onresult?.({resultIndex:0,results:[result]});}
        if(d.type==='start')r.onstart?.({});if(d.type==='error')r.onerror?.({error:d.error});
        if(d.type==='end'){r.running=false;r.onend?.({});sessions.delete(d.id);}
      });
      window.SpeechRecognition=window.webkitSpeechRecognition=NativeRecognition;
      document.addEventListener('DOMContentLoaded',()=>{document.documentElement.dataset.nativeApp='apple';});
    })();
    """#
}

#if os(macOS)
struct WorkspaceView: NSViewRepresentable {
    let bridge: BrowserBridge
    func makeNSView(context: Context) -> WKWebView { bridge.webView }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
#else
struct WorkspaceView: UIViewRepresentable {
    let bridge: BrowserBridge
    func makeUIView(context: Context) -> WKWebView { bridge.webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
#endif
