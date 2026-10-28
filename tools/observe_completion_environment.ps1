param(
    [Parameter(Mandatory=$true)][int[]]$ProcessIds,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$Duration=600,
    [int]$Interval=10
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$workRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'work'))+[IO.Path]::DirectorySeparatorChar
$outputPath=[IO.Path]::GetFullPath($Output)
if(-not $outputPath.StartsWith($workRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Project work output required.'}
if(Test-Path -LiteralPath $outputPath){throw 'Use a new evidence file.'}
if($Duration -le 0 -or $Interval -le 0 -or -not $ProcessIds.Count){throw 'Positive duration, interval and process IDs required.'}
$identities=@{}
foreach($observedPid in $ProcessIds){
    $entry=Get-CimInstance Win32_Process -Filter "ProcessId=$observedPid"
    if(-not $entry -or -not ($entry.Name -eq 'SlicerApp-real.exe' -or
       ($entry.Name -eq 'python.exe' -and $entry.CommandLine.Contains('Cardiac-CT-Motion-Control') -and $entry.CommandLine.Contains('app.py')))){
        throw 'Only the observed Slicer/project recognizer processes are in scope.'
    }
    $identities[$observedPid]=$entry.CreationDate
}
$principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
$elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$clock=[Diagnostics.Stopwatch]::StartNew()
$samples=[Collections.Generic.List[object]]::new()
while($clock.Elapsed.TotalSeconds -lt $Duration){
    $alive=@();$tcp=@();$udp=@();$queryErrors=@()
    foreach($observedPid in $ProcessIds){
        $entry=Get-CimInstance Win32_Process -Filter "ProcessId=$observedPid"
        if($entry -and $entry.CreationDate -eq $identities[$observedPid]){
            $alive+=$observedPid
            try{$tcp+=@(Get-NetTCPConnection -OwningProcess $observedPid -ErrorAction Stop | Select-Object OwningProcess,State,LocalAddress,LocalPort,RemoteAddress,RemotePort)}catch{
                if($_.FullyQualifiedErrorId -notlike 'CmdletizationQuery_NotFound*'){$queryErrors+=('tcp query unavailable for '+$observedPid)}
            }
            try{$udp+=@(Get-NetUDPEndpoint -OwningProcess $observedPid -ErrorAction Stop | Select-Object OwningProcess,LocalAddress,LocalPort)}catch{
                if($_.FullyQualifiedErrorId -notlike 'CmdletizationQuery_NotFound*'){$queryErrors+=('udp query unavailable for '+$observedPid)}
            }
        }
    }
    $samples.Add(@{elapsed_s=$clock.Elapsed.TotalSeconds;alive=$alive;tcp=$tcp;udp=$udp;query_errors=$queryErrors})
    Start-Sleep -Milliseconds ([int]([Math]::Min($Interval,[Math]::Max(0,$Duration-$clock.Elapsed.TotalSeconds))*1000))
}
$external=@($samples | ForEach-Object {$_.tcp} | Where-Object {$_.State -eq 'Established' -and $_.RemoteAddress -notin @('127.0.0.1','::1')})
$result=@{kind='actual OS sampled connection/privilege observation; not packet capture or complete egress audit';
    duration_s=$clock.Elapsed.TotalSeconds;required_duration_s=$Duration;interval_s=$Interval;
    elevated=$elevated;process_ids=$ProcessIds;external_established_tcp_observed=($external.Count -gt 0);
    camera_or_patient_images_saved=$false;independent_review=$false;
    limitation='Connections shorter than the sampling interval and UDP payload/destinations are unobserved. No clinical or X-08 total acceptance claim.';samples=$samples.ToArray()}
$result | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $outputPath -Encoding utf8
[pscustomobject]@{Duration=$result.duration_s;Samples=$samples.Count;Elevated=$elevated;ExternalEstablishedTCPObserved=$result.external_established_tcp_observed}
