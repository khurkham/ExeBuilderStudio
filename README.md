# ExeBuilderStudio

Windows desktop builder, version 1.0. Developed by Khurkham Langkhur.

## Download and install

Download `ExeBuilderStudio_Setup.exe` from [Latest release](https://github.com/khurkham/ExeBuilderStudio/releases/latest). The installer contains the application, Shan and Thai fonts, logo and Windows icons. Python is not required on the user's computer.

## Online updates

Open About and click Update ExeBuilderStudio. The application checks this public repository's latest release, downloads the Windows installer with progress, verifies its SHA-256, then launches the installer. End users do not enter a repository or GitHub token.

For older builds that have no update repository configured, install the first online-enabled Setup manually once.

## Publisher releases

GitHub Actions builds a Windows x64 installer and publishes it to Releases. To publish a new version, increase `APP_VERSION` in `tool_downloads.py` and `AppVersion` in `installer/ExeBuilderStudio.iss`, then push to main. Existing release versions are not overwritten. You can also run the Windows installer and online updates workflow manually.

## Build locally

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Build_Studio.ps1 -CreateInstaller
```

Requires Python and Inno Setup on the build machine. See [Thai guide](README_TH.md).
