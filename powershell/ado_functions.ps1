# ════════════════════════════════════════════════════════════════════════════════
# AION - Azure DevOps PowerShell Functions
# Ajouter dans ton $PROFILE :
#   . "C:\code\python\AION\powershell\ado_functions.ps1"
# ════════════════════════════════════════════════════════════════════════════════

# ── Configuration ────────────────────────────────────────────────────────────
$ADO_ORG     = "Premiertech"
$ADO_PAT     = $env:ADO_PAT   # Charge depuis variable d environnement
$ADO_PROJECT = "PTG - TMM D2" # Projet par defaut

# Headers d authentification
function Get-AdoHeaders {
    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$ADO_PAT"))
    return @{
        "Authorization" = "Basic $token"
        "Content-Type"  = "application/json"
        "Accept"        = "application/json"
    }
}

# ── ado-get : Voir un work item ───────────────────────────────────────────────
function ado-get {
    <#
    .SYNOPSIS
        Affiche les details d un work item Azure DevOps.
    .EXAMPLE
        ado-get 12345
    #>
    param(
        [Parameter(Mandatory=$true)]
        [int]$Id
    )

    $headers = Get-AdoHeaders
    $url     = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems/${Id}?api-version=7.1"

    try {
        $item   = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
        $fields = $item.fields

        $assigned = if ($fields.'System.AssignedTo') {
            $fields.'System.AssignedTo'.displayName
        } else { "Non assigne" }

        Write-Host ""
        Write-Host "  Work Item #$Id" -ForegroundColor Cyan
        Write-Host "  $('─' * 50)" -ForegroundColor DarkGray
        Write-Host "  Titre    : $($fields.'System.Title')" -ForegroundColor White
        Write-Host "  Type     : $($fields.'System.WorkItemType')" -ForegroundColor Yellow
        Write-Host "  Statut   : $($fields.'System.State')" -ForegroundColor Green
        Write-Host "  Projet   : $($fields.'System.TeamProject')" -ForegroundColor Gray
        Write-Host "  Assigne  : $assigned" -ForegroundColor Gray
        if ($fields.'System.IterationPath') {
            Write-Host "  Sprint   : $($fields.'System.IterationPath')" -ForegroundColor Gray
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ❌ Erreur : $_" -ForegroundColor Red
    }
}

# ── ado-set : Mettre a jour le statut ────────────────────────────────────────
function ado-set {
    <#
    .SYNOPSIS
        Met a jour le statut d un work item Azure DevOps.
    .EXAMPLE
        ado-set 12345 "In Progress"
        ado-set 12345 "Done" -Comment "Termine par AION"
        ado-set 12345 "Done" -Project "PTG - TMM"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [int]$Id,

        [Parameter(Mandatory=$true)]
        [ValidateSet(
            "New", "Active", "Resolved", "Closed",
            "ToDo", "In Progress", "On hold", "In Review",
            "Done", "Removed", "In Analysis"
        )]
        [string]$State,

        [string]$Comment  = "",
        [string]$Project  = $ADO_PROJECT
    )

    $headers = Get-AdoHeaders
    $headers["Content-Type"] = "application/json-patch+json"
    $url = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems/${Id}?api-version=7.1"

    # Recuperer l etat actuel
    $current_state = ""
    $current_title = ""
    try {
        $current_url = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems/${Id}?api-version=7.1"
        $current = Invoke-RestMethod -Uri $current_url -Headers @{
            "Authorization" = $headers["Authorization"]
            "Accept" = "application/json"
        } -Method Get
        $current_state = $current.fields.'System.State'
        $current_title = $current.fields.'System.Title'
    } catch {}

    # Construire le patch
    $patch = @(
        @{
            op    = "replace"
            path  = "/fields/System.State"
            value = $State
        }
    )

    if ($Comment) {
        $patch += @{
            op    = "add"
            path  = "/fields/System.History"
            value = "[AION] $Comment"
        }
    }

    try {
        $result = Invoke-RestMethod -Uri $url -Headers $headers -Method Patch -Body ($patch | ConvertTo-Json)

        Write-Host ""
        Write-Host "  ✅ Work Item #$Id mis a jour" -ForegroundColor Green
        Write-Host "  Titre  : $current_title" -ForegroundColor White
        if ($current_state) {
            Write-Host "  Statut : $current_state → $State" -ForegroundColor Yellow
        } else {
            Write-Host "  Statut : $State" -ForegroundColor Yellow
        }
        if ($Comment) {
            Write-Host "  Note   : $Comment" -ForegroundColor Gray
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ❌ Erreur mise a jour : $_" -ForegroundColor Red
    }
}

# ── ado-list : Lister les work items ─────────────────────────────────────────
function ado-list {
    <#
    .SYNOPSIS
        Liste les work items d un projet.
    .EXAMPLE
        ado-list
        ado-list -State "In Progress"
        ado-list -Type "Bug" -State "Active"
        ado-list -Project "PTG - TMM" -Limit 20
    #>
    param(
        [string]$Project  = $ADO_PROJECT,
        [string]$State    = "",
        [string]$Type     = "",
        [string]$Assigned = "",
        [int]   $Limit    = 10
    )

    $headers = Get-AdoHeaders
    $headers["Content-Type"] = "application/json"

    # Construire WIQL
    $conditions = @("[System.TeamProject] = '$Project'")
    if ($State)    { $conditions += "[System.State] = '$State'" }
    if ($Type)     { $conditions += "[System.WorkItemType] = '$Type'" }
    if ($Assigned -eq "@me") {
        $conditions += "[System.AssignedTo] = @Me"
    } elseif ($Assigned) {
        $conditions += "[System.AssignedTo] contains '$Assigned'"
    }

    $where = $conditions -join " AND "
    $wiql = @{
        query = "SELECT [System.Id],[System.Title],[System.WorkItemType],[System.State] FROM WorkItems WHERE $where ORDER BY [System.ChangedDate] DESC"
    } | ConvertTo-Json

    $proj_encoded = [Uri]::EscapeDataString($Project)
    $wiql_url = "https://dev.azure.com/$ADO_ORG/$proj_encoded/_apis/wit/wiql?`$top=$Limit&api-version=7.1"

    try {
        $wiql_result = Invoke-RestMethod -Uri $wiql_url -Headers $headers -Method Post -Body $wiql
        $item_ids = ($wiql_result.workItems | Select-Object -First $Limit).id

        if (-not $item_ids) {
            Write-Host "  Aucun item trouve." -ForegroundColor Gray
            return
        }

        $ids_str = $item_ids -join ","
        $details_url = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems?ids=$ids_str&fields=System.Id,System.Title,System.WorkItemType,System.State&api-version=7.1"
        $details = Invoke-RestMethod -Uri $details_url -Headers @{
            "Authorization" = $headers["Authorization"]
            "Accept" = "application/json"
        } -Method Get

        $type_icons = @{
            "Bug"="🔴"; "Task"="✅"; "User Story"="📖"; "Feature"="⭐"; "Epic"="🚀"
        }

        Write-Host ""
        Write-Host "  Azure DevOps — $Project ($($details.count) item(s))" -ForegroundColor Cyan
        Write-Host "  $('─' * 60)" -ForegroundColor DarkGray

        foreach ($item in $details.value) {
            $f     = $item.fields
            $icon  = if ($type_icons[$f.'System.WorkItemType']) { $type_icons[$f.'System.WorkItemType'] } else { "📌" }
            $id    = $item.id
            $state = $f.'System.State'
            $title = $f.'System.Title'
            if ($title.Length -gt 55) { $title = $title.Substring(0, 52) + "..." }

            $state_color = switch ($state) {
                "Done"        { "Green" }
                "Closed"      { "Green" }
                "In Progress" { "Yellow" }
                "Active"      { "Yellow" }
                "New"         { "Cyan" }
                "ToDo"        { "Cyan" }
                "Removed"     { "Red" }
                default       { "White" }
            }

            Write-Host "  $icon " -NoNewline
            Write-Host ("#" + $id.ToString().PadRight(8)) -NoNewline -ForegroundColor DarkCyan
            Write-Host ("[$state]".PadRight(15)) -NoNewline -ForegroundColor $state_color
            Write-Host $title -ForegroundColor White
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ❌ Erreur : $_" -ForegroundColor Red
    }
}

# ── ado-open : Ouvrir dans le navigateur ─────────────────────────────────────
function ado-open {
    <#
    .SYNOPSIS
        Ouvre un work item dans le navigateur.
    .EXAMPLE
        ado-open 12345
    #>
    param(
        [Parameter(Mandatory=$true)]
        [int]$Id,
        [string]$Project = $ADO_PROJECT
    )
    $proj_encoded = [Uri]::EscapeDataString($Project)
    $url = "https://dev.azure.com/$ADO_ORG/$proj_encoded/_workitems/edit/$Id"
    Start-Process $url
    Write-Host "  🌐 Ouverture : $url" -ForegroundColor Cyan
}

# ── ado-my : Mes work items assignes ─────────────────────────────────────────
function ado-my {
    <#
    .SYNOPSIS
        Liste les work items qui me sont assignes.
    .EXAMPLE
        ado-my
        ado-my -Project "PTG - TMM"
    #>
    param(
        [string]$Project = $ADO_PROJECT,
        [string]$State   = "",
        [int]   $Limit   = 15
    )
    ado-list -Project $Project -Assigned "@me" -State $State -Limit $Limit
}

# ── ado-project : Changer le projet par defaut ───────────────────────────────
function ado-project {
    <#
    .SYNOPSIS
        Change le projet ADO par defaut pour la session.
    .EXAMPLE
        ado-project "PTG - TMM"
        ado-project "PTG - TMM D2"
    #>
    param([string]$Name)
    $script:ADO_PROJECT = $Name
    Write-Host "  ✅ Projet par defaut : $Name" -ForegroundColor Green
}

# ── Aliases courts ────────────────────────────────────────────────────────────
Set-Alias -Name adog  -Value ado-get     -Scope Global
Set-Alias -Name ados  -Value ado-set     -Scope Global
Set-Alias -Name adol  -Value ado-list    -Scope Global
Set-Alias -Name adom  -Value ado-my      -Scope Global
Set-Alias -Name adoo  -Value ado-open    -Scope Global
Set-Alias -Name adop  -Value ado-project -Scope Global

Write-Host "  🔵 Azure DevOps functions loaded | Org: $ADO_ORG | Projet: $ADO_PROJECT" -ForegroundColor DarkCyan
Write-Host "  Commandes : ado-get, ado-set, ado-list, ado-my, ado-open, ado-project" -ForegroundColor DarkGray
Write-Host "  Aliases   : adog, ados, adol, adom, adoo, adop" -ForegroundColor DarkGray
