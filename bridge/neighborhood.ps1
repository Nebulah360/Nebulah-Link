# Run with the Windows PowerShell architecture matching installed XDevkit COM.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$architecture = if ([IntPtr]::Size -eq 8) { 'x64' } else { 'x86' }
$request = $null
try {
  $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
  if ($null -eq $request -or $request -is [System.Array] -or
      $request -is [System.ValueType] -or $request -is [string]) { throw 'JSON object required' }
} catch {
  # Keep malformed adapter input structured and free of PowerShell/COM text.
  @{ diagnostic=@{code='ADAPTER_PROCESS_FAILED'; stage='startup'; architecture=$architecture; hresult='0x80070057'} } |
    ConvertTo-Json -Depth 3 -Compress
  exit 1
}
$manager = $null; $nativeConsole = $null; $console = $null; $connection = $null
$stage = 'com'; $failureCode = 'XDEVKIT_COM_FAILED'

try {
  if ($request.action -cnotin @('browse','browse-many','capacity','cpu-key','download-file','file-info','plugins','receive','status','storage')) { throw 'Read-only adapter operation required' }
  if ($request.target -and ([string]$request.target -notmatch '^[A-Za-z0-9_.-]{1,253}$')) { throw 'Invalid console target' }
  foreach ($remotePath in @($request.path) + @($request.paths)) {
    if ($null -ne $remotePath -and ([string]$remotePath -notmatch '^[A-Za-z0-9_]+:\\' -or [string]$remotePath -match '[\x00-\x1f"<>|?*]' -or [string]$remotePath -match '(?:^|\\)\.\.(?:\\|$)')) { throw 'Invalid console read path' }
  }
  . "$PSScriptRoot/telemetry.ps1"
  try { $manager = New-Object -ComObject 'XDevkit.XboxManager' } catch {
    # Some installations expose the registered COM class without this ProgID.
    # Activate only the XboxManager class; no SDK binaries are bundled/loaded.
    $managerType = [Type]::GetTypeFromCLSID([Guid]'A5EB45D8-F3B6-49B9-984A-0D313AB60342')
    $manager = [Activator]::CreateInstance($managerType)
  }
  $target = [string]$request.target
  if ([string]::IsNullOrWhiteSpace($target)) {
    $stage = 'default-console'; $failureCode = 'DEFAULT_CONSOLE_FAILED'
    $target = [string]$manager.DefaultConsole
    if ([string]::IsNullOrWhiteSpace($target)) {
      $failureCode = 'DEFAULT_CONSOLE_EMPTY'
      throw 'Default console unavailable'
    }
  }
  $stage = 'open-console'; $failureCode = 'CONSOLE_OPEN_FAILED'
  $nativeConsole = $manager.OpenConsole($target)
  if ($null -eq $nativeConsole) { throw 'Console object unavailable' }
  $stage = 'interface'; $failureCode = 'XDEVKIT_INTERFACE_FAILED'
  Add-Type -Path "$PSScriptRoot/ComDispatch.cs"
  $console = New-Object Nebulah.ConsoleDispatch -ArgumentList $nativeConsole
  # Set supported timeouts before the first remote operation, including drives.
  try { $console.ConnectTimeout = 2000 } catch {}
  try { $console.ConversationTimeout = 2000 } catch {}
  if ($request.action -in @('download-file','receive')) { $console.ConversationTimeout = 180000 }
  $stage = 'operation'; $failureCode = 'ADAPTER_OPERATION_FAILED'
  switch ($request.action) {
    'status' {
      # Deliberate allowlist. Never serialize a COM console/debug object.
      $stage = 'storage'; $failureCode = 'STORAGE_DISCOVERY_FAILED'
      $storage = Get-ConsoleStorage $console
      $stage = 'operation'; $failureCode = 'ADAPTER_OPERATION_FAILED'
      $telemetry = Get-ConsoleTelemetry $console
      $telemetry.resolved_target = $target
      $telemetry.drives = @($storage.drives)
      $telemetry.storage = @{source=$storage.source; state=$storage.state}
      $telemetry | ConvertTo-Json -Depth 5 -Compress
    }
    'cpu-key' {
      # Only invoked by the bridge after explicit, single-use consent.
      $console.ConnectTimeout = 2000
      $console.ConversationTimeout = 2000
      $connection = $console.OpenConnection('')
      $response = ''
      $console.SendTextCommand($connection, 'consolefeatures ver=2 type=10 params="A\0\A\0\"', [ref]$response)
      if ($response -notmatch '^200[- ]+\s*([0-9a-fA-F]{32})\s*$') { throw 'CPU key unavailable' }
      @{ cpu_key=$Matches[1].ToUpperInvariant() } | ConvertTo-Json -Compress
      $response = $null
    }
    'plugins' {
      # Module observation only; do not infer DLL/plugin identity from a name.
      Get-ConsoleModuleInventory $console | ConvertTo-Json -Depth 4 -Compress
    }
    'storage' {
      $stage = 'storage'; $failureCode = 'STORAGE_DISCOVERY_FAILED'
      Find-AccessibleConsoleStorage $console | ConvertTo-Json -Depth 4 -Compress
    }
    'capacity' {
      $connection = $console.OpenConnection($null)
      $reply = Read-TelemetryReply $console $connection ('drivefreespace name="' + [string]$request.path + '"')
      $values = @{}
      foreach ($key in @('totalbyteshi','totalbyteslo','totalfreebyteshi','totalfreebyteslo')) {
        if ($reply -notmatch ('(?:^|\s)' + $key + '=(?:0x)?([0-9A-Fa-f]{1,8})(?=\s|$)')) { throw 'Capacity unavailable' }
        $values[$key] = [Convert]::ToUInt64($Matches[1],16)
      }
      $total = $values.totalbyteshi * [uint64]4294967296 + $values.totalbyteslo
      $free = $values.totalfreebyteshi * [uint64]4294967296 + $values.totalfreebyteslo
      @{total=$total; free=$free} | ConvertTo-Json -Compress
    }
    'file-info' {
      $stage = 'transfer-info'; $failureCode = 'TRANSFER_INFO_FAILED'
      $file = $console.GetDownloadFileInfo([string]$request.path)
      @{directory=$file.IsDirectory; size=$file.Size} | ConvertTo-Json -Compress
    }
    'download-file' {
      $stage = 'transfer-read'; $failureCode = 'TRANSFER_READ_FAILED'
      $file = $console.GetDownloadFileInfo([string]$request.path)
      if ($file.IsDirectory -or $file.Size -ne [long]$request.size -or $file.Size -gt 134217728) { throw 'Remote size changed' }
      $console.ReceiveFile([string]$request.local,[string]$request.path)
      if ((Get-Item -LiteralPath ([string]$request.local)).Length -ne [long]$request.size) { throw 'Downloaded size changed' }
      @{ok=$true} | ConvertTo-Json -Compress
    }
    'browse' {
      $stage = 'storage'; $failureCode = 'STORAGE_BROWSE_FAILED'
      $items = @($console.DirectoryFiles([string]$request.path) | ForEach-Object {
        @{ name=[string]$_.Name; directory=[bool]$_.IsDirectory; size=[long]$_.Size }
      })
      @{ files=$items } | ConvertTo-Json -Depth 4 -Compress
    }
    'browse-many' {
      $stage = 'storage'; $failureCode = 'STORAGE_BROWSE_FAILED'
      $listings = @(
        foreach ($folder in $request.paths) {
          try {
            $items = @($console.DirectoryFiles([string]$folder) | ForEach-Object {
              @{ name=[string]$_.Name; directory=[bool]$_.IsDirectory; size=[long]$_.Size }
            })
            @{ files=$items }
          } catch {
            # A missing/removable folder must not discard other listings.
            @{ error=$true }
          }
        }
      )
      @{ listings=$listings } | ConvertTo-Json -Depth 6 -Compress
    }
    'receive' {
      $stage = 'transfer-info'; $failureCode = 'TRANSFER_INFO_FAILED'
      $file = $console.GetDownloadFileInfo([string]$request.path)
      if ($file.IsDirectory -or $file.Size -gt 67108864 -or $file.Size -lt 24) { throw 'File outside inspection limits' }
      $stage = 'transfer-read'; $failureCode = 'TRANSFER_READ_FAILED'
      $console.ReceiveFile([string]$request.local, [string]$request.path)
      if ((Get-Item -LiteralPath ([string]$request.local)).Length -ne $file.Size) { throw 'Inspected file size changed' }
      @{ ok=$true } | ConvertTo-Json -Compress
    }
    default { throw 'Read-only adapter operation required' }
  }
} catch {
  $cause = $_.Exception
  while ($null -ne $cause -and $null -ne $cause.InnerException) { $cause = $cause.InnerException }
  $hresult = '0x80004005'
  if ($null -ne $cause) { try { $hresult = '0x' + ([int]$cause.HResult).ToString('X8') } catch {} }
  @{ diagnostic=@{code=$failureCode; stage=$stage; architecture=$architecture; hresult=$hresult} } | ConvertTo-Json -Depth 3 -Compress
  exit 1
} finally {
  if ($null -ne $connection) { try { $console.CloseConnection($connection) } catch {} }
  if ($null -ne $nativeConsole) { try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($nativeConsole) } catch {} }
  if ($null -ne $manager) { try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($manager) } catch {} }
}
