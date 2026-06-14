# ============================================================================
# AION - Azure DevOps PowerShell Functions
# Ajouter dans ton $PROFILE :
#   . "C:\code\python\AION\powershelldo_functions.ps1"
# ============================================================================

# ── Configuration ─────────────────────────────────────────────────────────────
$ADO_ORG     = "Premiertech"
$ADO_PAT     = $env:ADO_PAT
$ADO_PROJECT = "PTG - TMM D2"

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
    .SYNOPSIS Affiche les details d un work item Azure DevOps.
    .EXAMPLE  ado-get 191614
    #>
    param([Parameter(Mandatory=$true)][int]$Id)

    $headers = Get-AdoHeaders
    $url     = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems/${Id}?api-version=7.1"

    try {
        $item   = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
        $fields = $item.fields
        $assigned = if ($fields."System.AssignedTo") {
            $fields."System.AssignedTo".displayName
        } else { "Non assigne" }

        Write-Host ""
        Write-Host "  Work Item #$Id" -ForegroundColor Cyan
        Write-Host "  $(("-" * 50))" -ForegroundColor DarkGray
        Write-Host "  Titre    : $($fields."System.Title")" -ForegroundColor White
        Write-Host "  Type     : $($fields."System.WorkItemType")" -ForegroundColor Yellow
        Write-Host "  Statut   : $($fields."System.State")" -ForegroundColor Green
        Write-Host "  Projet   : $($fields."System.TeamProject")" -ForegroundColor Gray
        Write-Host "  Assigne  : $assigned" -ForegroundColor Gray
        if ($fields."System.IterationPath") {
            Write-Host "  Sprint   : $($fields."System.IterationPath")" -ForegroundColor Gray
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ERREUR : $_" -ForegroundColor Red
    }
}

# ── ado-set : Mettre a jour le statut ────────────────────────────────────────
function ado-set {
    <#
    .SYNOPSIS Met a jour le statut d un work item Azure DevOps.
    .EXAMPLE  ado-set 191614 "In Progress"
    .EXAMPLE  ado-set 191614 "Done" -Comment "Termine par AION"
    .EXAMPLE  ado-set 191614 "Done" -Project "PTG - TMM"
    #>
    param(
        [Parameter(Mandatory=$true)][int]$Id,
        [Parameter(Mandatory=$true)]
        [ValidateSet(
            "New","Active","Resolved","Closed",
            "ToDo","In Progress","On hold","In Review",
            "Done","Removed","In Analysis"
        )]
        [string]$State,
        [string]$Comment = "",
        [string]$Project = $ADO_PROJECT
    )

    $headers = Get-AdoHeaders
    $headers["Content-Type"] = "application/json-patch+json"
    $url = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems/${Id}?api-version=7.1"

    # Recuperer etat actuel
    $current_state = ""
    $current_title = ""
    try {
        $get_headers = @{
            "Authorization" = $headers["Authorization"]
            "Accept"        = "application/json"
        }
        $current       = Invoke-RestMethod -Uri $url -Headers $get_headers -Method Get
        $current_state = $current.fields."System.State"
        $current_title = $current.fields."System.Title"
    } catch {}

    $patch = @(
        @{ op = "replace"; path = "/fields/System.State"; value = $State }
    )
    if ($Comment) {
        $patch += @{ op = "add"; path = "/fields/System.History"; value = "[AION] $Comment" }
    }

    try {
        $null = Invoke-RestMethod -Uri $url -Headers $headers -Method Patch `
                    -Body ($patch | ConvertTo-Json -Depth 3)

        Write-Host ""
        Write-Host "  OK - Work Item #$Id mis a jour" -ForegroundColor Green
        Write-Host "  Titre  : $current_title" -ForegroundColor White
        if ($current_state) {
            Write-Host "  Statut : $current_state -> $State" -ForegroundColor Yellow
        } else {
            Write-Host "  Statut : $State" -ForegroundColor Yellow
        }
        if ($Comment) {
            Write-Host "  Note   : $Comment" -ForegroundColor Gray
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ERREUR mise a jour : $_" -ForegroundColor Red
    }
}

# ── ado-list : Lister les work items ─────────────────────────────────────────
function ado-list {
    <#
    .SYNOPSIS Liste les work items d un projet.
    .EXAMPLE  ado-list
    .EXAMPLE  ado-list -State "In Progress"
    .EXAMPLE  ado-list -Type "Bug" -State "Active"
    .EXAMPLE  ado-list -Project "PTG - TMM" -Limit 20
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

    $conditions = @("[System.TeamProject] = '$Project'")
    if ($State)    { $conditions += "[System.State] = '$State'" }
    if ($Type)     { $conditions += "[System.WorkItemType] = '$Type'" }
    if ($Assigned -eq "@me") {
        $conditions += "[System.AssignedTo] = @Me"
    } elseif ($Assigned) {
        $conditions += "[System.AssignedTo] contains '$Assigned'"
    }

    $where = $conditions -join " AND "
    $wiql  = @{
        query = "SELECT [System.Id],[System.Title],[System.WorkItemType],[System.State] FROM WorkItems WHERE $where ORDER BY [System.ChangedDate] DESC"
    } | ConvertTo-Json

    $proj_encoded = [Uri]::EscapeDataString($Project)
    $wiql_url     = "https://dev.azure.com/$ADO_ORG/$proj_encoded/_apis/wit/wiql?`$top=$Limit&api-version=7.1"

    try {
        $wiql_result = Invoke-RestMethod -Uri $wiql_url -Headers $headers `
                           -Method Post -Body $wiql
        $item_ids    = ($wiql_result.workItems | Select-Object -First $Limit).id

        if (-not $item_ids) {
            Write-Host "  Aucun item trouve." -ForegroundColor Gray
            return
        }

        $ids_str      = $item_ids -join ","
        $get_headers  = @{
            "Authorization" = $headers["Authorization"]
            "Accept"        = "application/json"
        }
        $details_url  = "https://dev.azure.com/$ADO_ORG/_apis/wit/workitems?ids=$ids_str&fields=System.Id,System.Title,System.WorkItemType,System.State&api-version=7.1"
        $details      = Invoke-RestMethod -Uri $details_url -Headers $get_headers -Method Get

        Write-Host ""
        Write-Host "  Azure DevOps - $Project ($($details.count) item(s))" -ForegroundColor Cyan
        Write-Host "  $(("-" * 60))" -ForegroundColor DarkGray

        foreach ($item in $details.value) {
            $f     = $item.fields
            $id    = $item.id
            $state = $f."System.State"
            $title = $f."System.Title"
            $type  = $f."System.WorkItemType"

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

            $type_short = switch ($type) {
                "Bug"        { "[Bug]" }
                "Task"       { "[Task]" }
                "User Story" { "[Story]" }
                "Feature"    { "[Feat]" }
                "Epic"       { "[Epic]" }
                default      { "[Item]" }
            }

            Write-Host "  $type_short " -NoNewline -ForegroundColor DarkYellow
            Write-Host ("#" + $id.ToString().PadRight(8)) -NoNewline -ForegroundColor DarkCyan
            Write-Host ("[$state]".PadRight(15)) -NoNewline -ForegroundColor $state_color
            Write-Host $title -ForegroundColor White
        }
        Write-Host ""
    }
    catch {
        Write-Host "  ERREUR : $_" -ForegroundColor Red
    }
}

# ── ado-open : Ouvrir dans le navigateur ─────────────────────────────────────
function ado-open {
    <#
    .SYNOPSIS Ouvre un work item dans le navigateur.
    .EXAMPLE  ado-open 191614
    #>
    param(
        [Parameter(Mandatory=$true)][int]$Id,
        [string]$Project = $ADO_PROJECT
    )
    $proj_encoded = [Uri]::EscapeDataString($Project)
    $url = "https://dev.azure.com/$ADO_ORG/$proj_encoded/_workitems/edit/$Id"
    Start-Process $url
    Write-Host "  Ouverture : $url" -ForegroundColor Cyan
}

# ── ado-my : Mes work items assignes ─────────────────────────────────────────
function ado-my {
    <#
    .SYNOPSIS Liste les work items qui me sont assignes.
    .EXAMPLE  ado-my
    .EXAMPLE  ado-my -State "In Progress"
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
    .SYNOPSIS Change le projet ADO par defaut.
    .EXAMPLE  ado-project "PTG - TMM"
    #>
    param([string]$Name)
    $script:ADO_PROJECT = $Name
    Write-Host "  Projet par defaut : $Name" -ForegroundColor Green
}

# ── ado-help : Aide contextuelle ─────────────────────────────────────────────
function ado-help {
    Write-Host ""
    Write-Host "  Azure DevOps - Commandes disponibles" -ForegroundColor Cyan
    Write-Host "  $(("-" * 50))" -ForegroundColor DarkGray
    Write-Host "  ado-get  <id>                    Voir un work item" -ForegroundColor White
    Write-Host "  ado-set  <id> <etat>             Changer le statut" -ForegroundColor White
    Write-Host "  ado-set  <id> <etat> -Comment X  Avec commentaire" -ForegroundColor White
    Write-Host "  ado-list                          Lister les items" -ForegroundColor White
    Write-Host "  ado-list -State ""In Progress""    Filtrer par etat" -ForegroundColor White
    Write-Host "  ado-list -Type Bug -State Active  Filtrer type+etat" -ForegroundColor White
    Write-Host "  ado-my                            Mes items assignes" -ForegroundColor White
    Write-Host "  ado-open <id>                     Ouvrir navigateur" -ForegroundColor White
    Write-Host "  ado-project ""PTG - TMM""           Changer projet" -ForegroundColor White
    Write-Host ""
    Write-Host "  Etats valides :" -ForegroundColor DarkGray
    Write-Host "    Bug        : New, Active, Resolved, Closed" -ForegroundColor Gray
    Write-Host "    Task/Feat  : ToDo, In Progress, On hold, In Review, Done, Removed" -ForegroundColor Gray
    Write-Host "    Story/Epic : New, In Analysis, In Progress, In Review, Done" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Aliases : adog, ados, adol, adom, adoo, adop, adoh" -ForegroundColor DarkGray
    Write-Host ""
}

# ── Aliases ───────────────────────────────────────────────────────────────────
Set-Alias -Name adog -Value ado-get     -Scope Global
Set-Alias -Name ados -Value ado-set     -Scope Global
Set-Alias -Name adol -Value ado-list    -Scope Global
Set-Alias -Name adom -Value ado-my      -Scope Global
Set-Alias -Name adoo -Value ado-open    -Scope Global
Set-Alias -Name adop -Value ado-project -Scope Global
Set-Alias -Name adoh -Value ado-help    -Scope Global

Write-Host "  ADO functions loaded | Org: $ADO_ORG | Projet: $ADO_PROJECT" -ForegroundColor DarkCyan
Write-Host "  ado-help pour la liste des commandes" -ForegroundColor DarkGray
