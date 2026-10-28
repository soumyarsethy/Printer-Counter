Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Run pythonw silently without popping up a command prompt window
WshShell.Run "pythonw """ & scriptDir & "\printer_counter.py""", 0, False

