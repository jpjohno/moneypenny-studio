# JJRVIS Apple clients

Status: development preview, 20 October 2026.

The standalone Mac app is implemented using SwiftUI and WebKit. It uses the existing private JJRVIS service, keeps WebKit session cookies in its own persistent store, and has a device-local unlock gate using Apple's LocalAuthentication. Touch ID or the device password confirms that local unlock; it does not create or authenticate a customer account. No biometric template enters JJRVIS.

English speech recognition is bridged to Apple's on-device Speech framework. It requires microphone and speech permission, an available on-device English recognizer, and actual device verification. Voice is initially off in a new native profile. Existing browser permissions are not inherited. The renderer and speech bridge remain loaded through ordinary workspace navigation.

The interface loads current service code when the app opens. The native executable does not silently replace itself. Public native updates require a Developer ID distribution certificate, notarization, a signed update feed and release hosting, or App Store distribution. The available Apple Development certificate is sufficient for this Mac's development build; it is not evidence of paid membership or notarization.

## Builds

Run `python3 build.py` for an ad-hoc local Mac build. Pass `--identity` with your own valid Apple Development identity to sign a local development build. Run `python3 build.py --ios-simulator` to compile the shared iPhone client for the simulator. Build products remain under `.build/` and must not be committed.

The Mac app's first preference is the existing loopback service. If unavailable, it opens the fixed HTTPS private workspace. The iPhone client uses HTTPS and the existing device pairing flow. External news and music links open in the system browser. Only the fixed JJRVIS origins can invoke native speech.

## Pending Apple release steps

Confirm active Developer Program membership, the publishing legal entity and team. Select the signing team and bundle identifier in Xcode. Register distribution signing and provisioning through Apple, then archive, notarize or submit a TestFlight build. Account-holder agreements, identity verification and membership purchases must be completed by the account holder. No purchase or App Store submission has been made.

The iPhone Home Screen web app is available separately. It is not a published native iPhone application. Real iPhone camera, microphone, Face ID, pairing persistence and background behavior require device testing.

## Payments

Two separate, unconnected workflows are required:

* Customer subscriptions: customer identity, tenant isolation, entitlements, verified billing webhooks and the payment mechanism appropriate for each distribution channel.
* Payments requested by an owner: a supported payment/banking provider, a concrete payee and amount, an expiring authorization challenge, explicit confirmation and provider receipts. The assistant must never treat a conversation or a device unlock as permission to move money.

There are no payment credentials, merchant identifiers, charges or money-moving endpoints in this release. Neither workflow is live.
