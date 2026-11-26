# Basecamp apps by thehat

> **Disclaimer.** These are personal, experimental hobby projects. They are not
> official Logos products. Not audited. They are provided as is, with no warranty of
> any kind and no affiliation with or endorsement by any of the projects they
> interoperate with.

A package catalogue for [Logos Basecamp](https://github.com/logos-co/logos-basecamp). Add it once in
Basecamp and you can install and update these apps from inside Basecamp, signed by **thehat**.

| App | What it does | Source |
|---|---|---|
| **Manifesto** | Read the Logos manifesto and sign it in one click | [roxanneen/Manifesto-app](https://github.com/roxanneen/Manifesto-app) |
| **OneSecret** | Share a secret that can be read once, with no server | [IP3-Studio/OneSecret](https://github.com/IP3-Studio/OneSecret) |
| **Chess** | Play Stockfish, pass and play, or play a friend online | [IP3-Studio/Basecamp-chess-app](https://github.com/IP3-Studio/Basecamp-chess-app) |
| **Presence pilot** | An experiment with presence beacons that cannot be linked to each other | [IP3-Studio/Basecamp-presence-pilot](https://github.com/IP3-Studio/Basecamp-presence-pilot) |

Works on macOS with an Apple chip and on 64-bit Linux desktops (x86_64 and ARM64). Not on Windows,
Intel Macs, phones or tablets.

## Add the catalogue to Basecamp

You need Basecamp 0.3.2 or newer.

1. In Basecamp, open **Package Manager**.
2. Click **Manage Repositories**.
3. Add this address:

   ```
   https://raw.githubusercontent.com/roxanneen/basecamp-apps/main/logos-repo.json
   ```

4. Go back to the package list. The four apps appear there. Pick one and install it.

Basecamp shows these packages as signed by **thehat**. Updates arrive through the same list.

## What adding it means

- **You are trusting the publisher.** Every Basecamp app runs inside your Basecamp session with no
  sandbox. Adding a catalogue means trusting whoever signs its packages.
- **The packages are signed.** Each one carries an Ed25519 signature made with the publisher key
  below, and Basecamp checks it, along with the file's hash, before installing.
- **This catalogue lists only its own four apps.** It never lists a package from the official Logos
  catalogue. OneSecret and Chess need `delivery_module`, and Basecamp takes that from the official
  catalogue.
- **The signature says who published the file.** It does not say the app is safe or reviewed. The
  code for each app is in its own repository, linked above.

Publisher key:

```
did:jwk:eyJjcnYiOiJFZDI1NTE5Iiwia3R5IjoiT0tQIiwieCI6InZTcmo2S2JLellTXzFYdnU4YWNOYzd4SEJreTNjeTEzZmxJNXdjU21JWEUifQ
```

## How it is built

Each app builds its own per-platform packages in its own repository's CI. This catalogue takes those
release files, merges the three platforms into one package per app, signs that package on the
publisher's own computer, and publishes it here as a release asset.

| File | |
|---|---|
| `logos-repo.json` | What Basecamp reads first: the catalogue's name, the publisher key it trusts, and where the listing is |
| `packages.txt` | Which release of which app is in the catalogue |
| `scripts/prepare.sh` | Downloads and merges the per-platform packages. Signs nothing |
| `scripts/sign.sh` | Signs the merged packages. The only step that uses the secret key |
| `scripts/publish.sh` | Checks every package is signed by the trusted key, uploads it, rebuilds and uploads the listing |
| release `index` | The generated listing (`index.json`) and icons |
| releases `<app>-v<version>` | The signed packages |

The formats are those of the official Logos catalogue, and the listing is written with
[`logos-modules-release-tool`](https://github.com/logos-co/logos-modules-release-tool).

## Licence

The scripts in this repository are MIT licensed. Each app has its own licence in its own repository.
