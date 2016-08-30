!define APPNAME "Matuc"
!define DESCRIPTION "Command-line driven AGSBS utility for converting markdown with extensions"
# version digits must be integers
!define VERSIONMAJOR 0
!define VERSIONMINOR 1
!define VERSIONBUILD 1

# These will be displayed by the "Click here for support information" link in "Add/Remove Programs"
# email link which would open the email address in the email program
!define HELPURL "mailto:agsbs@groups.tu-dresden.de"
# This is the size (in kB) of all the files copied into "Program Files"
!define INSTALLSIZE 83700
# installer/uninstaller's title bar
Name "${APPNAME}"
  
!include "EnvVarUpdate.nsh"

# plain text files must have \r\n line delimiters
LicenseData "COPYING.txt"
Outfile "matuc_installer.exe"
InstallDir "$PROGRAMFILES\agsbs\matuc"

# installation flow

page license
page directory
page instfiles
UninstPage uninstConfirm
UninstPage instfiles

# before installation - check for existing installations

Function .onInit

  ReadRegStr $R0 HKLM \
      "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" \
      "UninstallString"
  StrCmp $R0 "" done

  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
      "${APPNAME} is already installed. $\n$\nClick `OK` to remove the \
      previous version or `Cancel` to cancel this upgrade." \
  IDOK uninst
  Abort

  ;Run the uninstaller
  uninst:
  ClearErrors
  ExecWait '$R0 _?=$INSTDIR' ;Do not copy the uninstaller to a temp file

  IfErrors no_remove_uninstaller done
    ;You can either use Delete /REBOOTOK in the uninstaller or add some code
    ;here to remove the uninstaller. Use a registry key to check
    ;whether the user has chosen to uninstall. If you are using an uninstaller
    ;components page, make sure all sections are uninstalled.

  no_remove_uninstaller:
done:

FunctionEnd


section ""

  # set values
  SetOutPath $INSTDIR

  # create batch file to run matuc
  FileOpen $0 "$INSTDIR\matuc.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "setlocal$\r$\n"
  FileWrite $0 "SET PATH=%PATH%;$\"$INSTDIR\binary$\"$\r$\n"
  FileWrite $0 "$\"$INSTDIR\binary\python$\" $\"$INSTDIR\matuc.py$\" %*$\r$\n"
  FileWrite $0 "endlocal"
  FileClose $0

  # select the files to install / to ship
  File /r "binary"
  file /r MAGSBS
  file matuc.py
  file COPYING.txt
  file 3rdparty\pandocfilters.py

  ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"


  # Start Menu
  createDirectory "$SMPROGRAMS\${APPNAME}"
  createShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}-Deinstallation.lnk" "$INSTDIR\uninstall.exe" "" ""
  createShortCut "$SMPROGRAMS\${APPNAME}\Hilfe.lnk" "http://elvis.inf.tu-dresden.de/wiki/index.php/Matuc" "" ""
 
  # Registry information for add/remove programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} converter - ${DESCRIPTION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$\"$INSTDIR$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "AG SBS, TU Dresden"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "HelpLink" "$\"${HELPURL}$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "$\"${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}$\""
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
  # There is no option for modifying or repairing the install
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
  # Set the INSTALLSIZE constant (!defined at the top of this script) so Add/Remove Programs can accurately report the size
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" ${INSTALLSIZE}

  # uninstallation
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR\binary"
  RMDir /r "$INSTDIR"
  rmDir /r "$SMPROGRAMS\${APPNAME}"

  # Remove uninstaller information from the registry
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

SectionEnd
