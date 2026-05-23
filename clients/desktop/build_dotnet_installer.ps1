param(
  [string]$OutputName = "AIProject1Setup.exe"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $ProjectDir

$ExePath = Join-Path $ProjectDir "dist\AI Project 1.exe"
if (!(Test-Path $ExePath)) {
  Write-Host "Executable is missing. Build it first:"
  Write-Host "powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -InstallPyInstaller"
  exit 1
}

$Csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (!(Test-Path $Csc)) {
  $Csc = "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (!(Test-Path $Csc)) {
  throw ".NET Framework C# compiler was not found."
}

$PackageDir = Join-Path $ProjectDir "build\installer-dotnet"
$PayloadDir = Join-Path $PackageDir "payload"
New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null
Copy-Item -LiteralPath $ExePath -Destination (Join-Path $PayloadDir "AI Project 1.exe") -Force
Copy-Item -LiteralPath (Join-Path $ProjectDir "README.md") -Destination (Join-Path $PayloadDir "README.md") -Force

$ZipPath = Join-Path $PackageDir "payload.zip"
if (Test-Path $ZipPath) {
  Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PayloadDir "*") -DestinationPath $ZipPath -Force

$SourcePath = Join-Path $PackageDir "InstallerStub.cs"
@'
using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;

internal static class InstallerStub
{
    [STAThread]
    private static int Main()
    {
        try
        {
            string tempDir = Path.Combine(Path.GetTempPath(), "AIProject1Setup-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);
            string zipPath = Path.Combine(tempDir, "payload.zip");
            using (Stream input = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (FileStream output = File.Create(zipPath))
            {
                if (input == null)
                {
                    throw new InvalidOperationException("Installer payload was not found.");
                }
                input.CopyTo(output);
            }
            ZipFile.ExtractToDirectory(zipPath, tempDir);

            string installDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "AI Project 1"
            );
            Directory.CreateDirectory(installDir);

            string sourceExe = Path.Combine(tempDir, "AI Project 1.exe");
            string targetExe = Path.Combine(installDir, "AI Project 1.exe");
            File.Copy(sourceExe, targetExe, true);

            string sourceReadme = Path.Combine(tempDir, "README.md");
            if (File.Exists(sourceReadme))
            {
                File.Copy(sourceReadme, Path.Combine(installDir, "README.md"), true);
            }

            string startMenuDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "AI Project 1"
            );
            Directory.CreateDirectory(startMenuDir);
            CreateShortcut(Path.Combine(startMenuDir, "AI Project 1.lnk"), targetExe, installDir);

            string desktopDir = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            if (!String.IsNullOrWhiteSpace(desktopDir))
            {
                CreateShortcut(Path.Combine(desktopDir, "AI Project 1.lnk"), targetExe, installDir);
            }

            MessageBox.Show(
                "AI Project 1 has been installed.",
                "AI Project 1",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            );
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "AI Project 1 Installer", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static void CreateShortcut(string shortcutPath, string targetPath, string workingDirectory)
    {
        Type shellType = Type.GetTypeFromProgID("WScript.Shell");
        if (shellType == null)
        {
            return;
        }
        object shell = Activator.CreateInstance(shellType);
        object shortcut = shellType.InvokeMember(
            "CreateShortcut",
            BindingFlags.InvokeMethod,
            null,
            shell,
            new object[] { shortcutPath }
        );
        Type shortcutType = shortcut.GetType();
        shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
        shortcutType.InvokeMember(
            "WorkingDirectory",
            BindingFlags.SetProperty,
            null,
            shortcut,
            new object[] { workingDirectory }
        );
        shortcutType.InvokeMember(
            "IconLocation",
            BindingFlags.SetProperty,
            null,
            shortcut,
            new object[] { targetPath + ",0" }
        );
        shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
    }
}
'@ | Set-Content -LiteralPath $SourcePath -Encoding UTF8

$OutputPath = Join-Path $ProjectDir "dist\$OutputName"
$IconPath = Join-Path $ProjectDir "assets\app_icon.ico"
& $Csc `
  /nologo `
  /target:winexe `
  /out:"$OutputPath" `
  /win32icon:"$IconPath" `
  /resource:"$ZipPath",payload.zip `
  /reference:System.IO.Compression.dll `
  /reference:System.IO.Compression.FileSystem.dll `
  /reference:System.Windows.Forms.dll `
  "$SourcePath"

if (!(Test-Path $OutputPath)) {
  throw "Installer was not created: $OutputPath"
}

Write-Host "Installer:"
Write-Host $OutputPath
