using System.Diagnostics;
using System.Text.Json;
using BadBuilder.Configuration;
using BadBuilder.Services;
using BadBuilder.Services.Disks;
using BadBuilder.UI;

namespace BadBuilder.Application;

internal static class WebBuilder
{
    private sealed class Request
    {
        public int DiskNumber { get; set; }
        public long DiskBytes { get; set; }
        public string DiskModel { get; set; } = "";
        public string Exploit { get; set; } = "BadUpdate";
        public string Bootstrap { get; set; } = "XeUnshackle";
        public bool FirmwareUpdate { get; set; }
        public List<string> HomebrewIds { get; set; } = [];
        public List<CustomHomebrew> CustomHomebrew { get; set; } = [];
        public string? LaunchId { get; set; }
        public Dictionary<string, string> ArchivePaths { get; set; } = [];
        public string Confirmation { get; set; } = "";
    }

    private sealed class CustomHomebrew
    {
        public string Path { get; set; } = "";
        public string? EntryPoint { get; set; }
    }

    private static string _statusPath = "";

    private static void Report(string state, string message)
    {
        var temporary = _statusPath + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(new { state, message }));
        File.Move(temporary, _statusPath, true);
    }

    internal static async Task RunAsync(string requestPath)
    {
        _statusPath = Path.ChangeExtension(requestPath, ".status.json");
        try
        {
            var request = JsonSerializer.Deserialize<Request>(await File.ReadAllTextAsync(requestPath))
                ?? throw new InvalidDataException("Builder request is empty.");
            if (request.Confirmation != $"ERASE DISK {request.DiskNumber}")
                throw new InvalidOperationException("Disk erase confirmation did not match the selected disk.");

            var config = BuildConfig(request);
            Controls.WebArchivePaths = request.ArchivePaths;
            Controls.WebReport = message => Report("running", message);

            var workRoot = Path.Combine(AppContext.BaseDirectory, "Work");
            var downloadRoot = Path.Combine(workRoot, "Downloads");
            var stagingRoot = Path.Combine(workRoot, "Staging", Path.GetFileNameWithoutExtension(requestPath));
            Directory.CreateDirectory(downloadRoot);
            Directory.CreateDirectory(stagingRoot);

            Report("running", "Resolving and downloading selected packages.");
            var artifacts = ArtifactCatalog.GetSelectedArtifacts(config);
            var download = await DownloadService.DownloadAsync(artifacts, downloadRoot, CancellationToken.None);
            Report("running", "Extracting packages before disk erase.");
            var staged = new List<(ArtifactDefinition Artifact, string StagingPath)>();
            foreach (var item in download.Artifacts)
            {
                string root = Path.Combine(stagingRoot, item.Artifact.ID);
                Directory.CreateDirectory(root);
                staged.Add((item.Artifact, await ArchiveService.ExtractAsync(item.ArchivePath, root, CancellationToken.None)));
            }

            var disk = ValidateDisk(request);
            Report("running", $"Erasing USB disk {request.DiskNumber} and formatting FAT32.");
            config.MountPoint = DiskService.FormatFAT32(disk);
            Report("running", "Copying selected packages to the USB disk.");
            var extra = new List<InstallOperation>
            {
                new(InstallOperationKind.WriteFile, "name.txt", Contents: "USB Storage Device"),
                new(InstallOperationKind.WriteFile, "info.txt", Contents: "This drive was created with BadBuilder by Pdawg.\nhttps://github.com/Pdawg-bytes/BadBuilder")
            };
            await InstallService.ExecuteAsync(staged, extra, config.MountPoint, CancellationToken.None);
            bool launchSet = config.LaunchHomebrew is null || SetDefaultLaunch(config.MountPoint, config.LaunchHomebrew);
            Report("complete", launchSet
                ? "USB drive prepared. Safely eject it before using it on the console."
                : "USB drive prepared, but launch.ini lacked a Default entry. Default homebrew launch was not set. Safely eject the drive.");
        }
        catch (Exception error)
        {
            Report("error", error.Message);
        }
    }

    private static BuilderConfig BuildConfig(Request request)
    {
        if (!Enum.TryParse<ExploitOption>(request.Exploit, false, out var exploit)
            || !ArtifactCatalog.Exploits.ContainsKey(exploit))
            throw new InvalidOperationException("Choose a supported exploit.");
        if (!Enum.TryParse<BootstrapOption>(request.Bootstrap, false, out var bootstrap)
            || !ArtifactCatalog.Bootstraps.ContainsKey(bootstrap))
            throw new InvalidOperationException("Choose a supported bootstrap.");
        var config = new BuilderConfig([])
        {
            SelectedExploit = exploit,
            SelectedBootstrap = bootstrap,
            FirmwareUpdateEnabled = request.FirmwareUpdate
        };
        if (request.FirmwareUpdate && (request.HomebrewIds.Count > 0 || request.CustomHomebrew.Count > 0 || request.LaunchId is not null))
            throw new InvalidOperationException("Dashboard update mode cannot include homebrew or a default launch.");
        foreach (string id in request.HomebrewIds.Distinct(StringComparer.Ordinal))
            config.Homebrew.Add(ArtifactCatalog.Homebrew.FirstOrDefault(item => item.Artifact.ID == id)
                ?? throw new InvalidOperationException("Unknown included homebrew selection."));
        if (request.CustomHomebrew.Count > 16)
            throw new InvalidOperationException("Too many custom homebrew archives.");
        for (int index = 0; index < request.CustomHomebrew.Count; index++)
        {
            var item = request.CustomHomebrew[index];
            string path = Path.GetFullPath(FileServices.NormalizeUserPath(item.Path));
            FileServices.EnsureFile(path);
            if (item.EntryPoint is not null && (item.EntryPoint.Any(char.IsControl)
                || item.EntryPoint.Contains(':') || item.EntryPoint.StartsWith('/') || item.EntryPoint.StartsWith('\\')
                || item.EntryPoint.Split(['/', '\\']).Any(part => part is "." or "..")))
                throw new InvalidOperationException("Selected homebrew entry point is unsafe.");
            if (item.EntryPoint is not null && !ArchiveService.FindEntryPoints(path).Contains(item.EntryPoint, StringComparer.OrdinalIgnoreCase))
                throw new InvalidOperationException("Selected homebrew entry point is absent from its archive.");
            string name = Path.GetFileNameWithoutExtension(path);
            if (string.IsNullOrWhiteSpace(name) || name is "." or "..")
                throw new InvalidOperationException("Custom homebrew archive name is invalid.");
            var artifact = new ArtifactDefinition($"homebrew-custom-{index}", name, "Custom homebrew", "homebrew",
                null, [new InstallOperation(InstallOperationKind.CopyDirectory, $"Apps/{name}", ".")],
                ArtifactPriority.Homebrew, path);
            config.Homebrew.Add(new HomebrewEntry(artifact, SourcePath: path, EntryPointRelativePath: item.EntryPoint));
        }
        if (request.LaunchId is not null)
        {
            if (bootstrap != BootstrapOption.XeUnshackle)
                throw new InvalidOperationException("Default homebrew launch requires XeUnshackle.");
            config.LaunchHomebrew = config.Homebrew.FirstOrDefault(item => item.Artifact.ID == request.LaunchId
                && item.EntryPointRelativePath is not null)
                ?? throw new InvalidOperationException("Choose an installed homebrew with a verified entry point.");
        }
        return config;
    }

    private static DiskInfo ValidateDisk(Request request)
    {
        if (request.DiskNumber < 0 || request.DiskBytes <= 0)
            throw new InvalidOperationException("USB disk identity is invalid.");
        var disk = DiskService.EnumerateDisks().SingleOrDefault(item => item.ID == request.DiskNumber.ToString()
            && item.Size == request.DiskBytes && item.Type == DriveType.Removable)
            ?? throw new InvalidOperationException("Selected USB disk changed. Refresh and review it again.");

        var process = new ProcessStartInfo("powershell.exe")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        process.ArgumentList.Add("-NoProfile");
        process.ArgumentList.Add("-NonInteractive");
        process.ArgumentList.Add("-Command");
        process.ArgumentList.Add($"Get-Disk -Number {request.DiskNumber} | Select-Object Number,FriendlyName,BusType,Size,IsSystem,IsBoot,IsReadOnly,OperationalStatus | ConvertTo-Json -Compress");
        using var child = Process.Start(process) ?? throw new IOException("USB disk check could not start.");
        string output = child.StandardOutput.ReadToEnd();
        child.WaitForExit();
        if (child.ExitCode != 0 || string.IsNullOrWhiteSpace(output))
            throw new IOException("USB disk check failed before formatting.");
        using var document = JsonDocument.Parse(output);
        var details = document.RootElement;
        string? friendlyName = details.GetProperty("FriendlyName").GetString();
        if (details.GetProperty("Number").GetInt32() != request.DiskNumber
            || details.GetProperty("Size").GetInt64() != request.DiskBytes
            || friendlyName is null || friendlyName[..Math.Min(100, friendlyName.Length)] != request.DiskModel
            || details.GetProperty("BusType").GetString() != "USB"
            || details.GetProperty("IsSystem").GetBoolean()
            || details.GetProperty("IsBoot").GetBoolean()
            || details.GetProperty("IsReadOnly").GetBoolean()
            || details.GetProperty("OperationalStatus").GetString() != "Online")
            throw new InvalidOperationException("Selected disk is no longer a writable, online, non-system USB disk.");
        return disk;
    }

    private static bool SetDefaultLaunch(string mountPoint, HomebrewEntry homebrew)
    {
        string iniPath = Path.Combine(mountPoint, "launch.ini");
        if (!File.Exists(iniPath))
        {
            return false;
        }
        var lines = File.ReadAllLines(iniPath);
        string path = $"Usb:\\Apps\\{homebrew.Artifact.DisplayName}\\{homebrew.EntryPointRelativePath!.Replace('/', '\\')}";
        for (int index = 0; index < lines.Length; index++)
            if (lines[index].TrimStart().StartsWith("Default =", StringComparison.OrdinalIgnoreCase))
            {
                lines[index] = $"Default = {path}";
                File.WriteAllLines(iniPath, lines);
                return true;
            }
        return false;
    }
}
